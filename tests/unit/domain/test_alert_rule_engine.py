"""Unit tests for AlertRuleEngine — RF-G.9 e Seção 12 do PRD.

Cobre as 4 regras determinísticas e o filtro anti-fadiga (MAX_ACTIVE_ALERTS=7).
"""

from __future__ import annotations

import uuid

from taskflow.domain.policies.alert_rule_engine import Alert, AlertRuleEngine


# ── Fixtures helpers ──────────────────────────────────────────────────────────

def _metric(metric_id: str, value: float, **kwargs: object) -> dict:
    return {"metric_id": metric_id, "value": value, **kwargs}


# ── Regra 1 — WIP overflow ────────────────────────────────────────────────────

class TestWipOverflowRule:
    def test_wip_above_threshold_generates_alert(self) -> None:
        alerts = AlertRuleEngine.evaluate_metrics([_metric("flow.wip", 6.0)])
        assert len(alerts) == 1
        assert alerts[0].rule_id == "rule_wip_overflow"
        assert alerts[0].severity == "warning"
        assert alerts[0].current_value == 6.0
        assert alerts[0].threshold_value == 5.0

    def test_wip_at_threshold_no_alert(self) -> None:
        alerts = AlertRuleEngine.evaluate_metrics([_metric("flow.wip", 5.0)])
        assert alerts == []

    def test_wip_below_threshold_no_alert(self) -> None:
        alerts = AlertRuleEngine.evaluate_metrics([_metric("flow.wip", 3.0)])
        assert alerts == []

    def test_wip_alert_message_contains_value(self) -> None:
        alerts = AlertRuleEngine.evaluate_metrics([_metric("flow.wip", 9.0)])
        assert "9" in alerts[0].message


# ── Regra 2 — Lead time p85 ───────────────────────────────────────────────────

class TestLeadTimeRule:
    def test_lead_time_above_threshold_critical(self) -> None:
        alerts = AlertRuleEngine.evaluate_metrics([_metric("flow.lead_time_p85", 8.5)])
        assert len(alerts) == 1
        assert alerts[0].rule_id == "rule_lead_time_high"
        assert alerts[0].severity == "critical"
        assert alerts[0].threshold_value == 7.0

    def test_lead_time_at_threshold_no_alert(self) -> None:
        alerts = AlertRuleEngine.evaluate_metrics([_metric("flow.lead_time_p85", 7.0)])
        assert alerts == []

    def test_lead_time_below_threshold_no_alert(self) -> None:
        alerts = AlertRuleEngine.evaluate_metrics([_metric("flow.lead_time_p85", 4.0)])
        assert alerts == []


# ── Regra 3 — Meeting overload ────────────────────────────────────────────────

class TestMeetingOverloadRule:
    def test_meeting_ratio_above_threshold_warning(self) -> None:
        alerts = AlertRuleEngine.evaluate_metrics([_metric("capacity.meeting_ratio", 55.0)])
        assert len(alerts) == 1
        assert alerts[0].rule_id == "rule_meeting_overload"
        assert alerts[0].severity == "warning"
        assert alerts[0].threshold_value == 40.0

    def test_meeting_ratio_at_threshold_no_alert(self) -> None:
        alerts = AlertRuleEngine.evaluate_metrics([_metric("capacity.meeting_ratio", 40.0)])
        assert alerts == []

    def test_meeting_ratio_message_contains_percentage(self) -> None:
        alerts = AlertRuleEngine.evaluate_metrics([_metric("capacity.meeting_ratio", 60.0)])
        assert "60.0%" in alerts[0].message


# ── Regra 4 — Project health ──────────────────────────────────────────────────

class TestProjectHealthRule:
    def test_health_below_threshold_critical(self) -> None:
        alerts = AlertRuleEngine.evaluate_metrics([_metric("project.health_score", 60.0)])
        assert len(alerts) == 1
        assert alerts[0].rule_id == "rule_project_health_degraded"
        assert alerts[0].severity == "critical"
        assert alerts[0].threshold_value == 75.0

    def test_health_at_threshold_no_alert(self) -> None:
        alerts = AlertRuleEngine.evaluate_metrics([_metric("project.health_score", 75.0)])
        assert alerts == []

    def test_health_above_threshold_no_alert(self) -> None:
        alerts = AlertRuleEngine.evaluate_metrics([_metric("project.health_score", 90.0)])
        assert alerts == []


# ── Supressão e tipos inválidos ───────────────────────────────────────────────

class TestSuppressedAndInvalidMetrics:
    def test_suppressed_metric_is_ignored(self) -> None:
        alerts = AlertRuleEngine.evaluate_metrics([
            _metric("flow.wip", 10.0, is_suppressed=True)
        ])
        assert alerts == []

    def test_non_numeric_value_is_skipped(self) -> None:
        alerts = AlertRuleEngine.evaluate_metrics([
            {"metric_id": "flow.wip", "value": "not_a_number"}
        ])
        assert alerts == []

    def test_none_value_is_skipped(self) -> None:
        alerts = AlertRuleEngine.evaluate_metrics([
            {"metric_id": "flow.wip", "value": None}
        ])
        assert alerts == []

    def test_unknown_metric_id_produces_no_alert(self) -> None:
        alerts = AlertRuleEngine.evaluate_metrics([_metric("unknown.metric", 9999.0)])
        assert alerts == []

    def test_empty_list_returns_empty(self) -> None:
        assert AlertRuleEngine.evaluate_metrics([]) == []


# ── Anti-Fadiga: MAX_ACTIVE_ALERTS ───────────────────────────────────────────

class TestAntiFatigueFilter:
    def test_more_than_max_alerts_are_capped(self) -> None:
        """Gera 8 alertas WIP e verifica corte em 7."""
        metrics = [_metric("flow.wip", 6.0 + i) for i in range(8)]
        alerts = AlertRuleEngine.evaluate_metrics(metrics)
        assert len(alerts) == AlertRuleEngine.MAX_ACTIVE_ALERTS

    def test_critical_alerts_have_priority_over_warning(self) -> None:
        """Critical deve aparecer antes de warning após ordenação por severidade."""
        metrics = [
            _metric("flow.wip", 6.0),                    # warning
            _metric("flow.lead_time_p85", 10.0),          # critical
            _metric("project.health_score", 50.0),        # critical
            _metric("capacity.meeting_ratio", 50.0),      # warning
        ]
        alerts = AlertRuleEngine.evaluate_metrics(metrics)
        severities = [a.severity for a in alerts]
        first_warning_idx = next(
            (i for i, s in enumerate(severities) if s == "warning"), len(severities)
        )
        for critical_alert in [a for a in alerts if a.severity == "critical"]:
            assert alerts.index(critical_alert) < first_warning_idx

    def test_all_alerts_have_unique_ids(self) -> None:
        metrics = [_metric("flow.wip", 6.0 + i) for i in range(4)]
        alerts = AlertRuleEngine.evaluate_metrics(metrics)
        ids = [a.id for a in alerts]
        assert len(ids) == len(set(ids))


# ── Alert dataclass ───────────────────────────────────────────────────────────

class TestAlertDataclass:
    def test_alert_default_status_is_open(self) -> None:
        alert = Alert(
            id=uuid.uuid4(),
            rule_id="test",
            severity="warning",
            title="T",
            message="M",
            metric_id="flow.wip",
            current_value=6.0,
            threshold_value=5.0,
        )
        assert alert.status == "open"
