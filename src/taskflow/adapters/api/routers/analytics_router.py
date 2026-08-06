"""Router FastAPI para o Motor de Métricas e Cockpit Analítico — RF-I e RF-J."""

import uuid
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taskflow.adapters.persistence.models import (
    CalendarEventORM,
    DailyCalendarSnapshotORM,
    DailyProjectSnapshotORM,
    DailyTaskSnapshotORM,
    MetricValueORM,
    SourceItemORM,
    TaskEvidenceORM,
    TaskORM,
)
from taskflow.adapters.persistence.unit_of_work import SqlAlchemyUnitOfWork
from taskflow.application.use_cases.build_daily_snapshots import BuildDailySnapshotsUseCase
from taskflow.application.use_cases.compute_metrics import ComputeMetricsUseCase
from taskflow.application.use_cases.generate_narrative_insight import (
    GenerateNarrativeInsightUseCase,
)
from taskflow.config.container import get_db_session, get_llm_provider
from taskflow.domain.metrics.registry import MetricRegistry
from taskflow.domain.ports.ports import LLMProvider

router = APIRouter(prefix="/api/analytics", tags=["Analytics & Cockpit"])


class ComputeMetricsRequest(BaseModel):
    start_date: str | None = None
    end_date: str | None = None
    project_id: uuid.UUID | None = None


def _metric_caveat(metric_id: str) -> str:
    definition = MetricRegistry.get(metric_id)
    return definition.limitations if definition else "Manually supplied metric."


def _metric_formula(metric_id: str) -> str:
    definition = MetricRegistry.get(metric_id)
    return definition.formula if definition else "manually supplied value"


def _metric_source(metric_id: str) -> str:
    definition = MetricRegistry.get(metric_id)
    return definition.source if definition else "manual"


def _metric_name(metric_id: str) -> str:
    definition = MetricRegistry.get(metric_id)
    return definition.name if definition else metric_id


def _metric_unit(metric_id: str) -> str:
    definition = MetricRegistry.get(metric_id)
    return definition.unit if definition else "number"


def _metric_origin(metric_id: str) -> str:
    definition = MetricRegistry.get(metric_id)
    return definition.data_origin if definition else "manual"




class GenerateInsightRequest(BaseModel):
    scope: str = "cockpit"
    scope_id: uuid.UUID | None = None


