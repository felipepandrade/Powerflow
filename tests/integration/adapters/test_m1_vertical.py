from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import date, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from taskflow.adapters.persistence.models import (
    Base,
    CorrelationRunORM,
    SignalORM,
    SourceItemORM,
    TaskEvidenceORM,
    TaskStatusHistoryORM,
    TaskUpdateORM,
)
from taskflow.adapters.persistence.signal_repository import SqlAlchemySignalRepository
from taskflow.adapters.persistence.task_repository import SqlAlchemyTaskRepository
from taskflow.adapters.persistence.unit_of_work import SqlAlchemyUnitOfWork
from taskflow.application.dto.commands import (
    CorrelateSignalCommand,
    IngestSourceItemCommand,
    UndoAutoActionCommand,
)
from taskflow.application.use_cases.correlate_signal import CorrelateSignalUseCase
from taskflow.application.use_cases.extract_signals import ExtractSignalsUseCase
from taskflow.application.use_cases.ingest_source_item import IngestSourceItemUseCase
from taskflow.application.use_cases.manage_task import ManageTaskUseCase
from taskflow.domain.value_objects.enums import CalendarSensitivity, SourceKind
from tests.fakes import FakeEmbeddingProvider, FakeLLMProvider, FakeQueue


@pytest.fixture
async def m1_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


def email_command(external_id: str, revision: str, body: str) -> IngestSourceItemCommand:
    return IngestSourceItemCommand(
        kind=SourceKind.EMAIL,
        channel="mail",
        external_id=external_id,
        revision_hash=revision,
        occurred_at=datetime(2026, 8, 5, 9, 0),
        title="Quarterly report",
        body_preview=body,
        body_full=body,
        store_full_body=False,
    )


@pytest.mark.asyncio
async def test_safe_vertical_persists_audit_and_idempotent_undo(
    m1_session: AsyncSession,
) -> None:
    signal_repo = SqlAlchemySignalRepository(m1_session)
    task_repo = SqlAlchemyTaskRepository(m1_session)
    uow = SqlAlchemyUnitOfWork(m1_session)
    queue = FakeQueue()
    ingest = IngestSourceItemUseCase(task_repo, signal_repo, queue, uow)

    origin_text = "I will deliver the quarterly report by August 10."
    origin_cmd = email_command("mail-1", "rev-1", origin_text)
    origin = await ingest.execute(origin_cmd)
    duplicate = await ingest.execute(origin_cmd)
    assert duplicate.was_deduplicated is True
    assert duplicate.source_item_id == origin.source_item_id
    stored_source = await signal_repo.get_source_item_by_id(origin.source_item_id)
    assert stored_source is not None
    assert stored_source.body_full is None

    origin_llm = FakeLLMProvider(
        classify_response={"has_commitment": True},
        extract_response={
            "signals": [{
                "signal_type": "commitment",
                "evidence_quote": "deliver the quarterly report by August 10",
                "extraction_confidence": 0.96,
                "payload": {
                    "title": "Deliver quarterly report",
                    "description": "Prepare and deliver the report",
                    "due_date": "2026-08-10",
                    "priority": "high",
                },
            }]
        },
    )
    origin_signal_id = (
        await ExtractSignalsUseCase(
            signal_repo, origin_llm, queue, uow
        ).execute(origin.source_item_id)
    )[0]
    origin_result = await CorrelateSignalUseCase(
        task_repo,
        signal_repo,
        origin_llm,
        FakeEmbeddingProvider(),
        uow,
    ).execute(CorrelateSignalCommand(origin_signal_id))
    assert origin_result.applied_task_id is not None
    task_id = origin_result.applied_task_id

    update_text = "For the same report, delivery moves to August 12. Draft completed."
    update = await ingest.execute(email_command("mail-2", "rev-1", update_text))
    update_llm = FakeLLMProvider(
        classify_response={"has_commitment": True},
        extract_response={
            "signals": [{
                "signal_type": "progress_update",
                "evidence_quote": "delivery moves to August 12",
                "extraction_confidence": 0.97,
                "payload": {
                    "task_id": str(task_id),
                    "title": "Deliver quarterly report",
                    "due_date": "2026-08-12",
                    "progress_note": "Draft completed.",
                },
            }]
        },
    )
    update_signal_id = (
        await ExtractSignalsUseCase(
            signal_repo, update_llm, queue, uow
        ).execute(update.source_item_id)
    )[0]
    update_result = await CorrelateSignalUseCase(
        task_repo,
        signal_repo,
        update_llm,
        FakeEmbeddingProvider(),
        uow,
    ).execute(CorrelateSignalCommand(update_signal_id))
    assert update_result.applied_task_id == task_id

    persisted = await task_repo.get_by_id(task_id)
    assert persisted is not None
    assert persisted.due_date == date(2026, 8, 12)
    assert len(persisted.evidence) == 2
    assert len(persisted.updates) == 1
    undo_history = next(
        row
        for row in persisted.status_history
        if row.signal_id == update_signal_id and row.snapshot
    )

    manage = ManageTaskUseCase(task_repo, uow, signal_repo=signal_repo)
    undo_command = UndoAutoActionCommand(task_id=task_id, history_id=undo_history.id)
    first_undo = await manage.undo_auto_action(undo_command)
    second_undo = await manage.undo_auto_action(undo_command)
    assert first_undo.due_date == date(2026, 8, 10)
    assert second_undo.due_date == date(2026, 8, 10)

    discarded_signal = await signal_repo.get_signal_by_id(update_signal_id)
    assert discarded_signal is not None
    assert discarded_signal.state.value == "discarded"

    for model, expected in (
        (SourceItemORM, 2),
        (SignalORM, 2),
        (CorrelationRunORM, 2),
        (TaskEvidenceORM, 2),
        (TaskUpdateORM, 1),
    ):
        count = await m1_session.scalar(select(func.count()).select_from(model))
        assert count == expected
    history_rows = (
        await m1_session.execute(
            select(TaskStatusHistoryORM).where(TaskStatusHistoryORM.task_id == task_id)
        )
    ).scalars().all()
    assert sum(row.is_undone for row in history_rows) == 1


@pytest.mark.asyncio
async def test_confidential_calendar_never_reaches_llm(
    m1_session: AsyncSession,
) -> None:
    signal_repo = SqlAlchemySignalRepository(m1_session)
    task_repo = SqlAlchemyTaskRepository(m1_session)
    uow = SqlAlchemyUnitOfWork(m1_session)
    queue = FakeQueue()
    ingest = IngestSourceItemUseCase(task_repo, signal_repo, queue, uow)
    result = await ingest.execute(
        IngestSourceItemCommand(
            kind=SourceKind.CALENDAR_EVENT,
            channel="calendar",
            external_id="private-event",
            revision_hash="rev-private",
            occurred_at=datetime(2026, 8, 5, 14, 0),
            title="Confidential reorganization",
            body_preview="Secret participants and agenda",
            calendar_starts_at=datetime(2026, 8, 5, 14, 0),
            calendar_ends_at=datetime(2026, 8, 5, 15, 0),
            calendar_sensitivity=CalendarSensitivity.CONFIDENTIAL.value,
        )
    )
    assert result.was_filtered is True
    llm = FakeLLMProvider()
    extracted = await ExtractSignalsUseCase(signal_repo, llm, queue, uow).execute(
        result.source_item_id
    )
    assert extracted == []
    assert llm.calls == []
