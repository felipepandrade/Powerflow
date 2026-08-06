"""Grounded deterministic executive one-pager."""
from __future__ import annotations

import re
import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taskflow.adapters.persistence.models import AlertORM, DecisionLogORM, MetricValueORM
from taskflow.domain.metrics.registry import MetricRegistry
from taskflow.domain.policies.narrative_guardrail_policy import NarrativeGuardrailPolicy
from taskflow.domain.ports.ports import UnitOfWork


class GenerateOnePagerUseCase:
    """Render only persisted values; free text cannot introduce unsupported numbers."""

    NUMBER = re.compile(r"(?<![\w])[-+]?\d+(?:[.,]\d+)?")

    def __init__(self, session: AsyncSession, uow: UnitOfWork) -> None:
        self._session = session
        self._uow = uow

    async def execute(
        self,
        project_id: uuid.UUID | None = None,
        period_start: date | None = None,
        period_end: date | None = None,
    ) -> dict[str, Any]:
        metric_stmt = select(MetricValueORM).order_by(
            MetricValueORM.computed_at.desc()).limit(20)
        if project_id is not None:
            metric_stmt = metric_stmt.where(
                MetricValueORM.dimension_key == "project_id",
                MetricValueORM.dimension_value == str(project_id))
        if period_start is not None:
            metric_stmt = metric_stmt.where(MetricValueORM.period_start >= period_start)
        if period_end is not None:
            metric_stmt = metric_stmt.where(MetricValueORM.period_end <= period_end)
        metrics = list((await self._session.execute(metric_stmt)).scalars().all())
        alerts = list((await self._session.execute(select(AlertORM).where(
            AlertORM.status == "open").order_by(AlertORM.created_at.desc()).limit(5)
        )).scalars().all())
        decisions = list((await self._session.execute(select(DecisionLogORM).order_by(
            DecisionLogORM.created_at.desc()).limit(5))).scalars().all())
        evidence = [float(metric.value) for metric in metrics
                    if metric.value is not None and not metric.is_suppressed]
        lines = ["# Powerflow executive one-pager", "", "## Grounded metrics"]
        for metric in metrics:
            definition = MetricRegistry.get(metric.metric_id)
            label = definition.name if definition else metric.metric_id
            if metric.is_suppressed:
                rendered = "suppressed"
            elif metric.value is None:
                rendered = "unknown"
            else:
                rendered = str(float(metric.value))
            lines.append(f"- **{label}**: {rendered}")
        lines.extend(["", "## Open alerts"])
        lines.extend(f"- {self._without_numbers(alert.explanation)}" for alert in alerts)
        if not alerts:
            lines.append("- No open alert is supported by the selected data.")
        lines.extend(["", "## Recent decisions"])
        lines.extend(f"- {self._without_numbers(decision.title)}" for decision in decisions)
        if not decisions:
            lines.append("- No decision recorded for this selection.")
        markdown = "\n".join(lines)
        validation = NarrativeGuardrailPolicy.validate(markdown, evidence)
        if not validation.is_valid:
            safe_lines = lines[:3 + len(metrics)]
            markdown = "\n".join(safe_lines)
            validation = NarrativeGuardrailPolicy.validate(markdown, evidence)
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "scope": str(project_id) if project_id else "global",
            "period_start": period_start.isoformat() if period_start else None,
            "period_end": period_end.isoformat() if period_end else None,
            "markdown": markdown,
            "metrics_count": len(metrics),
            "alerts_count": len(alerts),
            "decisions_count": len(decisions),
            "is_grounded": validation.is_valid,
            "unsupported_numbers": validation.discrepancies,
            "caveat": "View limited to the workflow captured by the manager.",
        }

    @classmethod
    def _without_numbers(cls, value: str) -> str:
        return cls.NUMBER.sub("[numeric detail omitted]", value)
