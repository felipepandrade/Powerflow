"""Validador sintático e guardrail anti-alucinação numérica para sínteses da LLM — RF-I.8 e RF-J.3."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


class NumericalHallucinationError(ValueError):
    """Exceção lançada quando a LLM gera um número que não consta na evidência determinística."""


@dataclass(frozen=True)
class GuardrailResult:
    """Resultado da validação do guardrail anti-alucinação."""

    is_valid: bool
    extracted_numbers: list[float]
    discrepancies: list[float] = field(default_factory=list)


class NarrativeGuardrailPolicy:
    """Garante 0 números órfãos ou inventados em relatórios e insights narrativos."""

    # Regex para capturar inteiros e decimais (ex: 45, 12.5, 85%)
    NUMBER_PATTERN = re.compile(r"(?<![\w])[-+]?\d+(?:[.,]\d+)?")

    @classmethod
    def validate(cls, narrative_text: str, evidence_values: list[float | int]) -> GuardrailResult:
        """Verifica se todo número mencionado na narrativa possui correspondente exato na evidência."""
        # 1. Normalizar evidências como float
        evidence_set = {float(v) for v in evidence_values if v is not None}

        # 2. Extrair números do texto
        raw_matches = cls.NUMBER_PATTERN.findall(narrative_text)
        extracted: list[float] = []

        for m in raw_matches:
            try:
                # Tratar vírgula decimal pt-BR
                clean_num = float(m.replace(",", "."))
                extracted.append(clean_num)
            except ValueError:
                continue

        # 3. Verificar discrepâncias (ignorando inteiros pequenos comuns de formatação como datas/listas 1, 2, 3)
        discrepancies = []
        for num in extracted:
            # Ignorar números de item (1, 2, 3) se pequenos e inteiros
            if num not in evidence_set:
                discrepancies.append(num)

        if discrepancies:
            return GuardrailResult(
                is_valid=False,
                extracted_numbers=extracted,
                discrepancies=discrepancies,
            )

        return GuardrailResult(
            is_valid=True,
            extracted_numbers=extracted,
            discrepancies=[],
        )
