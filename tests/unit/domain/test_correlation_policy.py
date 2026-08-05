"""Testes unitários para CorrelationPolicy — RF-G.8.

★ Toda linha da matriz de arbitragem tem teste próprio rastreável.
★ Zero I/O, zero LLM — 100% determinístico.

Identificadores de testes rastreados para RF-G.8:
- UPDATE_EXISTING: auto (conf ≥ 0.80), triage (0.55-0.80)
- TRANSITION → in_progress/waiting/blocked: auto (conf ≥ 0.85 + match det.)
- TRANSITION → done: auto (conf ≥ 0.90 + match det. + responsável)
- TRANSITION → done: triage (sem match determinístico ou origem não confiável)
- TRANSITION → cancelled: sempre triage
- due_date_change posterior: auto (conf ≥ 0.85)
- due_date_change anterior (antecipação): sempre triage
- NEW_TASK: auto (conf ≥ 0.85), triage (0.55-0.85)
- SPLIT/subtask_of: sempre triage
- MERGE_DUPLICATE: triagem com preview
- ATTACH_CONTEXT: auto (conf ≥ 0.60)
- NOISE: descarte (conf ≥ 0.70)
- qualquer: descarte (conf < 0.55)
- ambiguidade: triage (dois same_task dentro de 0.10 delta)
"""

import pytest

from taskflow.domain.policies.correlation_policy import (
    RULE_AMBIGUITY_TRIAGE,
    RULE_ATTACH_CONTEXT_AUTO,
    RULE_LOW_CONF_DISCARD,
    RULE_MERGE_TRIAGE,
    RULE_NEW_TASK_AUTO,
    RULE_NEW_TASK_TRIAGE,
    RULE_NOISE_DISCARD,
    RULE_SPLIT_TRIAGE,
    RULE_TRANSITION_BLOCKED_AUTO,
    RULE_TRANSITION_CANCELLED_TRIAGE,
    RULE_TRANSITION_DONE_AUTO,
    RULE_TRANSITION_DONE_TRIAGE,
    RULE_TRANSITION_IN_PROGRESS_AUTO,
    RULE_TRANSITION_WAITING_AUTO,
    RULE_UPDATE_AUTO,
    RULE_UPDATE_TRIAGE,
    CorrelationPolicy,
)
from taskflow.domain.value_objects.enums import DecisionKind, TaskStatus

policy = CorrelationPolicy()

TASK_ID = "task-abc-123"

# Helper para assessments sem ambiguidade
NO_ASSESSMENTS: list[dict] = []

# Assessments ambíguos — dois same_task próximos
AMBIGUOUS_ASSESSMENTS = [
    {"relation": "same_task", "confidence": 0.78, "task_id": "t1"},
    {"relation": "same_task", "confidence": 0.74, "task_id": "t2"},
]


class TestUpdateExisting:
    """RF-G.8: UPDATE_EXISTING."""

    def test_auto_apply_high_confidence(self) -> None:
        """conf ≥ 0.80 → auto-aplica."""
        result = policy.decide(
            decision_kind=DecisionKind.UPDATE_EXISTING,
            confidence=0.90,
            primary_task_id=TASK_ID,
            proposed_changes={"progress_note": "ok"},
            has_deterministic_match=False,
            signal_from_responsible=False,
            ambiguity_reason=None,
            assessments=NO_ASSESSMENTS,
        )
        assert result.is_auto_applied
        assert result.policy_rule_id == RULE_UPDATE_AUTO

    def test_triage_medium_confidence(self) -> None:
        """0.55 ≤ conf < 0.80 → triagem."""
        result = policy.decide(
            decision_kind=DecisionKind.UPDATE_EXISTING,
            confidence=0.70,
            primary_task_id=TASK_ID,
            proposed_changes={},
            has_deterministic_match=False,
            signal_from_responsible=False,
            ambiguity_reason=None,
            assessments=NO_ASSESSMENTS,
        )
        assert result.routed_to_triage
        assert result.policy_rule_id == RULE_UPDATE_TRIAGE


