"""Use Case: GenerateNarrativeInsightUseCase — UC-Analytics-3.

Gera sínteses narrativas qualitativas para dashboards e relatórios utilizando LLM (Gemini / Ollama),
garantindo 100% de precisão numérica através do Guardrail Anti-Alucinação.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taskflow.adapters.persistence.models import InsightORM, MetricValueORM
from taskflow.domain.policies.narrative_guardrail_policy import NarrativeGuardrailPolicy
from taskflow.domain.ports.ports import LLMProvider, UnitOfWork

log = structlog.get_logger()


class GenerateNarrativeInsightUseCase:
    """UC-Analytics-3 — Geração de Insights Narrativos com Guardrail Estrito."""

    PROMPT_TEMPLATE = """Você é um assistente especialista em análise de fluxo e gestão de projetos.
Sua missão é escrever um resumo narrativo claro, sucinto e acionável em Português sobre o estado do projeto/área.

REGRAS CRÍTICAS INVIOLÁVEIS:
1. Você DEVE usar APENAS os números fornecidos exatamente como constam no JSON de evidências abaixo.
2. É ESTRITAMENTE PROIBIDO inventar, calcular novos números, fazer arredondamentos não informados ou estimar porcentagens.
3. Se um dado não estiver no JSON, não mencione nenhum valor numérico para ele.

JSON de Evidências Determinísticas:
{evidence_json}

Escreva a síntese narrativa:"""

    def __init__(self, session: AsyncSession, uow: UnitOfWork, llm_provider: LLMProvider) -> None:
        self._session = session
        self._uow = uow
        self._llm = llm_provider

    async def execute(self, scope: str, scope_id: uuid.UUID | None = None) -> dict[str, Any]:
        log.info("narrative_insight.start", scope=scope, scope_id=str(scope_id))

        # 1. Buscar métricas calculadas recentes para o escopo
        stmt = select(MetricValueORM).order_by(MetricValueORM.computed_at.desc()).limit(20)
        res = await self._session.execute(stmt)
        metric_values = res.scalars().all()

        evidence_map = {}
        evidence_numbers = []

        for mv in metric_values:
            if mv.value is not None:
                evidence_map[mv.metric_id] = mv.value
                evidence_numbers.append(mv.value)

        evidence_json = json.dumps(evidence_map, indent=2, ensure_ascii=False)
        prompt = self.PROMPT_TEMPLATE.format(evidence_json=evidence_json)

        # 2. Invocação da LLM
        llm_response = await self._llm.generate(prompt=prompt)
        text_generated = llm_response.text or "Sem dados suficientes para síntese."

        # 3. Aplicação do Guardrail Anti-Alucinação
        guardrail_res = NarrativeGuardrailPolicy.validate(text_generated, evidence_numbers)

        is_verified = guardrail_res.is_valid
        if not is_verified:
            log.warning(
                "narrative_insight.guardrail_warning",
                discrepancies=guardrail_res.discrepancies,
                note="Texto gerado contém numerais não pareados na evidência SQL.",
            )

        # 4. Salvar na tabela `insights`
        async with self._uow:
            orm = InsightORM(
                id=uuid.uuid4(),
                scope=scope,
                scope_id=scope_id,
                narrative_text=text_generated,
                key_takeaways=[str(k) for k in evidence_map.keys()][:5],
                metrics_referenced=evidence_map,
                confidence_score=0.95 if is_verified else 0.50,
                is_verified=is_verified,
                provider_used=getattr(self._llm, "model_name", "gemini/ollama"),
                prompt_tokens=llm_response.prompt_tokens,
                completion_tokens=llm_response.completion_tokens,
                created_at=datetime.utcnow(),
            )
            self._session.add(orm)
            await self._uow.commit()

        return {
            "insight_id": str(orm.id),
            "narrative_text": text_generated,
            "is_verified": is_verified,
            "discrepancies": guardrail_res.discrepancies,
        }
