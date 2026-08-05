"""StalenessPolicy — Motor de regras de estagnação — RF-E.1.

Política determinística que avalia o estado de uma tarefa e retorna
as ações de follow-up recomendadas.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from taskflow.domain.value_objects.enums import FollowUpChannel, TaskStatus


class StaleReason(str, Enum):
    """Causa da estagnação detectada."""

    WAITING_TOO_LONG = "waiting_too_long"
    DUE_DATE_APPROACHING = "due_date_approaching"
    DUE_DATE_OVERDUE = "due_date_overdue"
    IN_PROGRESS_NO_UPDATE = "in_progress_no_update"
    BLOCKED_TOO_LONG = "blocked_too_long"
    MEETING_AVAILABLE = "meeting_available"


@dataclass
class StalenessResult:
    """Resultado da avaliação de estagnação de uma tarefa."""

    is_stale: bool
    reason: StaleReason | None
    recommended_channel: FollowUpChannel | None
    meeting_source_id: str | None = None
    priority_escalation: bool = False
    suggest_result_checkin: bool = False

    @property
    def suggest_nudge(self) -> bool:
        """True se deve sugerir um nudge de follow-up."""
        return self.is_stale and self.recommended_channel in (
            FollowUpChannel.EMAIL,
            FollowUpChannel.TEAMS,
        )

    @property
    def suggest_bring_to_meeting(self) -> bool:
        """True se deve substituir nudge por item de pauta de reunião."""
        return self.is_stale and self.recommended_channel == FollowUpChannel.BRING_TO_MEETING


class StalenessPolicy:
    """Avalia estagnação de tarefas e recomenda ações — RF-E.1.

    Implementação 100% determinística e testável sem I/O ou LLM.
    """

    def __init__(
        self,
        waiting_days: int = 3,
        in_progress_days: int = 7,
        blocked_days: int = 5,
        due_date_warning_days: int = 2,
        prefer_meeting_hours: int = 48,
    ) -> None:
        self.waiting_days = waiting_days
        self.in_progress_days = in_progress_days
        self.blocked_days = blocked_days
        self.due_date_warning_days = due_date_warning_days
        self.prefer_meeting_hours = prefer_meeting_hours

    def evaluate(
        self,
        status: TaskStatus,
        last_interaction_at: datetime | None,
        last_activity_at: datetime,
        due_date: datetime | None,
        now: datetime,
        next_meeting_with_blocker_at: datetime | None = None,
        last_meeting_with_blocker_at: datetime | None = None,
        meeting_source_id: str | None = None,
    ) -> StalenessResult:
        """Avalia se uma tarefa está estagnada e qual ação recomendar.

        Args:
            status: Status atual da tarefa.
            last_interaction_at: Última interação com o bloqueador (ledger RF-G.11).
            last_activity_at: Última atividade na tarefa.
            due_date: Data de prazo da tarefa.
            now: Instante atual (injetado para determinismo).
            next_meeting_with_blocker_at: Próxima reunião com o bloqueador.
            last_meeting_with_blocker_at: Reunião passada com o bloqueador.
            meeting_source_id: ID do evento de reunião para BRING_TO_MEETING.
        """
        # Reunião passada com o bloqueador reseta o relógio — RF-F.5 INTERACTION_OCCURRED
        if last_meeting_with_blocker_at and last_meeting_with_blocker_at > (last_interaction_at or datetime.min):
            last_interaction_at = last_meeting_with_blocker_at

        ref_dt = last_interaction_at or last_activity_at

        # Verifica se há reunião próxima que substitui nudge — RF-E.1, RF-F.5 FORUM_AVAILABLE
        if (
            next_meeting_with_blocker_at
            and (next_meeting_with_blocker_at - now).total_seconds() / 3600 < self.prefer_meeting_hours
        ):
            if status == TaskStatus.WAITING_ON_OTHERS:
                hours_stale = (now - ref_dt).total_seconds() / 3600
                if hours_stale >= self.waiting_days * 24:
                    return StalenessResult(
                        is_stale=True,
                        reason=StaleReason.MEETING_AVAILABLE,
                        recommended_channel=FollowUpChannel.BRING_TO_MEETING,
                        meeting_source_id=meeting_source_id,
                    )

        # Verifica reunião passada → sugestão de check-in de resultado
        if last_meeting_with_blocker_at and status == TaskStatus.WAITING_ON_OTHERS:
            meeting_age_hours = (now - last_meeting_with_blocker_at).total_seconds() / 3600
            if meeting_age_hours < 48:  # Reunião recente
                return StalenessResult(
                    is_stale=True,
                    reason=StaleReason.MEETING_AVAILABLE,
                    recommended_channel=FollowUpChannel.EMAIL,
                    suggest_result_checkin=True,
                )

        # Avaliações por status
        if status == TaskStatus.WAITING_ON_OTHERS:
            days_stale = (now - ref_dt).total_seconds() / 86400
            if days_stale >= self.waiting_days:
                return StalenessResult(
                    is_stale=True,
                    reason=StaleReason.WAITING_TOO_LONG,
                    recommended_channel=FollowUpChannel.EMAIL,
                )

        if status == TaskStatus.IN_PROGRESS:
            days_stale = (now - last_activity_at).total_seconds() / 86400
            if days_stale >= self.in_progress_days:
                return StalenessResult(
                    is_stale=True,
                    reason=StaleReason.IN_PROGRESS_NO_UPDATE,
                    recommended_channel=FollowUpChannel.EMAIL,
                )

        if status == TaskStatus.BLOCKED:
            days_stale = (now - last_activity_at).total_seconds() / 86400
            if days_stale >= self.blocked_days:
                return StalenessResult(
                    is_stale=True,
                    reason=StaleReason.BLOCKED_TOO_LONG,
                    recommended_channel=FollowUpChannel.EMAIL,
                )

        # Verificação de prazo
        if due_date and status not in (TaskStatus.DONE, TaskStatus.CANCELLED):
            days_to_due = (due_date - now).total_seconds() / 86400
            if days_to_due < 0:
                return StalenessResult(
                    is_stale=True,
                    reason=StaleReason.DUE_DATE_OVERDUE,
                    recommended_channel=FollowUpChannel.EMAIL,
                    priority_escalation=True,
                )
            if days_to_due <= self.due_date_warning_days:
                return StalenessResult(
                    is_stale=True,
                    reason=StaleReason.DUE_DATE_APPROACHING,
                    recommended_channel=FollowUpChannel.EMAIL,
                )

        return StalenessResult(
            is_stale=False,
            reason=None,
            recommended_channel=None,
        )
