"""Router FastAPI para o Motor de Métricas e Cockpit Analítico — RF-I e RF-J."""

import uuid
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taskflow.adapters.persistence.models import MetricValueORM
from taskflow.adapters.persistence.unit_of_work import SqlAlchemyUnitOfWork
from taskflow.application.use_cases.build_daily_snapshots import BuildDailySnapshotsUseCase
from taskflow.application.use_cases.compute_metrics import ComputeMetricsUseCase
from taskflow.application.use_cases.generate_narrative_insight import GenerateNarrativeInsightUseCase
from taskflow.config.container import get_db_session, get_llm_provider

router = APIRouter(prefix="/api/analytics", tags=["Analytics & Cockpit"])


class ComputeMetricsRequest(BaseModel):
    start_date: str | None = None
    end_date: str | None = None
    project_id: uuid.UUID | None = None


class GenerateInsightRequest(BaseModel):
    scope: str = "cockpit"
    scope_id: uuid.UUID | None = None


@router.get("/metrics")
async def get_latest_metrics(
    metric_id: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    stmt = select(MetricValueORM).order_by(MetricValueORM.computed_at.desc())
    if metric_id:
        stmt = stmt.where(MetricValueORM.metric_id == metric_id)
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
            "is_suppressed": o.is_suppressed,
            "sample_size": o.sample_size,
            "computed_at": o.computed_at.isoformat(),
        }
        for o in orms
    ]


@router.post("/snapshots")
async def build_snapshots(
    snapshot_date: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    target_dt = date.fromisoformat(snapshot_date) if snapshot_date else date.today()
    uow = SqlAlchemyUnitOfWork(session)
    uc = BuildDailySnapshotsUseCase(session, uow)
    res = await uc.execute(target_dt)
    return {"status": "success", "result": res}


@router.post("/compute")
async def compute_metrics(
    req: ComputeMetricsRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    start_dt = date.fromisoformat(req.start_date) if req.start_date else (date.today() - timedelta(days=7))
    end_dt = date.fromisoformat(req.end_date) if req.end_date else date.today()

    uow = SqlAlchemyUnitOfWork(session)
    uc = ComputeMetricsUseCase(session, uow)
    results = await uc.execute(start_dt, end_dt, project_id=req.project_id)
    return {"status": "success", "computed_metrics": len(results), "data": results}


@router.post("/insights")
async def generate_insight(
    req: GenerateInsightRequest,
    session: AsyncSession = Depends(get_db_session),
    llm=Depends(get_llm_provider),
) -> dict[str, Any]:
    uow = SqlAlchemyUnitOfWork(session)
    uc = GenerateNarrativeInsightUseCase(session, uow, llm)
    result = await uc.execute(scope=req.scope, scope_id=req.scope_id)
    return {"status": "success", "insight": result}
