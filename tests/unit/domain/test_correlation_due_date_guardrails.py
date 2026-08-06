from taskflow.domain.policies.correlation_policy import (
    RULE_DUE_DATE_ADVANCE_TRIAGE,
    RULE_DUE_DATE_POSTPONE_AUTO,
    CorrelationPolicy,
)
from taskflow.domain.value_objects.enums import DecisionKind


def decide(due_date: str, current_due_date: str):
    return CorrelationPolicy().decide(
        decision_kind=DecisionKind.UPDATE_EXISTING,
        confidence=0.90,
        primary_task_id="5e3eeb4f-26b6-4b80-8084-7bd3e5c85ac0",
        proposed_changes={
            "due_date": due_date,
            "current_due_date": current_due_date,
        },
        has_deterministic_match=True,
        signal_from_responsible=False,
        ambiguity_reason=None,
        assessments=[],
    )


def test_due_date_postponement_can_auto_apply() -> None:
    result = decide("2026-08-12", "2026-08-10")
    assert result.is_auto_applied
    assert result.policy_rule_id == RULE_DUE_DATE_POSTPONE_AUTO


def test_due_date_advance_always_routes_to_triage() -> None:
    result = decide("2026-08-08", "2026-08-10")
    assert result.routed_to_triage
    assert result.policy_rule_id == RULE_DUE_DATE_ADVANCE_TRIAGE


def test_update_without_candidate_identity_routes_to_triage() -> None:
    result = CorrelationPolicy().decide(
        decision_kind=DecisionKind.UPDATE_EXISTING,
        confidence=0.99,
        primary_task_id=None,
        proposed_changes={"progress_note": "done"},
        has_deterministic_match=False,
        signal_from_responsible=False,
        ambiguity_reason=None,
        assessments=[],
    )
    assert result.routed_to_triage
    assert result.ambiguity_reason == "candidate_identity_missing"