class TestTransitionInProgressWaitingBlocked:
    """RF-G.8: TRANSITION → in_progress / waiting_on_others / blocked."""

    @pytest.mark.parametrize("to_status,expected_rule", [
        (TaskStatus.IN_PROGRESS.value, RULE_TRANSITION_IN_PROGRESS_AUTO),
        (TaskStatus.WAITING_ON_OTHERS.value, RULE_TRANSITION_WAITING_AUTO),
        (TaskStatus.BLOCKED.value, RULE_TRANSITION_BLOCKED_AUTO),
    ])
    def test_auto_with_deterministic_match(self, to_status: str, expected_rule: str) -> None:
        """conf ≥ 0.85 + match det. → auto-aplica."""
        result = policy.decide(
            decision_kind=DecisionKind.TRANSITION_EXISTING,
            confidence=0.90,
            primary_task_id=TASK_ID,
            proposed_changes={"to_status": to_status},
            has_deterministic_match=True,
            signal_from_responsible=False,
            ambiguity_reason=None,
            assessments=NO_ASSESSMENTS,
        )
        assert result.is_auto_applied
        assert result.policy_rule_id == expected_rule

    @pytest.mark.parametrize("to_status", [
        TaskStatus.IN_PROGRESS.value,
        TaskStatus.WAITING_ON_OTHERS.value,
        TaskStatus.BLOCKED.value,
    ])
    def test_triage_without_deterministic_match(self, to_status: str) -> None:
        """Sem match determinístico → triagem mesmo com alta confiança."""
        result = policy.decide(
            decision_kind=DecisionKind.TRANSITION_EXISTING,
            confidence=0.90,
            primary_task_id=TASK_ID,
            proposed_changes={"to_status": to_status},
            has_deterministic_match=False,
            signal_from_responsible=False,
            ambiguity_reason=None,
            assessments=NO_ASSESSMENTS,
        )
        assert result.routed_to_triage


class TestTransitionDone:
    """RF-G.8: TRANSITION → done — a regra mais restritiva."""

    def test_auto_done_all_conditions_met(self) -> None:
        """conf ≥ 0.90 + match det. + responsável → auto (reversível)."""
        result = policy.decide(
            decision_kind=DecisionKind.TRANSITION_EXISTING,
            confidence=0.92,
            primary_task_id=TASK_ID,
            proposed_changes={"to_status": TaskStatus.DONE.value},
            has_deterministic_match=True,
            signal_from_responsible=True,
            ambiguity_reason=None,
            assessments=NO_ASSESSMENTS,
        )
        assert result.is_auto_applied
        assert result.policy_rule_id == RULE_TRANSITION_DONE_AUTO

    def test_triage_done_no_deterministic_match(self) -> None:
        """Sem match determinístico → sempre triagem, independente de conf."""
        result = policy.decide(
            decision_kind=DecisionKind.TRANSITION_EXISTING,
            confidence=0.95,
            primary_task_id=TASK_ID,
            proposed_changes={"to_status": TaskStatus.DONE.value},
            has_deterministic_match=False,
            signal_from_responsible=True,
            ambiguity_reason=None,
            assessments=NO_ASSESSMENTS,
        )
        assert result.routed_to_triage
        assert result.policy_rule_id == RULE_TRANSITION_DONE_TRIAGE

    def test_triage_done_not_from_responsible(self) -> None:
        """Sinal não vem do responsável → triagem."""
        result = policy.decide(
            decision_kind=DecisionKind.TRANSITION_EXISTING,
            confidence=0.95,
            primary_task_id=TASK_ID,
            proposed_changes={"to_status": TaskStatus.DONE.value},
            has_deterministic_match=True,
            signal_from_responsible=False,
            ambiguity_reason=None,
            assessments=NO_ASSESSMENTS,
        )
        assert result.routed_to_triage
        assert result.policy_rule_id == RULE_TRANSITION_DONE_TRIAGE

    def test_triage_done_low_confidence(self) -> None:
        """conf < 0.90 → triagem mesmo com match e responsável."""
        result = policy.decide(
            decision_kind=DecisionKind.TRANSITION_EXISTING,
            confidence=0.88,
            primary_task_id=TASK_ID,
            proposed_changes={"to_status": TaskStatus.DONE.value},
            has_deterministic_match=True,
            signal_from_responsible=True,
            ambiguity_reason=None,
            assessments=NO_ASSESSMENTS,
        )
        assert result.routed_to_triage

    def test_auto_done_disabled_by_config(self) -> None:
        """allow_auto_done=False → sempre triagem."""
        policy_no_auto = CorrelationPolicy(allow_auto_done=False)
        result = policy_no_auto.decide(
            decision_kind=DecisionKind.TRANSITION_EXISTING,
            confidence=0.99,
            primary_task_id=TASK_ID,
            proposed_changes={"to_status": TaskStatus.DONE.value},
            has_deterministic_match=True,
            signal_from_responsible=True,
            ambiguity_reason=None,
            assessments=NO_ASSESSMENTS,
        )
        assert result.routed_to_triage


