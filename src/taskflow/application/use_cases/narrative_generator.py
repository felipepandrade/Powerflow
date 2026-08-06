"""Grounded narrative insight generation with one retry and fail-closed suppression."""
from __future__ import annotations

import json
import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taskflow.adapters.persistence.models import InsightORM, MetricValueORM
from taskflow.domain.policies.narrative_guardrail_policy import NarrativeGuardrailPolicy
from taskflow.domain.ports.ports import LLMProvider, UnitOfWork


class GenerateNarrativeInsightUseCase:
    """The LLM narrates deterministic values; it never computes metrics."""

    def __init__(self, session: AsyncSession, uow: UnitOfWork,
                 llm_provider: LLMProvider) -> None:
        self._session = session
        self._uow = uow
        self._llm = llm_provider

    async def execute(
        self,
        scope: str,
        scope_id: uuid.UUID | None = None,
        period_start: date | None = None,
        period_end: date | None = None,
    ) -> dict[str, Any]:
        end = period_end or datetime.now(UTC).date()
        start = period_start or end
        stmt = select(MetricValueORM).where(
            MetricValueORM.period_start >= start,
            MetricValueORM.period_end <= end,
            MetricValueORM.is_suppressed.is_(False),
            MetricValueORM.value.is_not(None),
        ).order_by(MetricValueORM.computed_at.desc())
        if scope_id is not None:
            stmt = stmt.where(MetricValueORM.dimension_value == str(scope_id))
        values = list((await self._session.execute(stmt)).scalars().all())
        evidence = {row.metric_id: float(row.value) for row in values if row.value is not None}
        evidence_numbers = list(evidence.values())
        payload = {
            "scope": scope,
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "metrics": evidence,
            "rule": "Use only exact supplied metric values; do not derive or round numbers.",
        }
        prompt = "Produza uma síntese gerencial curta a partir deste JSON:\n" + json.dumps(
            payload, ensure_ascii=False, sort_keys=True)
        text = await self._generate(prompt)
        validation = NarrativeGuardrailPolicy.validate(text, evidence_numbers)
        retries = 0
        if not validation.is_valid:
            retries = 1
            retry_prompt = (
                prompt + "\nA resposta anterior continha numerais sem suporte. "
                "Reescreva sem acrescentar qualquer numeral.")
            text = await self._generate(retry_prompt)
            validation = NarrativeGuardrailPolicy.validate(text, evidence_numbers)
        suppressed = not validation.is_valid
        published_text = None if suppressed else text
        insight = InsightORM(
            id=uuid.uuid4(), scope=scope, period_start=start, period_end=end,
            filters={"scope_id": str(scope_id)} if scope_id else None,
            input_payload=payload, headline=None, summary=published_text,
            findings=None, suggested_actions=None,
            data_caveats=["Visão do fluxo que passa pelo gestor."],
            numeric_guard_passed=validation.is_valid,
            guard_failures=[{"unsupported_number": number}
                            for number in validation.discrepancies] or None,
            retry_count=retries, is_suppressed=suppressed,
            model=getattr(self._llm, "model_name", self._llm.__class__.__name__),
            created_at=datetime.utcnow(),
        )
        async with self._uow:
            self._session.add(insight)
            await self._uow.commit()
        return {
            "insight_id": str(insight.id),
            "narrative_text": published_text,
            "is_verified": validation.is_valid,
            "is_suppressed": suppressed,
            "retry_count": retries,
            "discrepancies": validation.discrepancies,
            "input_payload": payload,
        }

    async def _generate(self, prompt: str) -> str:
        return await self._llm.draft_follow_up(
            {"title": prompt}, {"purpose": "grounded_narrative"}, "analytical")
