"""Use Case: ComputeMetricsUseCase — UC-Analytics-2.

Executa o cálculo determinístico (100% Python/SQL sem LLM) de todas as métricas do catálogo
salvando os resultados em `metric_values` com envelope de procedência completo.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date, datetime, timedelta
import math
import statistics
from typing import Any
import structlog
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from taskflow.adapters.persistence.models import (
    DailyCalendarSnapshotORM,
    DailyProjectSnapshotORM,
    DailyTaskSnapshotORM,
    MetricValueORM,
)
from taskflow.domain.metrics.ethics_guard import EthicsGuard
from taskflow.domain.metrics.registry import MetricRegistry
from taskflow.domain.metrics.suppression_policy import SuppressionPolicy
from taskflow.domain.ports.ports import UnitOfWork

log = structlog.get_logger()


def _calculate_percentile(values: Sequence[float | int], percentile: float) -> float:
    """Calcula o percentil determinístico usando interpolação linear pura em Python."""
    if not values:
        return 0.0
    sorted_v = sorted(values)
    k = (len(sorted_v) - 1) * (percentile / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(sorted_v[int(k)])
    d0 = sorted_v[int(f)] * (c - k)
    d1 = sorted_v[int(c)] * (k - f)
    return float(d0 + d1)



class ComputeMetricsUseCase:
    """UC-Analytics-2 — Motor Determinístico de Métricas."""

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
        log.info("metrics.compute.start", start=start_date.isoformat(), end=end_date.isoformat())

        results = []
        async with self._uow:
            # 1. Throughput
            tp = await self._compute_throughput(start_date, end_date, project_id)
            results.append(tp)

            # 2. Net Flow
            nf = await self._compute_net_flow(start_date, end_date, project_id)
            results.append(nf)

            # 3. WIP
            wip = await self._compute_wip(end_date, project_id)
            results.append(wip)

            # 4. Lead Time p50 / p85
            lt50, lt85 = await self._compute_lead_times(start_date, end_date, project_id)
            results.extend([lt50, lt85])

            # 5. Aging WIP p85
            aging = await self._compute_aging_wip_p85(end_date, project_id)
            results.append(aging)

            # 6. Meeting Hours & Ratio
            mh, mr = await self._compute_meeting_metrics(start_date, end_date)
            results.extend([mh, mr])

            # 7. Context Switches
            cs = await self._compute_context_switches(start_date, end_date)
            results.append(cs)

            # 8. Project Health Score
            phs = await self._compute_project_health_score(end_date)
            results.append(phs)

            await self._uow.commit()

        log.info("metrics.compute.completed", count=len(results))
        return results

    async def _save_metric_value(
        self,
        metric_id: str,
        metric_date: date,
        val: float | None,
        sample_size: int,
        is_suppressed: bool = False,
        area_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        # Aplicar Guardião Ético
        EthicsGuard.validate_metric_query(metric_id)

        # Aplicar Supressão se aplicável (apenas para agregações por área/grupo)
        sup = SuppressionPolicy.apply(val, sample_size, is_group_metric=bool(area_id))
        final_val = sup.value
        is_suppressed_final = sup.is_suppressed

        dim_key = "_total"
        dim_val = None
        if project_id:
            dim_key = "project_id"
            dim_val = str(project_id)
        elif area_id:
            dim_key = "area_id"
            dim_val = str(area_id)

        # Deletar pré-existente para garantir idempotência do cálculo diário
        await self._session.execute(
            delete(MetricValueORM).where(
                MetricValueORM.metric_id == metric_id,
                MetricValueORM.metric_version == 1,
                MetricValueORM.grain == "daily",
                MetricValueORM.period_start == metric_date,
                MetricValueORM.dimension_key == dim_key,
            )
        )

        orm = MetricValueORM(
            id=uuid.uuid4(),
            metric_id=metric_id,
            metric_version=1,
            grain="daily",
            period_start=metric_date,
            period_end=metric_date,
            dimension_key=dim_key,
            dimension_value=dim_val,
            value=final_val,
            is_suppressed=is_suppressed_final,
            sample_size=sample_size,
            computed_at=datetime.utcnow(),
        )
        self._session.add(orm)
        return {
            "metric_id": metric_id,
            "value": final_val,
            "is_suppressed": is_suppressed_final,
            "sample_size": sample_size,
        }

    async def _compute_throughput(
        self, start_date: date, end_date: date, project_id: uuid.UUID | None
    ) -> dict[str, Any]:
        stmt = select(func.count()).select_from(DailyTaskSnapshotORM).where(
            DailyTaskSnapshotORM.snapshot_date >= start_date,
            DailyTaskSnapshotORM.snapshot_date <= end_date,
            DailyTaskSnapshotORM.completed_today == True,
        )
        if project_id:
            stmt = stmt.where(DailyTaskSnapshotORM.project_id == project_id)
        res = await self._session.execute(stmt)
        count = res.scalar() or 0
        return await self._save_metric_value("flow.throughput", end_date, float(count), sample_size=count, project_id=project_id)

    async def _compute_net_flow(
        self, start_date: date, end_date: date, project_id: uuid.UUID | None
    ) -> dict[str, Any]:
        stmt_created = select(func.count()).select_from(DailyTaskSnapshotORM).where(
            DailyTaskSnapshotORM.snapshot_date >= start_date,
            DailyTaskSnapshotORM.snapshot_date <= end_date,
            DailyTaskSnapshotORM.created_today == True,
        )
        if project_id:
            stmt_created = stmt_created.where(DailyTaskSnapshotORM.project_id == project_id)

        stmt_completed = select(func.count()).select_from(DailyTaskSnapshotORM).where(
            DailyTaskSnapshotORM.snapshot_date >= start_date,
            DailyTaskSnapshotORM.snapshot_date <= end_date,
            DailyTaskSnapshotORM.completed_today == True,
        )
        if project_id:
            stmt_completed = stmt_completed.where(DailyTaskSnapshotORM.project_id == project_id)

        res_c = await self._session.execute(stmt_created)
        created = res_c.scalar() or 0

        res_comp = await self._session.execute(stmt_completed)
        completed = res_comp.scalar() or 0

        net = created - completed
        return await self._save_metric_value("flow.net_flow", end_date, float(net), sample_size=created + completed, project_id=project_id)

    async def _compute_wip(self, end_date: date, project_id: uuid.UUID | None) -> dict[str, Any]:
        stmt = select(func.count()).select_from(DailyTaskSnapshotORM).where(
            DailyTaskSnapshotORM.snapshot_date == end_date,
            DailyTaskSnapshotORM.status.not_in(["done", "cancelled"]),
        )
        if project_id:
            stmt = stmt.where(DailyTaskSnapshotORM.project_id == project_id)
        res = await self._session.execute(stmt)
        count = res.scalar() or 0
        return await self._save_metric_value("flow.wip", end_date, float(count), sample_size=count, project_id=project_id)

    async def _compute_lead_times(
        self, start_date: date, end_date: date, project_id: uuid.UUID | None
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        stmt = select(DailyTaskSnapshotORM.age_days).where(
            DailyTaskSnapshotORM.snapshot_date >= start_date,
            DailyTaskSnapshotORM.snapshot_date <= end_date,
            DailyTaskSnapshotORM.completed_today == True,
        )
        if project_id:
            stmt = stmt.where(DailyTaskSnapshotORM.project_id == project_id)

        res = await self._session.execute(stmt)
        ages = res.scalars().all()

        if not ages:
            p50_res = await self._save_metric_value("flow.lead_time_p50", end_date, 0.0, sample_size=0, project_id=project_id)
            p85_res = await self._save_metric_value("flow.lead_time_p85", end_date, 0.0, sample_size=0, project_id=project_id)
            return p50_res, p85_res

        p50 = _calculate_percentile(ages, 50.0)
        p85 = _calculate_percentile(ages, 85.0)

        p50_res = await self._save_metric_value("flow.lead_time_p50", end_date, round(p50, 1), sample_size=len(ages), project_id=project_id)
        p85_res = await self._save_metric_value("flow.lead_time_p85", end_date, round(p85, 1), sample_size=len(ages), project_id=project_id)
        return p50_res, p85_res

    async def _compute_aging_wip_p85(self, end_date: date, project_id: uuid.UUID | None) -> dict[str, Any]:
        stmt = select(DailyTaskSnapshotORM.age_days).where(
            DailyTaskSnapshotORM.snapshot_date == end_date,
            DailyTaskSnapshotORM.status.not_in(["done", "cancelled"]),
        )
        if project_id:
            stmt = stmt.where(DailyTaskSnapshotORM.project_id == project_id)

        res = await self._session.execute(stmt)
        ages = res.scalars().all()

        if not ages:
            return await self._save_metric_value("flow.aging_wip_p85", end_date, 0.0, sample_size=0, project_id=project_id)

        p85 = _calculate_percentile(ages, 85.0)
        return await self._save_metric_value("flow.aging_wip_p85", end_date, round(p85, 1), sample_size=len(ages), project_id=project_id)

    async def _compute_meeting_metrics(
        self, start_date: date, end_date: date
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        stmt = select(func.sum(DailyCalendarSnapshotORM.total_meeting_minutes)).where(
            DailyCalendarSnapshotORM.snapshot_date >= start_date,
            DailyCalendarSnapshotORM.snapshot_date <= end_date,
        )
        res = await self._session.execute(stmt)
        total_min = res.scalar() or 0

        hours = round(total_min / 60.0, 1)
        ratio = round(min(100.0, (total_min / (480.0 * max(1, (end_date - start_date).days + 1))) * 100.0), 1)

        mh = await self._save_metric_value("capacity.meeting_hours", end_date, hours, sample_size=1)
        mr = await self._save_metric_value("capacity.meeting_ratio", end_date, ratio, sample_size=1)
        return mh, mr

    async def _compute_context_switches(self, start_date: date, end_date: date) -> dict[str, Any]:
        stmt = select(func.avg(DailyCalendarSnapshotORM.meeting_count)).where(
            DailyCalendarSnapshotORM.snapshot_date >= start_date,
            DailyCalendarSnapshotORM.snapshot_date <= end_date,
        )
        res = await self._session.execute(stmt)
        avg_switches = res.scalar() or 0.0
        return await self._save_metric_value("capacity.context_switches", end_date, round(float(avg_switches), 1), sample_size=1)

    async def _compute_project_health_score(self, end_date: date) -> dict[str, Any]:
        stmt = select(func.avg(DailyProjectSnapshotORM.health_score)).where(
            DailyProjectSnapshotORM.snapshot_date == end_date
        )
        res = await self._session.execute(stmt)
        avg_score = res.scalar() or 100.0
        return await self._save_metric_value("project.health_score", end_date, round(float(avg_score), 1), sample_size=1)
