"""Roteador de confiança para aplicação de decisões e propostas de triagem — RF-C.4 e RF-G.8."""

from __future__ import annotations

from dataclasses import dataclass

from taskflow.domain.value_objects.enums import DecisionKind


@dataclass(frozen=True)
class ConfidenceThresholds:
    """Limiares de confiança configuráveis."""

    auto_update_min: float = 0.80
    auto_transition_min: float = 0.85
    auto_done_min: float = 0.90
    new_task_min: float = 0.85
    attach_context_min: float = 0.60
    noise_min: float = 0.70
    discard_max: float = 0.55


class ConfidenceRouter:
    """Roteia decisões com base nos limiares de confiança.

    Determina se uma decisão é aplicada automaticamente, enviada para a
    fila de triagem como proposta humana, ou descartada.
    """

    def __init__(self, thresholds: ConfidenceThresholds | None = None) -> None:
        self._t = thresholds or ConfidenceThresholds()

    def should_auto_apply(self, decision_kind: DecisionKind, confidence: float) -> bool:
        """Retorna True se a decisão atinge o limiar para aplicação automática."""
        if decision_kind == DecisionKind.UPDATE_EXISTING:
            return confidence >= self._t.auto_update_min
        if decision_kind == DecisionKind.TRANSITION_EXISTING:
            return confidence >= self._t.auto_transition_min
        if decision_kind == DecisionKind.NEW_TASK:
            return confidence >= self._t.new_task_min
        if decision_kind == DecisionKind.ATTACH_CONTEXT:
            return confidence >= self._t.attach_context_min
        if decision_kind == DecisionKind.NOISE:
            return confidence >= self._t.noise_min
        return False

    def should_route_to_triage(self, decision_kind: DecisionKind, confidence: float) -> bool:
        """Retorna True se a decisão deve gerar uma proposta de triagem."""
        if decision_kind in (DecisionKind.NOISE, DecisionKind.ATTACH_CONTEXT):
            return False
        return confidence >= self._t.discard_max and not self.should_auto_apply(decision_kind, confidence)

    def should_discard(self, confidence: float) -> bool:
        """Retorna True se a confiança for insuficiente para qualquer ação."""
        return confidence < self._t.discard_max
