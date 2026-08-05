"""Router FastAPI para Alertas e Registro de Decisões (Decision Log)."""

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taskflow.adapters.persistence.models import AlertORM, DecisionLogORM, MetricValueORM
from taskflow.domain.policies.alert_rule_engine import AlertRuleEngine
from taskflow.config.container import get_db_session

router = APIRouter(prefix="/api", tags=["Alerts & Decisions"])


class DecisionCreateRequest(BaseModel):
    title: str = Field(..., description="Título curto da decisão gerencial tomada")
    decision_text: str = Field(..., description="Descrição detalhada da ação/decisão")
    rationale: str | None = Field(None, description="Justificativa técnica/estratégica")
    project_id: uuid.UUID | None = None
    area_id: uuid.UUID | None = None
    expected_impact: str | None = None


@router.get("/alerts")
async def list_alerts(session: AsyncSession = Depends(get_db_session)) -> list[dict[str, Any]]:
    # Buscar últimos alertas gravados
    stmt = select(AlertORM).order_by(AlertORM.created_at.desc()).limit(20)
    res = await session.execute(stmt)
    orms = res.scalars().all()

    if not orms:
        # Se não existirem gravados, calcular dinamicamente a partir das últimas métricas
        stmt_m = select(MetricValueORM).order_by(MetricValueORM.computed_at.desc()).limit(30)
        res_m = await session.execute(stmt_m)
        metric_values = res_m.scalars().all()

        m_data = [{"metric_id": mv.metric_id, "value": float(mv.value)} for mv in metric_values if mv.value is not None]
        eval_alerts = AlertRuleEngine.evaluate_metrics(m_data)

        # Salvar no banco
        for a in eval_alerts:
            rule_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, a.rule_id)
            orm_a = AlertORM(
                id=a.id,
                rule_id=rule_uuid,
                severity=a.severity,
                explanation=a.message,
                status=a.status,
            )
            session.add(orm_a)
        await session.commit()

        return [
            {
                "id": str(a.id),
                "rule_id": a.rule_id,
                "severity": a.severity,
                "title": a.title,
                "message": a.message,
                "status": a.status,
                "created_at": a.created_at.isoformat(),
            }
            for a in eval_alerts
        ]

    return [
        {
            "id": str(o.id),
            "rule_id": o.rule_id,
            "severity": o.severity,
            "title": o.title,
            "message": o.message,
            "status": o.status,
            "created_at": o.created_at.isoformat(),
        }
        for o in orms
    ]


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)
) -> dict[str, Any]:
    orm = await session.get(AlertORM, alert_id)
    if not orm:
        raise HTTPException(status_code=404, detail="Alerta não encontrado.")

    orm.status = "acknowledged"
    orm.acknowledged_at = datetime.utcnow()
    await session.commit()

    return {"status": "success", "message": f"Alerta {alert_id} reconhecido com sucesso."}


@router.get("/decisions")
async def list_decisions(session: AsyncSession = Depends(get_db_session)) -> list[dict[str, Any]]:
    stmt = select(DecisionLogORM).order_by(DecisionLogORM.created_at.desc())
    res = await session.execute(stmt)
    orms = res.scalars().all()

    return [
        {
            "id": str(o.id),
            "title": o.title,
            "context": o.context,
            "decision": o.decision,
            "expected_outcome": o.expected_outcome,
            "project_id": str(o.project_id) if o.project_id else None,
            "created_at": o.created_at.isoformat(),
        }
        for o in orms
    ]


@router.post("/decisions", status_code=201)
async def create_decision(
    req: DecisionCreateRequest, session: AsyncSession = Depends(get_db_session)
) -> dict[str, Any]:
    orm = DecisionLogORM(
        id=uuid.uuid4(),
        title=req.title,
        context=req.rationale or req.title,
        decision=req.decision_text,
        expected_outcome=req.expected_impact,
        project_id=req.project_id,
        created_at=datetime.utcnow(),
    )
    session.add(orm)
    await session.commit()

    return {"status": "success", "id": str(orm.id), "title": orm.title}
