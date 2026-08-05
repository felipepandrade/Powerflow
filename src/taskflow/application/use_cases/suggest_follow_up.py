"""Use Case: SuggestFollowUp — UC-6.

Gera rascunhos de mensagens de follow-up via LLM — RF-E.2.
"""

from __future__ import annotations

import structlog

from taskflow.application.dto.commands import FollowUpDraft, SuggestFollowUpCommand
from taskflow.domain.ports.ports import LLMProvider, TaskRepository
from taskflow.domain.value_objects.enums import FollowUpChannel

log = structlog.get_logger()


class SuggestFollowUpUseCase:
    """UC-6 — Geração de rascunho de nudge via LLM — RF-E.2.

    Nunca envia automaticamente. O rascunho é apresentado ao usuário
    que confirma antes do envio.
    """

    def __init__(
        self,
        task_repo: TaskRepository,
        llm: LLMProvider,
    ) -> None:
        self._task_repo = task_repo
        self._llm = llm

    async def execute(self, cmd: SuggestFollowUpCommand) -> FollowUpDraft:
        """Gera um rascunho de follow-up para a tarefa."""
        task = await self._task_repo.get_by_id(cmd.task_id)
        if task is None:
            raise ValueError(f"Tarefa {cmd.task_id} não encontrada.")

        task_context = {
            "title": task.title,  # type: ignore[union-attr]
            "description": task.description,  # type: ignore[union-attr]
            "status": task.status.value,  # type: ignore[union-attr]
            "due_date": task.due_date.isoformat() if task.due_date else None,  # type: ignore[union-attr]
        }

        draft_body = await self._llm.draft_follow_up(
            task=task_context,
            context={"channel": cmd.channel.value},
            tone=cmd.tone,
        )

        subject: str | None = None
        if cmd.channel == FollowUpChannel.EMAIL:
            subject = f"Acompanhamento: {task.title}"  # type: ignore[union-attr]

        log.info("follow_up.drafted", task_id=str(cmd.task_id), channel=cmd.channel.value)

        return FollowUpDraft(
            task_id=cmd.task_id,
            channel=cmd.channel,
            subject=subject,
            body=draft_body,
            tone=cmd.tone,
        )
