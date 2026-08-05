"""Use Case: ScanStaleItems — UC-5.

Varre tarefas ativas, aplica StalenessPolicy e cria FollowUps sugeridos.
Considerações:
- FORUM_AVAILABLE: Próxima reunião com bloqueador → BRING_TO_MEETING
- INTERACTION_OCCURRED: Reunião passada recente → reset do relógio
"""

from __future__ import annotations

import uuid
from datetime import datetime

import structlog

from taskflow.application.dto.commands import (
    ScanStaleItemsCommand,
    ScanStaleItemsResult,
    StaleTaskReport,
)
from taskflow.domain.entities.task import FollowUp, Task
from taskflow.domain.policies.staleness_policy import StalenessPolicy
from taskflow.domain.ports.ports import (
    Clock,
    SignalRepository,
    SystemClock,
    TaskRepository,
    UnitOfWork,
)
from taskflow.domain.value_objects.enums import FollowUpChannel, FollowUpStatus, TaskStatus

log = structlog.get_logger()

# Status de tarefas que participam da varredura de estagnação
STALE_CANDIDATE_STATUSES = [
    TaskStatus.WAITING_ON_OTHERS.value,
    TaskStatus.IN_PROGRESS.value,
    TaskStatus.BLOCKED.value,
    TaskStatus.OPEN.value,
]


class ScanStaleItemsUseCase:
    """UC-5 — Varredura de estagnação e geração de follow-ups.

    Implementa todas as regras de RF-E.1 de forma determinística.
    Usa Clock injetado para facilitar testes.
    """

    def __init__(
        self,
        task_repo: TaskRepository,
        signal_repo: SignalRepository,
        uow: UnitOfWork,
        staleness_policy: StalenessPolicy | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._task_repo = task_repo
        self._signal_repo = signal_repo
        self._uow = uow
        self._staleness = staleness_policy or StalenessPolicy()
        self._clock = clock or SystemClock()

    async def execute(self, cmd: ScanStaleItemsCommand) -> ScanStaleItemsResult:
        """Executa a varredura e cria follow-ups para tarefas estagnadas."""
        now = self._clock.now()
        log.info("scan_stale.start", now=now.isoformat(), dry_run=cmd.dry_run)

        tasks = await self._task_repo.find_active(
            status_filter=STALE_CANDIDATE_STATUSES,
            limit=500,
        )

        reports: list[StaleTaskReport] = []
        follow_ups_created = 0

        for task in tasks:
            report = await self._evaluate_task(task, now, cmd.dry_run)
            if report is not None:
                reports.append(report)
                if report.follow_up_id is not None:
                    follow_ups_created += 1

        log.info(
            "scan_stale.done",
            total_scanned=len(tasks),
            stale_count=len(reports),
            follow_ups_created=follow_ups_created,
        )

        return ScanStaleItemsResult(
            total_scanned=len(tasks),
            stale_count=len(reports),
            follow_ups_created=follow_ups_created,
            reports=reports,
        )

    async def _evaluate_task(
        self,
        task: Task,
        now: datetime,
        dry_run: bool,
    ) -> StaleTaskReport | None:
        """Avalia uma tarefa e cria follow-up se estagnada."""
        # Obtém informações de reunião do contexto (simplificado para MVP)
        next_meeting_at, meeting_source_id, last_meeting_at = self._get_meeting_context(task)

        staleness = self._staleness.evaluate(
            status=task.status,
            last_interaction_at=task.last_interaction_at,
            last_activity_at=task.last_activity_at,
            due_date=datetime(
                task.due_date.year,
                task.due_date.month,
                task.due_date.day,
            ) if task.due_date else None,
            now=now,
            next_meeting_with_blocker_at=next_meeting_at,
            last_meeting_with_blocker_at=last_meeting_at,
            meeting_source_id=meeting_source_id,
        )

        if not staleness.is_stale:
            return None

        follow_up_id: uuid.UUID | None = None

        if not dry_run:
            follow_up = FollowUp(
                id=uuid.uuid4(),
                task_id=task.id,
                rule_id=staleness.reason.value if staleness.reason else "unknown",
                channel=staleness.recommended_channel or FollowUpChannel.EMAIL,
                target_meeting_id=uuid.UUID(meeting_source_id) if staleness.suggest_bring_to_meeting and meeting_source_id else None,
                suggested_at=now,
                status=FollowUpStatus.SUGGESTED,
            )
            async with self._uow:
                await self._signal_repo.save(follow_up)  # type: ignore[arg-type]
                await self._uow.commit()
            follow_up_id = follow_up.id

        return StaleTaskReport(
            task_id=task.id,
            task_title=task.title,
            stale_reason=staleness.reason.value if staleness.reason else "unknown",
            recommended_channel=staleness.recommended_channel,
            follow_up_id=follow_up_id,
            suggest_bring_to_meeting=staleness.suggest_bring_to_meeting,
            meeting_source_id=meeting_source_id,
        )

    def _get_meeting_context(
        self,
        task: Task,
    ) -> tuple[datetime | None, str | None, datetime | None]:
        """Obtém contexto de reunião com o bloqueador — simplificado para MVP.

        Em produção: consulta CalendarEvent com attendees que incluem waiting_on.
        Returns: (next_meeting_at, meeting_source_id, last_meeting_at)
        """
        # MVP: sem contexto de reunião automático — usa interação manual
        return None, None, None
