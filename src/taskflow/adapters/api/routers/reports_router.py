"""Router FastAPI para Relatórios Executivos, Entrada Manual de Indicadores e Import/Export — Épico K."""

import csv
import io
import uuid
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taskflow.adapters.persistence.models import MetricValueORM, TaskORM
from taskflow.adapters.persistence.unit_of_work import SqlAlchemyUnitOfWork
from taskflow.application.use_cases.generate_one_pager import GenerateOnePagerUseCase
from taskflow.config.container import get_db_session

router = APIRouter(prefix="/api/reports", tags=["Reports & Import/Export"])


class ManualMetricRequest(BaseModel):
    metric_id: str = Field(..., description="Identificador da métrica manual (ex: manual.nps_cliente)")
    value: float = Field(..., description="Valor numérico do indicador")
    dimension_key: str = "_total"
    dimension_value: str | None = None
    note: str | None = Field(None, description="Justificativa / contexto do indicador manual")


@router.get("/one-pager")
async def get_one_pager(
    project_id: uuid.UUID | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    uow = SqlAlchemyUnitOfWork(session)
    uc = GenerateOnePagerUseCase(session, uow)
    return await uc.execute(project_id=project_id)


@router.post("/manual-metric", status_code=201)
async def add_manual_metric(
    req: ManualMetricRequest, session: AsyncSession = Depends(get_db_session)
) -> dict[str, Any]:
    today = date.today()
    orm = MetricValueORM(
        id=uuid.uuid4(),
        metric_id=req.metric_id,
        metric_version=1,
        grain="daily",
        period_start=today,
        period_end=today,
        dimension_key=req.dimension_key,
        dimension_value=req.dimension_value,
        value=req.value,
        is_suppressed=False,
        sample_size=1,
        suppression_reason=f"Entrada Manual: {req.note}" if req.note else "Entrada Manual",
        computed_at=datetime.utcnow(),
    )
    session.add(orm)
    await session.commit()

    return {"status": "success", "id": str(orm.id), "metric_id": orm.metric_id, "value": orm.value}


@router.get("/export/csv")
async def export_tasks_csv(session: AsyncSession = Depends(get_db_session)) -> Response:
    stmt = select(TaskORM).order_by(TaskORM.created_at.desc())
    res = await session.execute(stmt)
    tasks = res.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "title", "status", "priority", "due_date", "created_at"])

    for t in tasks:
        writer.writerow([
            str(t.id),
            t.title,
            t.status,
            t.priority,
            t.due_date.isoformat() if t.due_date else "",
            t.created_at.isoformat() if t.created_at else "",
        ])

    csv_content = output.getvalue()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=taskflow_tasks_export.csv"},
    )


@router.post("/import/csv")
async def import_tasks_csv(
    file: UploadFile = File(...), session: AsyncSession = Depends(get_db_session)
) -> dict[str, Any]:
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Formato inválido. O arquivo precisa ser .csv")

    content = await file.read()
    decoded = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(decoded))

    imported_count = 0
    for row in reader:
        title = row.get("title")
        if not title:
            continue

        task_orm = TaskORM(
            id=uuid.uuid4(),
            title=title,
            description=row.get("description"),
            status=row.get("status", "inbox"),
            priority=row.get("priority", "medium"),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(task_orm)
        imported_count += 1

    await session.commit()
    return {"status": "success", "imported_tasks": imported_count}
