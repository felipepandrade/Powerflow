"""Testes unitários para DeduplicationPolicy, ConfidenceRouter e entidades org do domínio."""

from datetime import datetime

from taskflow.domain.entities.org import Area, Milestone, Portfolio, Project, Stakeholder
from taskflow.domain.entities.source import CalendarEvent, SourceItem
from taskflow.domain.policies.confidence_router import ConfidenceRouter, ConfidenceThresholds
from taskflow.domain.policies.deduplication_policy import DeduplicationPolicy
from taskflow.domain.value_objects.enums import (
    AreaKind,
    DecisionKind,
    MilestoneStatus,
    ProjectStatus,
)


def test_deduplication_policy_content_hash() -> None:
    h1 = DeduplicationPolicy.compute_content_hash("  Hello   World!  \n")
    h2 = DeduplicationPolicy.compute_content_hash("hello world!")
    assert h1 == h2


def test_deduplication_policy_source_item() -> None:
    item1 = SourceItem(external_id="ext-123", revision_hash="rev-abc")
    item2 = SourceItem(external_id="ext-123", revision_hash="rev-abc")
    item3 = SourceItem(external_id="ext-123", revision_hash="rev-xyz")

    assert DeduplicationPolicy.is_duplicate_source_item(item1, [item2]) is True
    assert DeduplicationPolicy.is_duplicate_source_item(item1, [item3]) is False


def test_deduplication_policy_calendar_event() -> None:
    now = datetime.utcnow()
    evt1 = CalendarEvent(series_master_id="series-1", starts_at=now, body_hash="hash1")
    evt2 = CalendarEvent(series_master_id="series-1", starts_at=now, body_hash="hash1")
    evt3 = CalendarEvent(series_master_id="series-1", starts_at=now, body_hash="hash2")

    assert DeduplicationPolicy.is_duplicate_calendar_event(evt1, [evt2]) is True
    assert DeduplicationPolicy.is_duplicate_calendar_event(evt1, [evt3]) is False


def test_confidence_router_decisions() -> None:
    router = ConfidenceRouter(ConfidenceThresholds(auto_update_min=0.80, discard_max=0.55))

    # Auto apply
    assert router.should_auto_apply(DecisionKind.UPDATE_EXISTING, 0.85) is True
    assert router.should_auto_apply(DecisionKind.UPDATE_EXISTING, 0.75) is False

    # Triage routing
    assert router.should_route_to_triage(DecisionKind.NEW_TASK, 0.70) is True
    assert router.should_route_to_triage(DecisionKind.NOISE, 0.70) is False

    # Discard
    assert router.should_discard(0.40) is True
    assert router.should_discard(0.60) is False


def test_org_entities() -> None:
    area = Area(name="Engenharia", kind=AreaKind.OWN_TEAM, is_own_team=True)
    assert area.is_own_team is True

    portfolio = Portfolio(name="Inovação 2026")
    assert portfolio.name == "Inovação 2026"

    stakeholder = Stakeholder(email="user@example.com", display_name="João Silva", area_id=area.id)
    assert stakeholder.email == "user@example.com"

    project = Project(name="PowerFlow", status=ProjectStatus.ACTIVE, portfolio_id=portfolio.id)
    assert project.status == ProjectStatus.ACTIVE

    milestone = Milestone(project_id=project.id, name="M1 - MVP", status=MilestoneStatus.PLANNED)
    assert milestone.status == MilestoneStatus.PLANNED