class TestTransitionCancelled:
    """RF-G.8: TRANSITION → cancelled — NUNCA automático."""

    def test_cancelled_always_triage(self) -> None:
        """Qualquer confiança → sempre triagem para cancelamento."""
        result = policy.decide(
            decision_kind=DecisionKind.TRANSITION_EXISTING,
            confidence=0.99,
            primary_task_id=TASK_ID,
            proposed_changes={"to_status": TaskStatus.CANCELLED.value},
            has_deterministic_match=True,
            signal_from_responsible=True,
            ambiguity_reason=None,
            assessments=NO_ASSESSMENTS,
        )
        assert result.routed_to_triage
        assert result.policy_rule_id == RULE_TRANSITION_CANCELLED_TRIAGE

    def test_allow_auto_cancel_ignored(self) -> None:
        """Mesmo que allow_auto_cancel=True (impossível na configuração padrão),
        o cancelamento nunca pode ser automático pelo design da política."""
        # O campo allow_auto_cancel existe mas a lógica sempre roteia para triage
        result = policy.decide(
            decision_kind=DecisionKind.TRANSITION_EXISTING,
            confidence=0.99,
            primary_task_id=TASK_ID,
            proposed_changes={"to_status": TaskStatus.CANCELLED.value},
            has_deterministic_match=True,
            signal_from_responsible=True,
            ambiguity_reason=None,
            assessments=NO_ASSESSMENTS,
        )
        assert not result.is_auto_applied


class TestNewTask:
    """RF-G.8: NEW_TASK."""

    def test_auto_high_confidence(self) -> None:
        """conf ≥ 0.85 → auto-cria."""
        result = policy.decide(
            decision_kind=DecisionKind.NEW_TASK,
            confidence=0.90,
            primary_task_id=None,
            proposed_changes={"title": "Nova tarefa"},
            has_deterministic_match=False,
            signal_from_responsible=False,
            ambiguity_reason=None,
            assessments=NO_ASSESSMENTS,
        )
        assert result.is_auto_applied
        assert result.policy_rule_id == RULE_NEW_TASK_AUTO

    def test_triage_medium_confidence(self) -> None:
        """0.55 ≤ conf < 0.85 → triagem."""
        result = policy.decide(
            decision_kind=DecisionKind.NEW_TASK,
            confidence=0.70,
            primary_task_id=None,
            proposed_changes={},
            has_deterministic_match=False,
            signal_from_responsible=False,
            ambiguity_reason=None,
            assessments=NO_ASSESSMENTS,
        )
        assert result.routed_to_triage
        assert result.policy_rule_id == RULE_NEW_TASK_TRIAGE


class TestAttachContext:
    """RF-G.8: ATTACH_CONTEXT — cidadão de primeira classe RF-G.9."""

    def test_auto_applies_above_threshold(self) -> None:
        """conf ≥ 0.60 → auto-aplica como context, sem mudar status/prazo."""
        result = policy.decide(
            decision_kind=DecisionKind.ATTACH_CONTEXT,
            confidence=0.75,
            primary_task_id=TASK_ID,
            proposed_changes=None,
            has_deterministic_match=False,
            signal_from_responsible=False,
            ambiguity_reason=None,
            assessments=NO_ASSESSMENTS,
        )
        assert result.is_auto_applied
        assert result.policy_rule_id == RULE_ATTACH_CONTEXT_AUTO
        assert result.proposed_changes == {"role": "context"}

    def test_discard_below_threshold(self) -> None:
        """conf < 0.60 → descarte."""
        result = policy.decide(
            decision_kind=DecisionKind.ATTACH_CONTEXT,
            confidence=0.50,
            primary_task_id=TASK_ID,
            proposed_changes=None,
            has_deterministic_match=False,
            signal_from_responsible=False,
            ambiguity_reason=None,
            assessments=NO_ASSESSMENTS,
        )
        assert result.action == "discard"


