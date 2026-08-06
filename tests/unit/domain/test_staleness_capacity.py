"""Testes unitários para StalenessPolicy e CapacityPolicy — RF-E.1, RF-F.6."""

from datetime import UTC, datetime, time, timedelta

import pytest

from taskflow.domain.policies.capacity_policy import CapacityPolicy, TimeBlock
from taskflow.domain.policies.staleness_policy import StalenessPolicy, StaleReason
from taskflow.domain.value_objects.enums import FollowUpChannel, TaskStatus

staleness = StalenessPolicy()
NOW = datetime(2026, 8, 4, 10, 0, 0)


class TestStalenessWaitingOnOthers:
    """RF-E.1: waiting_on_others sem interação > X dias."""

    def test_waiting_stale(self) -> None:
        last = NOW - timedelta(days=4)
        result = staleness.evaluate(
            status=TaskStatus.WAITING_ON_OTHERS,
            last_interaction_at=last,
            last_activity_at=last,
            due_date=None,
            now=NOW,
        )
        assert result.is_stale
        assert result.reason == StaleReason.WAITING_TOO_LONG

    def test_waiting_not_stale(self) -> None:
        last = NOW - timedelta(days=1)
        result = staleness.evaluate(
            status=TaskStatus.WAITING_ON_OTHERS,
            last_interaction_at=last,
            last_activity_at=last,
            due_date=None,
            now=NOW,
        )
        assert not result.is_stale


class TestStalenessFollowUpChannels:
    """RF-E.1: FORUM_AVAILABLE substitui nudge por BRING_TO_MEETING."""

    def test_meeting_within_48h_replaces_nudge(self) -> None:
        """Reunião futura com o bloqueador em < 48h → bring_to_meeting."""
        last = NOW - timedelta(days=5)
        next_meeting = NOW + timedelta(hours=20)
        result = staleness.evaluate(
            status=TaskStatus.WAITING_ON_OTHERS,
            last_interaction_at=last,
            last_activity_at=last,
            due_date=None,
            now=NOW,
            next_meeting_with_blocker_at=next_meeting,
            meeting_source_id="meeting-abc",
        )
        assert result.is_stale
        assert result.recommended_channel == FollowUpChannel.BRING_TO_MEETING
        assert result.meeting_source_id == "meeting-abc"

    def test_past_meeting_resets_clock_and_suggests_checkin(self) -> None:
        """Reunião passada recente com bloqueador → reseta relógio."""
        last_interaction = NOW - timedelta(days=7)
        last_meeting = NOW - timedelta(hours=12)
        result = staleness.evaluate(
            status=TaskStatus.WAITING_ON_OTHERS,
            last_interaction_at=last_interaction,
            last_activity_at=last_interaction,
            due_date=None,
            now=NOW,
            last_meeting_with_blocker_at=last_meeting,
        )
        assert result.suggest_result_checkin


class TestStalenessInProgress:
    """RF-E.1: in_progress sem update > 7 dias."""

    def test_in_progress_stale(self) -> None:
        last = NOW - timedelta(days=8)
        result = staleness.evaluate(
            status=TaskStatus.IN_PROGRESS,
            last_interaction_at=None,
            last_activity_at=last,
            due_date=None,
            now=NOW,
        )
        assert result.is_stale
        assert result.reason == StaleReason.IN_PROGRESS_NO_UPDATE


class TestStalenessBlocked:
    """RF-E.1: blocked > 5 dias."""

    def test_blocked_stale(self) -> None:
        last = NOW - timedelta(days=6)
        result = staleness.evaluate(
            status=TaskStatus.BLOCKED,
            last_interaction_at=None,
            last_activity_at=last,
            due_date=None,
            now=NOW,
        )
        assert result.is_stale
        assert result.reason == StaleReason.BLOCKED_TOO_LONG


