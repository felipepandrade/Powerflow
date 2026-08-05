"""Política de Supressão e K-Anonimato — RF-I.6 e Seção 8 do PRD."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SuppressedValue:
    """Invólucro para valores de métrica com suporte a K-anonimato."""

    value: float | None
    is_suppressed: bool
    sample_size: int
    suppression_reason: str | None = None


class SuppressionPolicy:
    """Aplica k-anonimato mínimo K=3 para métricas desagregadas por área/grupo."""

    DEFAULT_K_MIN: int = 3

    @classmethod
    def apply(
        cls,
        raw_value: float | None,
        sample_size: int,
        is_group_metric: bool = False,
        k_min: int = DEFAULT_K_MIN,
    ) -> SuppressedValue:
        if is_group_metric and sample_size < k_min:
            return SuppressedValue(
                value=None,
                is_suppressed=True,
                sample_size=sample_size,
                suppression_reason=f"Amostra insuficiente ({sample_size} < k_min={k_min}). Supressão aplicada para privacidade.",
            )

        return SuppressedValue(
            value=raw_value,
            is_suppressed=False,
            sample_size=sample_size,
            suppression_reason=None,
        )
