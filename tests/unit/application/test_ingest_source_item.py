"""Testes de integração para IngestSourceItemUseCase — UC-1."""

from datetime import datetime

import pytest

from taskflow.application.dto.commands import IngestSourceItemCommand
from taskflow.application.use_cases.ingest_source_item import IngestSourceItemUseCase
from taskflow.domain.value_objects.enums import CalendarSensitivity, SourceKind
from tests.fakes import FakeQueue, FakeSignalRepository, FakeTaskRepository, FakeUnitOfWork


def make_uc() -> tuple[IngestSourceItemUseCase, FakeSignalRepository, FakeQueue]:
    task_repo = FakeTaskRepository()
    sig_repo = FakeSignalRepository()
    queue = FakeQueue()
    uow = FakeUnitOfWork()
    uc = IngestSourceItemUseCase(
        task_repo=task_repo,
        signal_repo=sig_repo,
        queue=queue,
        uow=uow,
    )
    return uc, sig_repo, queue


def email_cmd(**kwargs) -> IngestSourceItemCommand:
    return IngestSourceItemCommand(
        kind=SourceKind.EMAIL,
        channel="email",
        external_id=kwargs.get("external_id", "msg-001"),
        occurred_at=datetime.utcnow(),
        revision_hash="hash-001",
        title="Precisamos terminar o relatório",
        body_preview="Conforme combinado, vou enviar até sexta.",
        author_email="parceiro@empresa.com",
    )


class TestIngestEmail:
    """Testes de ingestão de e-mail."""

    @pytest.mark.asyncio
    async def test_email_is_enqueued(self) -> None:
        uc, _, queue = make_uc()
        result = await uc.execute(email_cmd())
        assert result.was_enqueued_for_correlation
        assert len(queue.queued) == 1
        assert queue.queued[0]["task"] == "extract_signals"

    @pytest.mark.asyncio
    async def test_email_not_filtered(self) -> None:
        uc, _, _ = make_uc()
        result = await uc.execute(email_cmd())
        assert not result.was_filtered


class TestIngestCalendarEvent:
    """Testes de ingestão de evento de calendário — RF-F.3."""

    @pytest.mark.asyncio
    async def test_normal_event_is_enqueued(self) -> None:
        uc, _, _queue = make_uc()
        cmd = IngestSourceItemCommand(
            kind=SourceKind.CALENDAR_EVENT,
            channel="calendar",
            external_id="evt-001",
            occurred_at=datetime.utcnow(),
            revision_hash="r-001",
            title="Reunião de alinhamento",
            body_preview="Pauta: sprints e dependências",
            calendar_starts_at=datetime.utcnow(),
            calendar_ends_at=datetime.utcnow(),
            calendar_sensitivity=CalendarSensitivity.NORMAL.value,
        )
        result = await uc.execute(cmd)
        assert result.was_enqueued_for_correlation

    @pytest.mark.asyncio
    async def test_private_event_is_filtered_not_enqueued(self) -> None:
        """★ PROPRIEDADE RF-F.3: evento privado NÃO vai para correlação."""
        uc, _, queue = make_uc()
        cmd = IngestSourceItemCommand(
            kind=SourceKind.CALENDAR_EVENT,
            channel="calendar",
            external_id="evt-private-001",
            occurred_at=datetime.utcnow(),
            revision_hash="r-p-001",
            title="Consulta médica",
            body_preview="Detalhes confidenciais",
            calendar_starts_at=datetime.utcnow(),
            calendar_ends_at=datetime.utcnow(),
            calendar_sensitivity=CalendarSensitivity.PRIVATE.value,
        )
        result = await uc.execute(cmd)
        assert result.was_filtered
        assert result.filtered_reason == "privacy_redaction"
        assert not result.was_enqueued_for_correlation
        assert len(queue.queued) == 0

    @pytest.mark.asyncio
    async def test_confidential_event_is_filtered(self) -> None:
        """★ PROPRIEDADE RF-F.3: evento confidencial NÃO vai para correlação."""
        uc, _, queue = make_uc()
        cmd = IngestSourceItemCommand(
            kind=SourceKind.CALENDAR_EVENT,
            channel="calendar",
            external_id="evt-conf-001",
            occurred_at=datetime.utcnow(),
            revision_hash="r-c-001",
            calendar_starts_at=datetime.utcnow(),
            calendar_ends_at=datetime.utcnow(),
            calendar_sensitivity=CalendarSensitivity.CONFIDENTIAL.value,
        )
        result = await uc.execute(cmd)
        assert result.was_filtered
        assert len(queue.queued) == 0
