"""Testes de integração e unitários para BuildDailySnapshotsUseCase e HealthScorePolicy."""

import uuid
from datetime import UTC, date, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from taskflow.adapters.persistence.models import Base, ProjectORM, TaskORM
from taskflow.adapters.persistence.unit_of_work import SqlAlchemyUnitOfWork
from taskflow.application.use_cases.build_daily_snapshots import BuildDailySnapshotsUseCase
from taskflow.domain.policies.health_score_policy import HealthScorePolicy


@pytest.fixture
async def db_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


def test_health_score_policy_calculation() -> None:
    # Projeto perfeito
    res_perfect = HealthScorePolicy.calculate(
        tasks_total=10,
        tasks_open=10,
        tasks_in_progress=2,
        tasks_blocked=0,
        tasks_overdue=0,
        milestones_total=2,
        milestones_at_risk=0,
        milestones_missed=0,
        days_since_activity=1,
        oldest_blocked_days=0,
    )
    assert res_perfect.score >= 90.0

    # Projeto em risco
    res_risk = HealthScorePolicy.calculate(
        tasks_total=10,
        tasks_open=10,
        tasks_in_progress=8,  # WIP alto
        tasks_blocked=3,
        tasks_overdue=4,
        milestones_total=2,
        milestones_at_risk=1,
        milestones_missed=1,
        days_since_activity=10,
        oldest_blocked_days=5,
    )
    assert res_risk.score < 60.0
    assert "wip_score" in res_risk.components


def test_health_score_is_unknown_without_observable_tasks() -> None:
    result = HealthScorePolicy.calculate(
        tasks_total=0,
        tasks_open=0,
        tasks_in_progress=0,
        tasks_blocked=0,
        tasks_overdue=0,
        milestones_total=0,
        milestones_at_risk=0,
        milestones_missed=0,
        days_since_activity=None,
        oldest_blocked_days=None,
    )
    assert result.score is None
    assert result.coverage_pct == 0.0


@pytest.mark.asyncio
async def test_build_daily_snapshots_use_case(db_session: AsyncSession) -> None:
    # 1. Criar projeto e tarefas no banco
    proj_id = uuid.uuid4()
    proj = ProjectORM(id=proj_id, name="Projeto Teste Snapshots", status="active")
    db_session.add(proj)

    task1 = TaskORM(
        id=uuid.uuid4(), title="Tarefa 1", status="in_progress", priority="high", project_id=proj_id
    )
    task2 = TaskORM(
        id=uuid.uuid4(), title="Tarefa 2", status="done", priority="medium", project_id=proj_id
    )
    db_session.add_all([task1, task2])
    await db_session.commit()

    # 2. Executar use case
    uow = SqlAlchemyUnitOfWork(db_session)
    uc = BuildDailySnapshotsUseCase(db_session, uow)

    today = datetime.now(UTC).date()
    res = await uc.execute(today)

    assert res["task_snapshots"] == 2
    assert res["project_snapshots"] == 1
    assert res["calendar_snapshots"] == 1

    # 3. Teste de Idempotência: re-executar não duplica registros
    res_retry = await uc.execute(today)
    assert res_retry["task_snapshots"] == 2
    assert res_retry["project_snapshots"] == 1


@pytest.mark.asyncio
async def test_backfill_uses_status_history_and_is_append_only(
    db_session: AsyncSession,
) -> None:
    from sqlalchemy import select

    from taskflow.adapters.persistence.models import (
        DailyTaskSnapshotORM,
        TaskStatusHistoryORM,
    )

    task_id = uuid.uuid4()
    target = date(2026, 8, 2)
    task = TaskORM(
        id=task_id,
        title="Historical",
        status="done",
        created_at=datetime(2026, 8, 1, 9),
        completed_at=datetime(2026, 8, 3, 10),
    )
    history = TaskStatusHistoryORM(
        id=uuid.uuid4(),
        task_id=task_id,
        from_status="in_progress",
        to_status="done",
        actor="user",
        created_at=datetime(2026, 8, 3, 10),
    )
    db_session.add_all([task, history])
    await db_session.commit()

    use_case = BuildDailySnapshotsUseCase(db_session, SqlAlchemyUnitOfWork(db_session))
    await use_case.execute(target)
    snapshot = (
        await db_session.execute(
            select(DailyTaskSnapshotORM).where(
                DailyTaskSnapshotORM.snapshot_date == target,
                DailyTaskSnapshotORM.task_id == task_id,
            )
        )
    ).scalar_one()
    assert snapshot.status == "in_progress"

    task.status = "cancelled"
    await db_session.commit()
    await use_case.execute(target)
    same_snapshot = (
        await db_session.execute(
            select(DailyTaskSnapshotORM).where(
                DailyTaskSnapshotORM.snapshot_date == target,
                DailyTaskSnapshotORM.task_id == task_id,
            )
        )
    ).scalar_one()
    assert same_snapshot.status == "in_progress"
