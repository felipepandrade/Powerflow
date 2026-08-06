"""Deterministic trustworthy metric engine backed only by published snapshots."""
from __future__ import annotations

import math
import uuid
from collections.abc import Sequence
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from taskflow.adapters.persistence.models import (
    DailyCalendarSnapshotORM,
    DailyProjectSnapshotORM,
    DailyTaskSnapshotORM,
    MetricValueORM,
)
from taskflow.domain.metrics.ethics_guard import EthicsGuard
from taskflow.domain.metrics.registry import MetricRegistry
from taskflow.domain.metrics.result import MetricResult, MetricState
from taskflow.domain.metrics.suppression_policy import SuppressionPolicy
from taskflow.domain.ports.ports import UnitOfWork


class MissingSnapshotError(RuntimeError):
    """Raised when a requested period has no complete daily snapshot coverage."""


def calculate_percentile(values: Sequence[float | int], percentile: float) -> float | None:
    """Linear percentile, identical across SQLite and PostgreSQL."""
    if not values:
        return None
    ordered = sorted(float(value) for value in values)
    position = (len(ordered) - 1) * percentile / 100
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


class ComputeMetricsUseCase:
    """Computes numeric values without invoking any LLM."""

    def __init__(self, session: AsyncSession, uow: UnitOfWork) -> None:
        self._session = session
        self._uow = uow

    async def execute(
        self,
        start_date: date,
        end_date: date,
        area_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
    ) -> list[dict[str, Any]]:
        if end_date < start_date:
            raise ValueError("end_date must be on or after start_date")
        covered_dates = await self._require_complete_period(start_date, end_date)
        coverage_pct = 100.0
        results: list[MetricResult] = []
        async with self._uow:
            results.append(await self._throughput(start_date, end_date, covered_dates,
                                                  coverage_pct, area_id, project_id))
            results.append(await self._net_flow(start_date, end_date, covered_dates,
                                                coverage_pct, area_id, project_id))
            results.append(await self._wip(start_date, end_date, covered_dates,
                                           coverage_pct, area_id, project_id))
            results.extend(await self._lead_times(start_date, end_date, covered_dates,
                                                  coverage_pct, area_id, project_id))
            results.append(await self._aging(start_date, end_date, covered_dates,
                                             coverage_pct, area_id, project_id))
            results.extend(await self._calendar_metrics(start_date, end_date, covered_dates,
                                                        coverage_pct))
            results.append(await self._health(start_date, end_date, covered_dates,
                                              coverage_pct, project_id))
            await self._uow.commit()
        return [result.to_dict() for result in results]

    async def _require_complete_period(self, start: date, end: date) -> tuple[str, ...]:
        rows = (await self._session.execute(
            select(DailyCalendarSnapshotORM.snapshot_date).where(
                DailyCalendarSnapshotORM.snapshot_date >= start,
                DailyCalendarSnapshotORM.snapshot_date <= end,
            )
        )).scalars().all()
        actual = set(rows)
        expected = {start + timedelta(days=offset) for offset in range((end - start).days + 1)}
        missing = sorted(expected - actual)
        if missing:
            formatted = ", ".join(item.isoformat() for item in missing)
            raise MissingSnapshotError(f"Analytics aborted: missing snapshots for {formatted}")
        return tuple(item.isoformat() for item in sorted(actual))

    def _task_filters(
        self,
        start: date,
        end: date,
        area_id: uuid.UUID | None,
        project_id: uuid.UUID | None,
    ) -> list[Any]:
        filters: list[Any] = [
            DailyTaskSnapshotORM.snapshot_date >= start,
            DailyTaskSnapshotORM.snapshot_date <= end,
        ]
        if area_id is not None:
            filters.append(DailyTaskSnapshotORM.requester_area_id == area_id)
        if project_id is not None:
            filters.append(DailyTaskSnapshotORM.project_id == project_id)
        return filters

    async def _persist(self, result: MetricResult) -> MetricResult:
        definition = result.definition
        EthicsGuard.validate_metric_query(definition.id, result.dimension_key)
        await self._session.execute(delete(MetricValueORM).where(
            MetricValueORM.metric_id == definition.id,
            MetricValueORM.metric_version == definition.version,
            MetricValueORM.grain == "custom",
            MetricValueORM.period_start == result.period_start,
            MetricValueORM.dimension_key == result.dimension_key,
        ))
        self._session.add(MetricValueORM(
            id=uuid.uuid4(), metric_id=definition.id, metric_version=definition.version,
            grain="custom", period_start=result.period_start, period_end=result.period_end,
            dimension_key=result.dimension_key, dimension_value=result.dimension_value,
            value=result.value, numerator=result.numerator, denominator=result.denominator,
            sample_size=result.sample_size, coverage_pct=result.coverage_pct,
            coverage_level=result.coverage_level, is_suppressed=result.is_suppressed,
            suppression_reason=result.suppression_reason, computed_at=datetime.utcnow(),
        ))
        return result

    async def _result(
        self,
        metric_id: str,
        start: date,
        end: date,
        value: float | None,
        numerator: float | None,
        denominator: float | None,
        sample_size: int,
        coverage_pct: float,
        provenance: tuple[str, ...],
        area_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
    ) -> MetricResult:
        definition = MetricRegistry.require(metric_id)
        dimension_key = "_total"
        dimension_value = None
        if project_id is not None:
            dimension_key, dimension_value = "project_id", str(project_id)
        elif area_id is not None:
            dimension_key, dimension_value = "area_id", str(area_id)
        suppression = SuppressionPolicy.apply(
            value, sample_size, is_group_metric=area_id is not None)
        final_value = suppression.value
        state: MetricState = "suppressed" if suppression.is_suppressed else (
            "unknown" if final_value is None else "known")
        caveat = definition.limitations
        if final_value is None and not suppression.is_suppressed:
            caveat = f"{caveat} Dados insuficientes; valor desconhecido."
        result = MetricResult(
            definition=definition, period_start=start, period_end=end, value=final_value,
            numerator=numerator, denominator=denominator, sample_size=sample_size,
            coverage_pct=coverage_pct, coverage_level="high", state=state,
            caveat=caveat, is_suppressed=suppression.is_suppressed,
            suppression_reason=suppression.suppression_reason,
            dimension_key=dimension_key, dimension_value=dimension_value,
            provenance_ids=provenance,
        )
        return await self._persist(result)

    async def _task_rows(
        self, start: date, end: date, area_id: uuid.UUID | None,
        project_id: uuid.UUID | None,
    ) -> list[DailyTaskSnapshotORM]:
        result = await self._session.execute(select(DailyTaskSnapshotORM).where(
            *self._task_filters(start, end, area_id, project_id)))
        return list(result.scalars().all())

    async def _throughput(self, start: date, end: date, covered: tuple[str, ...],
                          coverage: float, area: uuid.UUID | None,
                          project: uuid.UUID | None) -> MetricResult:
        rows = await self._task_rows(start, end, area, project)
        ids = tuple(str(row.task_id) for row in rows if row.completed_today)
        return await self._result("flow.throughput", start, end, float(len(ids)),
                                  float(len(ids)), None, len(ids), coverage, ids,
                                  area, project)

    async def _net_flow(self, start: date, end: date, covered: tuple[str, ...],
                        coverage: float, area: uuid.UUID | None,
                        project: uuid.UUID | None) -> MetricResult:
        rows = await self._task_rows(start, end, area, project)
        created = {row.task_id for row in rows if row.created_today}
        completed = {row.task_id for row in rows if row.completed_today}
        provenance = tuple(str(item) for item in sorted(created | completed, key=str))
        return await self._result("flow.net_flow", start, end,
                                  float(len(created) - len(completed)), float(len(created)),
                                  float(len(completed)), len(provenance), coverage,
                                  provenance, area, project)

    async def _wip(self, start: date, end: date, covered: tuple[str, ...],
                   coverage: float, area: uuid.UUID | None,
                   project: uuid.UUID | None) -> MetricResult:
        rows = await self._task_rows(end, end, area, project)
        ids = tuple(str(row.task_id) for row in rows if row.status not in ("done", "cancelled"))
        return await self._result("flow.wip", start, end, float(len(ids)), float(len(ids)),
                                  None, len(ids), coverage, ids, area, project)

    async def _lead_times(self, start: date, end: date, covered: tuple[str, ...],
                          coverage: float, area: uuid.UUID | None,
                          project: uuid.UUID | None) -> tuple[MetricResult, MetricResult]:
        rows = await self._task_rows(start, end, area, project)
        completed = [row for row in rows if row.completed_today]
        ages = [row.age_days for row in completed]
        ids = tuple(str(row.task_id) for row in completed)
        p50 = calculate_percentile(ages, 50)
        p85 = calculate_percentile(ages, 85)
        first = await self._result("flow.lead_time_p50", start, end,
                                   round(p50, 1) if p50 is not None else None,
                                   None, float(len(ages)), len(ages), coverage, ids, area, project)
        second = await self._result("flow.lead_time_p85", start, end,
                                    round(p85, 1) if p85 is not None else None,
                                    None, float(len(ages)), len(ages), coverage, ids, area, project)
        return first, second

    async def _aging(self, start: date, end: date, covered: tuple[str, ...],
                     coverage: float, area: uuid.UUID | None,
                     project: uuid.UUID | None) -> MetricResult:
        rows = await self._task_rows(end, end, area, project)
        opened = [row for row in rows if row.status not in ("done", "cancelled")]
        percentile = calculate_percentile([row.age_days for row in opened], 85)
        ids = tuple(str(row.task_id) for row in opened)
        return await self._result("flow.aging_wip_p85", start, end,
                                  round(percentile, 1) if percentile is not None else None,
                                  None, float(len(opened)), len(opened), coverage, ids,
                                  area, project)

    async def _calendar_metrics(
        self, start: date, end: date, covered: tuple[str, ...], coverage: float,
    ) -> tuple[MetricResult, MetricResult, MetricResult]:
        rows = list((await self._session.execute(select(DailyCalendarSnapshotORM).where(
            DailyCalendarSnapshotORM.snapshot_date >= start,
            DailyCalendarSnapshotORM.snapshot_date <= end,
        ))).scalars().all())
        meeting = float(sum(row.total_meeting_minutes or 0 for row in rows))
        available = float(sum(row.available_minutes or 0 for row in rows))
        count = float(sum(row.meeting_count or 0 for row in rows))
        hours = await self._result("capacity.meeting_hours", start, end,
                                   round(meeting / 60, 1), meeting, 60.0, len(rows),
                                   coverage, covered)
        ratio_value = round(meeting / available * 100, 1) if available > 0 else None
        ratio = await self._result("capacity.meeting_ratio", start, end, ratio_value,
                                   meeting, available, len(rows), coverage, covered)
        switch_value = round(count / len(rows), 1) if rows else None
        switches = await self._result("capacity.context_switches", start, end, switch_value,
                                      count, float(len(rows)), len(rows), coverage, covered)
        return hours, ratio, switches

    async def _health(self, start: date, end: date, covered: tuple[str, ...],
                      coverage: float, project_id: uuid.UUID | None) -> MetricResult:
        stmt = select(DailyProjectSnapshotORM).where(
            DailyProjectSnapshotORM.snapshot_date == end)
        if project_id is not None:
            stmt = stmt.where(DailyProjectSnapshotORM.project_id == project_id)
        rows = list((await self._session.execute(stmt)).scalars().all())
        known = [float(row.health_score) for row in rows if row.health_score is not None]
        value = round(sum(known) / len(known), 1) if known else None
        ids = tuple(str(row.project_id) for row in rows if row.health_score is not None)
        return await self._result("project.health_score", start, end, value,
                                  sum(known) if known else None, float(len(known)),
                                  len(known), coverage, ids, project_id=project_id)