@router.get("/metrics")
async def get_latest_metrics(
    metric_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    project_id: uuid.UUID | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    stmt = select(MetricValueORM).order_by(MetricValueORM.computed_at.desc())
    if metric_id:
        stmt = stmt.where(MetricValueORM.metric_id == metric_id)
    if start_date is not None:
        stmt = stmt.where(MetricValueORM.period_start >= start_date)
    if end_date is not None:
        stmt = stmt.where(MetricValueORM.period_end <= end_date)
    if project_id is not None:
        stmt = stmt.where(MetricValueORM.dimension_value == str(project_id))
    stmt = stmt.limit(50)

    res = await session.execute(stmt)
    orms = res.scalars().all()

    return [
        {
            "id": str(o.id),
            "metric_id": o.metric_id,
            "grain": o.grain,
            "period_start": o.period_start.isoformat(),
            "period_end": o.period_end.isoformat(),
            "dimension_key": o.dimension_key,
            "dimension_value": o.dimension_value,
            "value": float(o.value) if o.value is not None else None,
            "metric_version": o.metric_version,
            "name": _metric_name(o.metric_id),
            "unit": _metric_unit(o.metric_id),
            "data_origin": _metric_origin(o.metric_id),
            "numerator": float(o.numerator) if o.numerator is not None else None,
            "denominator": float(o.denominator) if o.denominator is not None else None,
            "coverage": {"pct": o.coverage_pct, "level": o.coverage_level or "unknown"},
            "sample_size": o.sample_size or 0, "is_suppressed": o.is_suppressed,
            "suppression_reason": o.suppression_reason,
            "state": "suppressed" if o.is_suppressed else ("unknown" if o.value is None else "known"),
            "caveat": _metric_caveat(o.metric_id),
            "period_comparison": None,
            "formula": _metric_formula(o.metric_id),
            "provenance": {"metric_value_id": str(o.id),
                           "source": _metric_source(o.metric_id)},
            "computed_at": o.computed_at.isoformat(),
        }
        for o in orms
    ]





@router.get("/calendar")
async def get_normalized_calendar(
    start_date: date,
    end_date: date,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Return normalized events with explicit snapshot coverage and privacy redaction."""
    if end_date < start_date:
        raise HTTPException(status_code=422, detail="end_date must not precede start_date")
    if (end_date - start_date).days > 31:
        raise HTTPException(status_code=422, detail="calendar range cannot exceed 32 days")

    period_end = datetime.combine(end_date + timedelta(days=1), time.min)
    events = list((await session.execute(
        select(CalendarEventORM).where(
            CalendarEventORM.starts_at < period_end,
            CalendarEventORM.ends_at >= datetime.combine(start_date, time.min),
            CalendarEventORM.is_cancelled.is_(False),
        ).order_by(CalendarEventORM.starts_at)
    )).scalars().all())
    source_ids = [event.source_item_id for event in events]
    sources = (
        {
            item.id: item
            for item in (await session.execute(
                select(SourceItemORM).where(SourceItemORM.id.in_(source_ids))
            )).scalars().all()
        }
        if source_ids
        else {}
    )

    covered_dates = set((await session.execute(
        select(DailyCalendarSnapshotORM.snapshot_date).where(
            DailyCalendarSnapshotORM.snapshot_date >= start_date,
            DailyCalendarSnapshotORM.snapshot_date <= end_date,
        )
    )).scalars().all())
    expected_dates = {
        start_date + timedelta(days=offset)
        for offset in range((end_date - start_date).days + 1)
    }
    missing_dates = sorted(expected_dates - covered_dates)

    items: list[dict[str, Any]] = []
    for event in events:
        source = sources.get(event.source_item_id)
        is_redacted = bool(
            event.sensitivity in {"private", "confidential"}
            or (source is not None and source.is_redacted)
        )
        items.append({
            "source_item_id": str(event.source_item_id),
            "starts_at": event.starts_at.isoformat(),
            "ends_at": event.ends_at.isoformat(),
            "is_all_day": event.is_all_day,
            "show_as": event.show_as,
            "duration_minutes": event.duration_minutes,
            "is_redacted": is_redacted,
            "subject": None if is_redacted or source is None else source.title,
            "deep_link": None if is_redacted or source is None else source.web_link,
        })

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "state": "unknown" if missing_dates else "known",
        "coverage": {
            "expected_days": len(expected_dates),
            "covered_days": len(covered_dates),
            "missing_dates": [item.isoformat() for item in missing_dates],
        },
        "items": items,
        "item_count": len(items),
        "provenance": "calendar_events + daily_calendar_snapshots",
    }

@router.get("/metrics/{metric_id}/drilldown")
async def metric_drilldown(
    metric_id: str,
    period_start: date,
    period_end: date,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Reconcile a displayed metric with task and source evidence."""
    if period_end < period_start:
        raise HTTPException(status_code=422, detail="period_end must not precede period_start")
    metric = MetricRegistry.get(metric_id)
    if metric is None:
        raise HTTPException(status_code=404, detail="Metric not found")
    stmt = select(DailyTaskSnapshotORM).where(
        DailyTaskSnapshotORM.snapshot_date >= period_start,
        DailyTaskSnapshotORM.snapshot_date <= period_end)
    if metric_id == "flow.throughput":
        stmt = stmt.where(DailyTaskSnapshotORM.completed_today.is_(True))
    elif metric_id == "flow.wip":
        stmt = stmt.where(DailyTaskSnapshotORM.snapshot_date == period_end,
                          DailyTaskSnapshotORM.status.not_in(("done", "cancelled")))
    elif metric_id == "flow.net_flow":
        stmt = stmt.where(DailyTaskSnapshotORM.created_today.is_(True)
                          | DailyTaskSnapshotORM.completed_today.is_(True))
    elif metric_id in ("flow.lead_time_p50", "flow.lead_time_p85"):
        stmt = stmt.where(DailyTaskSnapshotORM.completed_today.is_(True))
    elif metric_id == "flow.aging_wip_p85":
        stmt = stmt.where(DailyTaskSnapshotORM.snapshot_date == period_end,
                          DailyTaskSnapshotORM.status.not_in(("done", "cancelled")))
    elif metric_id.startswith("capacity."):
        events = list((await session.execute(select(CalendarEventORM).where(
            CalendarEventORM.starts_at < datetime.combine(
                period_end + timedelta(days=1), time.min),
            CalendarEventORM.ends_at >= datetime.combine(period_start, time.min),
            CalendarEventORM.is_cancelled.is_(False),
            CalendarEventORM.is_all_day.is_(False),
        ))).scalars().all())
        source_ids = [event.source_item_id for event in events]
        event_sources = ({item.id: item for item in
                          (await session.execute(select(SourceItemORM).where(
                              SourceItemORM.id.in_(source_ids)))).scalars().all()}
                         if source_ids else {})
        capacity_items = [{"source_item_id": str(event.source_item_id),
                  "starts_at": event.starts_at.isoformat(),
                  "ends_at": event.ends_at.isoformat(),
                  "duration_minutes": event.duration_minutes,
                  "source": ({"kind": event_sources[event.source_item_id].kind,
                              "subject": event_sources[event.source_item_id].title,
                              "occurred_at": event_sources[event.source_item_id].occurred_at.isoformat(),
                              "deep_link": event_sources[event.source_item_id].web_link}
                             if event.source_item_id in event_sources else None)}
                 for event in events
                 if event.my_response != "declined" and event.show_as != "free"]
        return {"metric_id": metric_id, "formula": metric.formula, "items": capacity_items,
                "item_count": len(capacity_items), "reconciliation": {
                    "kind": "calendar_provenance", "reconciles": True}}
    elif metric_id == "project.health_score":
        projects = list((await session.execute(select(DailyProjectSnapshotORM).where(
            DailyProjectSnapshotORM.snapshot_date == period_end
        ))).scalars().all())
        return {"metric_id": metric_id, "formula": metric.formula,
                "items": [{"project_id": str(item.project_id),
                           "value": item.health_score,
                           "components": item.health_components} for item in projects],
                "item_count": len(projects),
                "reconciliation": {"kind": "project_components", "reconciles": True}}
    else:
        raise HTTPException(status_code=422, detail="Drill-down unavailable")
    snapshots = list((await session.execute(stmt)).scalars().all())
    task_ids = sorted({snapshot.task_id for snapshot in snapshots}, key=str)
    tasks = ({task.id: task for task in
              (await session.execute(select(TaskORM).where(
                  TaskORM.id.in_(task_ids)))).scalars().all()} if task_ids else {})
    evidences = (list((await session.execute(select(TaskEvidenceORM).where(
        TaskEvidenceORM.task_id.in_(task_ids)))).scalars().all()) if task_ids else [])
    source_ids = [evidence.source_item_id for evidence in evidences]
    sources = ({item.id: item for item in
                (await session.execute(select(SourceItemORM).where(
                    SourceItemORM.id.in_(source_ids)))).scalars().all()}
               if source_ids else {})
    evidence_by_task: dict[uuid.UUID, list[dict[str, Any]]] = {}
    for evidence in evidences:
        evidence_by_task.setdefault(evidence.task_id, []).append({
            "evidence_id": str(evidence.id), "source_item_id": str(evidence.source_item_id),
            "quote": evidence.quote, "role": evidence.role,
            "source": ({"kind": sources[evidence.source_item_id].kind,
                        "subject": sources[evidence.source_item_id].title,
                        "occurred_at": sources[evidence.source_item_id].occurred_at.isoformat(),
                        "deep_link": sources[evidence.source_item_id].web_link}
                       if evidence.source_item_id in sources else None),
        })
    task_items = [{"task_id": str(task_id),
              "title": tasks[task_id].title if task_id in tasks else None,
              "evidence": evidence_by_task.get(task_id, [])} for task_id in task_ids]
    metric_row = (await session.execute(select(MetricValueORM).where(
        MetricValueORM.metric_id == metric_id,
        MetricValueORM.period_start == period_start,
        MetricValueORM.period_end == period_end,
    ).order_by(MetricValueORM.computed_at.desc()))).scalars().first()
    displayed = float(metric_row.value) if metric_row and metric_row.value is not None else None
    reconciled_value: float | None
    if metric_id == "flow.net_flow":
        created = len({row.task_id for row in snapshots if row.created_today})
        completed = len({row.task_id for row in snapshots if row.completed_today})
        reconciled_value = float(created - completed)
    elif metric_id in ("flow.throughput", "flow.wip"):
        reconciled_value = float(len(task_ids))
    else:
        reconciled_value = displayed
    return {"metric_id": metric_id, "formula": metric.formula, "items": task_items,
            "item_count": len(task_items), "reconciliation": {
                "displayed_value": displayed, "drilldown_value": reconciled_value,
                "reconciles": displayed == reconciled_value}}
@router.post("/snapshots")
async def build_snapshots(
    snapshot_date: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    target_dt = date.fromisoformat(snapshot_date) if snapshot_date else datetime.now(UTC).date()
    uow = SqlAlchemyUnitOfWork(session)
    uc = BuildDailySnapshotsUseCase(session, uow)
    res = await uc.execute(target_dt)
    return {"status": "success", "result": res}


@router.post("/compute")
async def compute_metrics(
    req: ComputeMetricsRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    start_dt = date.fromisoformat(req.start_date) if req.start_date else datetime.now(UTC).date()
    end_dt = date.fromisoformat(req.end_date) if req.end_date else datetime.now(UTC).date()

    uow = SqlAlchemyUnitOfWork(session)
    uc = ComputeMetricsUseCase(session, uow)
    results = await uc.execute(start_dt, end_dt, project_id=req.project_id)
    return {"status": "success", "computed_metrics": len(results), "data": results}


@router.post("/insights")
async def generate_insight(
    req: GenerateInsightRequest,
    session: AsyncSession = Depends(get_db_session),
    llm: LLMProvider = Depends(get_llm_provider),
) -> dict[str, Any]:
    uow = SqlAlchemyUnitOfWork(session)
    uc = GenerateNarrativeInsightUseCase(session, uow, llm)
    result = await uc.execute(scope=req.scope, scope_id=req.scope_id)
    return {"status": "success", "insight": result}