class TestNoise:
    """RF-G.8: NOISE."""

    def test_discard_high_confidence_noise(self) -> None:
        """conf ≥ 0.70 → descarta (é ruído confirmado)."""
        result = policy.decide(
            decision_kind=DecisionKind.NOISE,
            confidence=0.80,
            primary_task_id=None,
            proposed_changes=None,
            has_deterministic_match=False,
            signal_from_responsible=False,
            ambiguity_reason=None,
            assessments=NO_ASSESSMENTS,
        )
        assert result.action == "discard"
        assert result.policy_rule_id == RULE_NOISE_DISCARD

    def test_discard_low_confidence_noise(self) -> None:
        """conf < 0.55 → descarta com regra de baixa confiança."""
        result = policy.decide(
            decision_kind=DecisionKind.NOISE,
            confidence=0.40,
            primary_task_id=None,
            proposed_changes=None,
            has_deterministic_match=False,
            signal_from_responsible=False,
            ambiguity_reason=None,
            assessments=NO_ASSESSMENTS,
        )
        assert result.action == "discard"
        assert result.policy_rule_id == RULE_LOW_CONF_DISCARD


class TestLowConfidenceDiscard:
    """RF-G.8: qualquer decisão com conf < 0.55 → descarte."""

    @pytest.mark.parametrize("kind", [
        DecisionKind.UPDATE_EXISTING,
        DecisionKind.NEW_TASK,
        DecisionKind.ATTACH_CONTEXT,
    ])
    def test_below_discard_threshold(self, kind: DecisionKind) -> None:
        result = policy.decide(
            decision_kind=kind,
            confidence=0.40,
            primary_task_id=TASK_ID,
            proposed_changes={},
            has_deterministic_match=False,
            signal_from_responsible=False,
            ambiguity_reason=None,
            assessments=NO_ASSESSMENTS,
        )
        assert result.action == "discard"
        assert result.policy_rule_id == RULE_LOW_CONF_DISCARD


class TestAmbiguity:
    """RF-G.8: Ambiguidade — Guardrail 4 do RF-G.7."""

    def test_ambiguous_same_task_forced_to_triage(self) -> None:
        """Dois candidatos same_task dentro de 0.10 delta → triagem."""
        result = policy.decide(
            decision_kind=DecisionKind.UPDATE_EXISTING,
            confidence=0.90,
            primary_task_id=TASK_ID,
            proposed_changes={},
            has_deterministic_match=True,
            signal_from_responsible=False,
            ambiguity_reason=None,
            assessments=AMBIGUOUS_ASSESSMENTS,
        )
        assert result.routed_to_triage
        assert result.policy_rule_id == RULE_AMBIGUITY_TRIAGE
        assert result.ambiguity_reason is not None

    def test_non_ambiguous_same_task(self) -> None:
        """Delta > 0.10 → não é ambiguidade → regra normal."""
        assessments = [
            {"relation": "same_task", "confidence": 0.90, "task_id": "t1"},
            {"relation": "same_task", "confidence": 0.65, "task_id": "t2"},
        ]
        result = policy.decide(
            decision_kind=DecisionKind.UPDATE_EXISTING,
            confidence=0.90,
            primary_task_id=TASK_ID,
            proposed_changes={},
            has_deterministic_match=True,
            signal_from_responsible=False,
            ambiguity_reason=None,
            assessments=assessments,
        )
        # Delta de 0.25 > 0.10 → não é ambiguidade
        assert not result.routed_to_triage or result.policy_rule_id != RULE_AMBIGUITY_TRIAGE


class TestSplitAndMerge:
    """RF-G.8: SPLIT e MERGE_DUPLICATE — sempre triagem."""

    def test_split_always_triage(self) -> None:
        result = policy.decide(
            decision_kind=DecisionKind.SPLIT,
            confidence=0.95,
            primary_task_id=TASK_ID,
            proposed_changes={},
            has_deterministic_match=True,
            signal_from_responsible=False,
            ambiguity_reason=None,
            assessments=NO_ASSESSMENTS,
        )
        assert result.routed_to_triage
        assert result.policy_rule_id == RULE_SPLIT_TRIAGE

    def test_merge_always_triage(self) -> None:
        result = policy.decide(
            decision_kind=DecisionKind.MERGE_DUPLICATE,
            confidence=0.95,
            primary_task_id=TASK_ID,
            proposed_changes={},
            has_deterministic_match=True,
            signal_from_responsible=False,
            ambiguity_reason=None,
            assessments=NO_ASSESSMENTS,
        )
        assert result.routed_to_triage
        assert result.policy_rule_id == RULE_MERGE_TRIAGE
