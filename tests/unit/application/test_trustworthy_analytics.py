"""M2 acceptance tests for trustworthy analytics."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from taskflow.adapters.persistence.models import (
    Base,
    DailyCalendarSnapshotORM,
    DailyTaskSnapshotORM,
    DecisionLogORM,
    MetricValueORM,
)
from taskflow.adapters.persistence.unit_of_work import SqlAlchemyUnitOfWork
from taskflow.application.use_cases.metric_engine import (
    ComputeMetricsUseCase,
    MissingSnapshotError,
)
from taskflow.application.use_cases.narrative_generator import GenerateNarrativeInsightUseCase
from taskflow.application.use_cases.one_pager_builder import GenerateOnePagerUseCase
from tests.fakes import FakeLLMProvider


@pytest.fixture
async def analytics_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


def _snapshot(
    today: date,
    *,
    status: str,
    age: int,
    completed: bool = False,
    created: bool = False,
    area_id: uuid.UUID | None = None,
) -> DailyTaskSnapshotORM:
    return DailyTaskSnapshotORM(
        snapshot_date=today, task_id=uuid.uuid4(), status=status,
        age_days=age, days_in_status=age, completed_today=completed,
        created_today=created, requester_area_id=area_id,
        cum_days_open=age, cum_days_in_progress=0,
        cum_days_waiting=0, cum_days_blocked=0,
    )


@pytest.mark.asyncio
async def test_formulas_envelope_unknown_and_suppression(
    analytics_session: AsyncSession,
) -> None:
    today = date(2026, 8, 5)
    area_id = uuid.uuid4()
    analytics_session.add_all([
        DailyCalendarSnapshotORM(
            snapshot_date=today, total_meeting_minutes=120,
            meeting_count=4, available_minutes=480),
        _snapshot(today, status="done", age=5, completed=True,
                  created=True, area_id=area_id),
        _snapshot(today, status="in_progress", age=10, area_id=area_id),
    ])
    await analytics_session.commit()
    use_case = ComputeMetricsUseCase(
        analytics_session, SqlAlchemyUnitOfWork(analytics_session))
    results = await use_case.execute(today, today)
    by_id = {item["metric_id"]: item for item in results}

    assert by_id["flow.throughput"]["value"] == 1.0
    assert by_id["flow.net_flow"]["value"] == 0.0
    assert by_id["capacity.meeting_ratio"]["value"] == 25.0
    assert by_id["flow.lead_time_p50"]["value"] == 5.0
    assert by_id["project.health_score"]["state"] == "unknown"
    assert by_id["project.health_score"]["value"] is None
    assert by_id["flow.throughput"]["coverage"] == {"pct": 100.0, "level": "high"}
    assert by_id["flow.throughput"]["provenance"]["record_ids"]

    area_results = await use_case.execute(today, today, area_id=area_id)
    area_throughput = next(
        item for item in area_results if item["metric_id"] == "flow.throughput")
    assert area_throughput["state"] == "suppressed"
    assert area_throughput["value"] is None
    assert area_throughput["sample_size"] == 1


@pytest.mark.asyncio
async def test_metrics_abort_without_complete_snapshot(
    analytics_session: AsyncSession,
) -> None:
    use_case = ComputeMetricsUseCase(
        analytics_session, SqlAlchemyUnitOfWork(analytics_session))
    with pytest.raises(MissingSnapshotError):
        await use_case.execute(date(2026, 8, 5), date(2026, 8, 5))


class HallucinatingLLM(FakeLLMProvider):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    async def draft_follow_up(
        self, task: dict[str, Any], context: dict[str, Any], tone: str,
    ) -> str:
        self.calls += 1
        return "Unsupported result: 999."


@pytest.mark.asyncio
async def test_narrative_retries_once_then_suppresses(
    analytics_session: AsyncSession,
) -> None:
    today = date(2026, 8, 5)
    analytics_session.add(MetricValueORM(
        id=uuid.uuid4(), metric_id="flow.throughput", metric_version=1,
        grain="daily", period_start=today, period_end=today,
        dimension_key="_total", value=10, sample_size=10,
        coverage_pct=100.0, coverage_level="high", is_suppressed=False,
    ))
    await analytics_session.commit()
    llm = HallucinatingLLM()
    use_case = GenerateNarrativeInsightUseCase(
        analytics_session, SqlAlchemyUnitOfWork(analytics_session), llm)
    result = await use_case.execute("cockpit", period_start=today, period_end=today)
    assert llm.calls == 2
    assert result["is_suppressed"] is True
    assert result["narrative_text"] is None
    assert result["discrepancies"] == [999.0]


@pytest.mark.asyncio
async def test_one_pager_omits_unsupported_free_text_numbers(
    analytics_session: AsyncSession,
) -> None:
    today = date(2026, 8, 5)
    analytics_session.add_all([
        MetricValueORM(
            id=uuid.uuid4(), metric_id="flow.throughput", metric_version=1,
            grain="daily", period_start=today, period_end=today,
            dimension_key="_total", value=10, sample_size=10,
            coverage_pct=100.0, coverage_level="high", is_suppressed=False),
        DecisionLogORM(
            id=uuid.uuid4(), title="Plan 999", context="context",
            decision="decision", created_at=datetime.utcnow()),
    ])
    await analytics_session.commit()
    result = await GenerateOnePagerUseCase(
        analytics_session, SqlAlchemyUnitOfWork(analytics_session)
    ).execute(period_start=today, period_end=today)
    assert result["is_grounded"] is True
    assert "999" not in result["markdown"]
    assert "10.0" in result["markdown"]