class TestStalenessDueDate:
    """RF-E.1: prazo próximo e prazo vencido."""

    def test_due_date_approaching(self) -> None:
        due = NOW + timedelta(days=1)
        result = staleness.evaluate(
            status=TaskStatus.OPEN,
            last_interaction_at=None,
            last_activity_at=NOW - timedelta(hours=1),
            due_date=due,
            now=NOW,
        )
        assert result.is_stale
        assert result.reason == StaleReason.DUE_DATE_APPROACHING

    def test_due_date_overdue(self) -> None:
        due = NOW - timedelta(days=2)
        result = staleness.evaluate(
            status=TaskStatus.OPEN,
            last_interaction_at=None,
            last_activity_at=NOW - timedelta(hours=1),
            due_date=due,
            now=NOW,
        )
        assert result.is_stale
        assert result.reason == StaleReason.DUE_DATE_OVERDUE
        assert result.priority_escalation

    def test_done_ignores_due_date(self) -> None:
        due = NOW - timedelta(days=5)
        result = staleness.evaluate(
            status=TaskStatus.DONE,
            last_interaction_at=None,
            last_activity_at=NOW - timedelta(hours=1),
            due_date=due,
            now=NOW,
        )
        assert not result.is_stale



    def test_all_day_and_timezone_are_handled(self) -> None:

        blocks = [
            TimeBlock(
                starts_at=datetime(2026, 8, 3, 12, 0, tzinfo=UTC),
                ends_at=datetime(2026, 8, 3, 13, 0, tzinfo=UTC),
            ),
            TimeBlock(
                starts_at=MONDAY,
                ends_at=MONDAY + timedelta(days=1),
                is_all_day=True,
            ),
        ]
        result = capacity.compute(MONDAY, blocks)
        assert result.meeting_minutes == pytest.approx(60)
        assert len(result.blocks) == 1


# ─── CapacityPolicy Tests ───────────────────────────────────────────


capacity = CapacityPolicy(
    work_start=time(8, 30),
    work_end=time(18, 0),
    work_days=frozenset({0, 1, 2, 3, 4}),
    buffer_minutes=60,
)

MONDAY = datetime(2026, 8, 3, 0, 0, 0)  # Segunda-feira
SATURDAY = datetime(2026, 8, 8, 0, 0, 0)  # Sábado


class TestCapacityWorkDay:
    """RF-F.6: Horas livres em dias úteis."""

    def test_no_meetings_full_capacity(self) -> None:
        result = capacity.compute(MONDAY, [])
        assert result.is_work_day
        # 8h30 às 18h = 570 min - 60 buffer = 510 min livres
        assert result.free_minutes == pytest.approx(510, abs=1)

    def test_overloaded_day(self) -> None:
        """Dia com > 8h de reuniões → sobrecarregado."""
        blocks = [
            TimeBlock(
                starts_at=MONDAY.replace(hour=8, minute=30),
                ends_at=MONDAY.replace(hour=18, minute=0),
            )
        ]
        result = capacity.compute(MONDAY, blocks)
        assert result.is_overloaded
        assert result.free_minutes == 0

    def test_overlapping_meetings_not_double_counted(self) -> None:
        """Reuniões sobrepostas não são contadas duplamente."""
        blocks = [
            TimeBlock(
                starts_at=MONDAY.replace(hour=9),
                ends_at=MONDAY.replace(hour=11),
            ),
            TimeBlock(
                starts_at=MONDAY.replace(hour=10),
                ends_at=MONDAY.replace(hour=12),
            ),
        ]
        result = capacity.compute(MONDAY, blocks)
        # Apenas 3h de reunião efetiva (9-12), não 4h
        assert result.meeting_minutes == pytest.approx(180, abs=1)


class TestCapacityNonWorkDay:
    """RF-F.6: Final de semana e dias não úteis."""

    def test_saturday_no_capacity(self) -> None:
        result = capacity.compute(SATURDAY, [])
        assert not result.is_work_day
        assert result.total_work_minutes == 0
        assert result.free_minutes == 0
