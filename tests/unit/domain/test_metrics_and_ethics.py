"""Testes unitários para MetricRegistry, EthicsGuard, SuppressionPolicy e ComputeMetricsUseCase."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from taskflow.adapters.persistence.models import (
    Base,
    DailyCalendarSnapshotORM,
    DailyTaskSnapshotORM,
)
from taskflow.adapters.persistence.unit_of_work import SqlAlchemyUnitOfWork
from taskflow.application.use_cases.compute_metrics import ComputeMetricsUseCase
from taskflow.domain.metrics.ethics_guard import EthicsGuard, EthicsViolationError
from taskflow.domain.metrics.registry import MetricRegistry
from taskflow.domain.metrics.suppression_policy import SuppressionPolicy


@pytest.fixture
async def db_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


def test_metric_registry_validation() -> None:
    assert MetricRegistry.validate_all() is True
    metrics = MetricRegistry.list_all()
    assert len(metrics) >= 10


def test_ethics_guard_blocks_forbidden_queries() -> None:
    # 1. Deve permitir consulta válida por projeto ou área
    EthicsGuard.validate_metric_query("flow.throughput", group_by="project_id")

    # 2. Deve lançar exceção se tentar agrupar por pessoa/indivíduo
    with pytest.raises(EthicsViolationError):
        EthicsGuard.validate_metric_query("flow.throughput", group_by="user_id")

    with pytest.raises(EthicsViolationError):
        EthicsGuard.validate_metric_query("flow.throughput", group_by="author_email")


def test_suppression_policy_k_anonymity() -> None:
    # Amostra < 3 em grupo deve ser suprimida
    res_supp = SuppressionPolicy.apply(raw_value=45.0, sample_size=2, is_group_metric=True, k_min=3)
    assert res_supp.is_suppressed is True
    assert res_supp.value is None

    # Amostra >= 3 deve retornar o valor normal
    res_ok = SuppressionPolicy.apply(raw_value=45.0, sample_size=5, is_group_metric=True, k_min=3)
    assert res_ok.is_suppressed is False
    assert res_ok.value == 45.0


@pytest.mark.asyncio
async def test_compute_metrics_use_case(db_session: AsyncSession) -> None:
    today = datetime.now(UTC).date()

    # Inserir alguns snapshots de tarefa no dia
    snap1 = DailyTaskSnapshotORM(
        snapshot_date=today,
        task_id=uuid.uuid4(),
        status="done",
        completed_today=True,
        age_days=5,
        days_in_status=5,
        cum_days_open=5,
        cum_days_in_progress=0,
        cum_days_waiting=0,
        cum_days_blocked=0,
    )
    snap2 = DailyTaskSnapshotORM(
        snapshot_date=today,
        task_id=uuid.uuid4(),
        status="in_progress",
        completed_today=False,
        age_days=10,
        days_in_status=10,
        cum_days_open=10,
        cum_days_in_progress=10,
        cum_days_waiting=0,
        cum_days_blocked=0,
    )
    calendar = DailyCalendarSnapshotORM(snapshot_date=today, available_minutes=480)
    db_session.add_all([snap1, snap2, calendar])
    await db_session.commit()

    uow = SqlAlchemyUnitOfWork(db_session)
    uc = ComputeMetricsUseCase(db_session, uow)

    results = await uc.execute(today, today)
    assert len(results) >= 10

    # Checar throughput
    tp_res = next(r for r in results if r["metric_id"] == "flow.throughput")
    assert tp_res["value"] == 1.0
