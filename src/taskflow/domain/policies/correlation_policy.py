"""CorrelationPolicy — Matriz de arbitragem determinística — RF-G.8.

★ Componente mais crítico do sistema.
★ 100% determinístico — o LLM produz hipótese; a política decide.
★ Zero dependência de I/O, rede ou LLM.
★ Cada linha da tabela RF-G.8 tem um identificador de regra (policy_rule_id).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from taskflow.domain.value_objects.enums import (
    DecisionKind,
    RelationType,
    TaskStatus,
)

# Constantes de regras — rastreabilidade total no correlation_runs
RULE_UPDATE_AUTO = "RF-G.8/UPDATE_EXISTING/auto"
RULE_UPDATE_TRIAGE = "RF-G.8/UPDATE_EXISTING/triage"
RULE_TRANSITION_IN_PROGRESS_AUTO = "RF-G.8/TRANSITION/in_progress/auto"
RULE_TRANSITION_WAITING_AUTO = "RF-G.8/TRANSITION/waiting_on_others/auto"
RULE_TRANSITION_BLOCKED_AUTO = "RF-G.8/TRANSITION/blocked/auto"
RULE_TRANSITION_DONE_AUTO = "RF-G.8/TRANSITION/done/auto"
RULE_TRANSITION_DONE_TRIAGE = "RF-G.8/TRANSITION/done/triage"
RULE_TRANSITION_CANCELLED_TRIAGE = "RF-G.8/TRANSITION/cancelled/triage"
RULE_DUE_DATE_POSTPONE_AUTO = "RF-G.8/due_date_change/postpone/auto"
RULE_DUE_DATE_ADVANCE_TRIAGE = "RF-G.8/due_date_change/advance/triage"
RULE_NEW_TASK_AUTO = "RF-G.8/NEW_TASK/auto"
RULE_NEW_TASK_TRIAGE = "RF-G.8/NEW_TASK/triage"
RULE_SPLIT_TRIAGE = "RF-G.8/SPLIT/triage"
RULE_MERGE_TRIAGE = "RF-G.8/MERGE_DUPLICATE/triage"
RULE_ATTACH_CONTEXT_AUTO = "RF-G.8/ATTACH_CONTEXT/auto"
RULE_NOISE_DISCARD = "RF-G.8/NOISE/discard"
RULE_LOW_CONF_DISCARD = "RF-G.8/any/low_confidence_discard"
RULE_AMBIGUITY_TRIAGE = "RF-G.8/any/ambiguity_triage"

# Transições automáticas permitidas (sem necessidade de match determinístico)
AUTO_TRANSITIONS: frozenset[str] = frozenset({
    TaskStatus.IN_PROGRESS.value,
    TaskStatus.WAITING_ON_OTHERS.value,
    TaskStatus.BLOCKED.value,
})


@dataclass
class CorrelationDecision:
    """Decisão de correlação produzida pela política."""

    action: str             # "apply" | "triage" | "discard"
    decision_kind: DecisionKind
    policy_rule_id: str
    primary_task_id: str | None = None
    proposed_changes: dict[str, Any] | None = None
    confidence: float = 0.0
    ambiguity_reason: str | None = None

    @property
    def is_auto_applied(self) -> bool:
        """True se a decisão é aplicada automaticamente."""
        return self.action == "apply"

    @property
    def routed_to_triage(self) -> bool:
        """True se a decisão é enviada para triagem."""
        return self.action == "triage"


class CorrelationPolicy:
    """Matriz de arbitragem de correlação — RF-G.8.

    Recebe a saída do estágio G2 (assessments do LLM) e aplica as regras
    determinísticas para produzir a decisão final.

    Princípios invioláveis:
    1. Tudo que aumenta trabalho (new task, update, context) pode ser automático.
    2. Tudo que fecha o loop (done, cancelled, prazo antecipado) exige confirmação.
    3. Toda ação automática é reversível e registrada.
    """

    def __init__(
        self,
        auto_update_min: float = 0.80,
        auto_transition_min: float = 0.85,
        auto_done_min: float = 0.90,
        new_task_auto_min: float = 0.85,
        attach_context_min: float = 0.60,
        noise_min: float = 0.70,
        discard_max: float = 0.55,
        ambiguity_delta: float = 0.10,
        allow_auto_done: bool = True,
        allow_auto_cancel: bool = False,  # NUNCA automático — princípio inviolável
    ) -> None:
        self.auto_update_min = auto_update_min
        self.auto_transition_min = auto_transition_min
        self.auto_done_min = auto_done_min
        self.new_task_auto_min = new_task_auto_min
        self.attach_context_min = attach_context_min
        self.noise_min = noise_min
        self.discard_max = discard_max
        self.ambiguity_delta = ambiguity_delta
        self.allow_auto_done = allow_auto_done
        self.allow_auto_cancel = allow_auto_cancel  # Sempre False — não alterar

    def decide(
        self,
        decision_kind: DecisionKind,
        confidence: float,
        primary_task_id: str | None,
        proposed_changes: dict[str, Any] | None,
        has_deterministic_match: bool,
        signal_from_responsible: bool,
        ambiguity_reason: str | None,
        assessments: list[dict[str, Any]],
    ) -> CorrelationDecision:
        """Aplica a matriz de arbitragem e retorna a decisão final.

        Args:
            decision_kind: Tipo de decisão sugerida pelo LLM.
            confidence: Confiança da decisão (0.0 - 1.0).
            primary_task_id: ID da tarefa primária identificada.
            proposed_changes: Mudanças propostas (status, prazo, etc.).
            has_deterministic_match: Se R1 ou R2 confirmaram a tarefa.
            signal_from_responsible: Se o sinal vem do responsável pela entrega.
            ambiguity_reason: Razão de ambiguidade (se houver).
            assessments: Lista de assessments do LLM para detecção de ambiguidade.
        """
        # Verifica ambiguidade antes de qualquer decisão — Guardrail 4
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")

        ambiguity = self._check_ambiguity(assessments)
        if ambiguity:
            return CorrelationDecision(
                action="triage",
                decision_kind=decision_kind,
                policy_rule_id=RULE_AMBIGUITY_TRIAGE,
                primary_task_id=primary_task_id,
                confidence=confidence,
                ambiguity_reason=ambiguity,
            )

        # Descarte por baixa confiança geral
        if confidence < self.discard_max:
            return CorrelationDecision(
                action="discard",
                decision_kind=decision_kind,
                policy_rule_id=RULE_LOW_CONF_DISCARD,
                confidence=confidence,
            )

        if decision_kind == DecisionKind.UPDATE_EXISTING:
            return self._decide_update(confidence, primary_task_id, proposed_changes)

        if decision_kind == DecisionKind.TRANSITION_EXISTING:
            return self._decide_transition(
                confidence,
                primary_task_id,
                proposed_changes,
                has_deterministic_match,
                signal_from_responsible,
            )

        if decision_kind == DecisionKind.NEW_TASK:
            return self._decide_new_task(confidence, proposed_changes)

        if decision_kind in (DecisionKind.SPLIT,):
            return self._decide_split(confidence, primary_task_id, proposed_changes)

        if decision_kind == DecisionKind.MERGE_DUPLICATE:
            return self._decide_merge(confidence, primary_task_id, proposed_changes)

        if decision_kind == DecisionKind.ATTACH_CONTEXT:
            return self._decide_attach_context(confidence, primary_task_id)

        if decision_kind == DecisionKind.NOISE:
            return self._decide_noise(confidence)

        # Fallback — discard
        return CorrelationDecision(
            action="discard",
            decision_kind=decision_kind,
            policy_rule_id=RULE_LOW_CONF_DISCARD,
            confidence=confidence,
        )

    def _check_ambiguity(self, assessments: list[dict[str, Any]]) -> str | None:
        """Detecta ambiguidade — Guardrail 4 do RF-G.7.

        Se dois candidatos têm relation='same_task' com confianças dentro
        de ambiguity_delta, força triagem.
        """
        same_task = [
            a for a in assessments
            if a.get("relation") == RelationType.SAME_TASK.value
        ]
        if len(same_task) >= 2:
            sorted_by_conf = sorted(
                same_task, key=lambda a: a.get("confidence", 0.0), reverse=True
            )
            top_conf = sorted_by_conf[0].get("confidence", 0.0)
            second_conf = sorted_by_conf[1].get("confidence", 0.0)
            if (top_conf - second_conf) <= self.ambiguity_delta:
                return (
                    f"Dois candidatos com same_task e confianças similares: "
                    f"{top_conf:.2f} e {second_conf:.2f}"
                )
        return None

    def _decide_update(
        self,
        confidence: float,
        task_id: str | None,
        changes: dict[str, Any] | None,
    ) -> CorrelationDecision:
        """RF-G.8: UPDATE_EXISTING."""
        if task_id is None:
            return CorrelationDecision(
                action="triage",
                decision_kind=DecisionKind.UPDATE_EXISTING,
                policy_rule_id=RULE_UPDATE_TRIAGE,
                proposed_changes=changes,
                confidence=confidence,
                ambiguity_reason="candidate_identity_missing",
            )

        if changes and changes.get("due_date") and changes.get("current_due_date"):
            proposed_due: date | None
            current_due: date | None
            try:
                proposed_due = date.fromisoformat(str(changes["due_date"]))
                current_due = date.fromisoformat(str(changes["current_due_date"]))
            except ValueError:
                proposed_due = current_due = None
            if proposed_due is None or current_due is None or proposed_due < current_due:
                return CorrelationDecision(
                    action="triage",
                    decision_kind=DecisionKind.UPDATE_EXISTING,
                    policy_rule_id=RULE_DUE_DATE_ADVANCE_TRIAGE,
                    primary_task_id=task_id,
                    proposed_changes=changes,
                    confidence=confidence,
                )
            if confidence >= self.auto_transition_min:
                return CorrelationDecision(
                    action="apply", decision_kind=DecisionKind.UPDATE_EXISTING,
                    policy_rule_id=RULE_DUE_DATE_POSTPONE_AUTO, primary_task_id=task_id,
                    proposed_changes=changes, confidence=confidence,
                )
        if confidence >= self.auto_update_min:
            return CorrelationDecision(
                action="apply",
                decision_kind=DecisionKind.UPDATE_EXISTING,
                policy_rule_id=RULE_UPDATE_AUTO,
                primary_task_id=task_id,
                proposed_changes=changes,
                confidence=confidence,
            )
        return CorrelationDecision(
            action="triage",
            decision_kind=DecisionKind.UPDATE_EXISTING,
            policy_rule_id=RULE_UPDATE_TRIAGE,
            primary_task_id=task_id,
            proposed_changes=changes,
            confidence=confidence,
        )

    def _decide_transition(
        self,
        confidence: float,
        task_id: str | None,
        changes: dict[str, Any] | None,
        has_deterministic_match: bool,
        signal_from_responsible: bool,
    ) -> CorrelationDecision:
        """RF-G.8: TRANSITION_EXISTING — várias regras por status alvo."""
        to_status = (changes or {}).get("to_status", "")

        # CANCELAMENTO — NUNCA automático (princípio inviolável)
        if to_status == TaskStatus.CANCELLED.value:
            return CorrelationDecision(
                action="triage",
                decision_kind=DecisionKind.TRANSITION_EXISTING,
                policy_rule_id=RULE_TRANSITION_CANCELLED_TRIAGE,
                primary_task_id=task_id,
                proposed_changes=changes,
                confidence=confidence,
            )

        # CONCLUSÃO — regras especiais
        if to_status == TaskStatus.DONE.value:
            return self._decide_done_transition(
                confidence, task_id, changes, has_deterministic_match, signal_from_responsible
            )

        # in_progress / waiting_on_others / blocked — auto com match determinístico
        if to_status in AUTO_TRANSITIONS:
            if confidence >= self.auto_transition_min and has_deterministic_match:
                rule = {
                    TaskStatus.IN_PROGRESS.value: RULE_TRANSITION_IN_PROGRESS_AUTO,
                    TaskStatus.WAITING_ON_OTHERS.value: RULE_TRANSITION_WAITING_AUTO,
                    TaskStatus.BLOCKED.value: RULE_TRANSITION_BLOCKED_AUTO,
                }.get(to_status, RULE_UPDATE_TRIAGE)
                return CorrelationDecision(
                    action="apply",
                    decision_kind=DecisionKind.TRANSITION_EXISTING,
                    policy_rule_id=rule,
                    primary_task_id=task_id,
                    proposed_changes=changes,
                    confidence=confidence,
                )

        return CorrelationDecision(
            action="triage",
            decision_kind=DecisionKind.TRANSITION_EXISTING,
            policy_rule_id=RULE_UPDATE_TRIAGE,
            primary_task_id=task_id,
            proposed_changes=changes,
            confidence=confidence,
        )

    def _decide_done_transition(
        self,
        confidence: float,
        task_id: str | None,
        changes: dict[str, Any] | None,
        has_deterministic_match: bool,
        signal_from_responsible: bool,
    ) -> CorrelationDecision:
        """RF-G.8: TRANSITION → done — regra mais restritiva do sistema."""
        if (
            self.allow_auto_done
            and confidence >= self.auto_done_min
            and has_deterministic_match
            and signal_from_responsible
        ):
            return CorrelationDecision(
                action="apply",
                decision_kind=DecisionKind.TRANSITION_EXISTING,
                policy_rule_id=RULE_TRANSITION_DONE_AUTO,
                primary_task_id=task_id,
                proposed_changes=changes,
                confidence=confidence,
            )
        return CorrelationDecision(
            action="triage",
            decision_kind=DecisionKind.TRANSITION_EXISTING,
            policy_rule_id=RULE_TRANSITION_DONE_TRIAGE,
            primary_task_id=task_id,
            proposed_changes=changes,
            confidence=confidence,
        )

    def _decide_new_task(
        self,
        confidence: float,
        changes: dict[str, Any] | None,
    ) -> CorrelationDecision:
        """RF-G.8: NEW_TASK."""
        if confidence >= self.new_task_auto_min:
            return CorrelationDecision(
                action="apply",
                decision_kind=DecisionKind.NEW_TASK,
                policy_rule_id=RULE_NEW_TASK_AUTO,
                proposed_changes=changes,
                confidence=confidence,
            )
        return CorrelationDecision(
            action="triage",
            decision_kind=DecisionKind.NEW_TASK,
            policy_rule_id=RULE_NEW_TASK_TRIAGE,
            proposed_changes=changes,
            confidence=confidence,
        )

    def _decide_split(
        self,
        confidence: float,
        task_id: str | None,
        changes: dict[str, Any] | None,
    ) -> CorrelationDecision:
        """RF-G.8: SPLIT/subtask_of — sempre triagem (mudança estrutural)."""
        return CorrelationDecision(
            action="triage",
            decision_kind=DecisionKind.SPLIT,
            policy_rule_id=RULE_SPLIT_TRIAGE,
            primary_task_id=task_id,
            proposed_changes=changes,
            confidence=confidence,
        )

    def _decide_merge(
        self,
        confidence: float,
        task_id: str | None,
        changes: dict[str, Any] | None,
    ) -> CorrelationDecision:
        """RF-G.8: MERGE_DUPLICATE — triagem com preview."""
        return CorrelationDecision(
            action="triage",
            decision_kind=DecisionKind.MERGE_DUPLICATE,
            policy_rule_id=RULE_MERGE_TRIAGE,
            primary_task_id=task_id,
            proposed_changes=changes,
            confidence=confidence,
        )

    def _decide_attach_context(
        self,
        confidence: float,
        task_id: str | None,
    ) -> CorrelationDecision:
        """RF-G.8: ATTACH_CONTEXT — cidadão de primeira classe.

        Auto-aplica: evidência role='context', sem alterar status nem prazo.
        """
        if confidence >= self.attach_context_min:
            return CorrelationDecision(
                action="apply",
                decision_kind=DecisionKind.ATTACH_CONTEXT,
                policy_rule_id=RULE_ATTACH_CONTEXT_AUTO,
                primary_task_id=task_id,
                proposed_changes={"role": "context"},
                confidence=confidence,
            )
        return CorrelationDecision(
            action="discard",
            decision_kind=DecisionKind.ATTACH_CONTEXT,
            policy_rule_id=RULE_LOW_CONF_DISCARD,
            confidence=confidence,
        )

    def _decide_noise(self, confidence: float) -> CorrelationDecision:
        """RF-G.8: NOISE — descarte com log."""
        if confidence >= self.noise_min:
            return CorrelationDecision(
                action="discard",
                decision_kind=DecisionKind.NOISE,
                policy_rule_id=RULE_NOISE_DISCARD,
                confidence=confidence,
            )
        return CorrelationDecision(
            action="discard",
            decision_kind=DecisionKind.NOISE,
            policy_rule_id=RULE_LOW_CONF_DISCARD,
            confidence=confidence,
        )
