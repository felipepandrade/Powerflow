"""Use Case: ManageTask — UC-3.

Operações CRUD de tarefas com:
- Validação de transições via TaskStateMachine
- Registro de histórico (audit trail)
- Suporte a Undo (RF-D.3)
"""

from __future__ import annotations

import uuid
from datetime import datetime

import structlog

from taskflow.application.dto.commands import (
    CreateTaskCommand,
    TaskView,
    TransitionTaskCommand,
    UndoLastTransitionCommand,
    UpdateTaskCommand,
)
from taskflow.domain.entities.task import Task, TaskStatusHistory
from taskflow.domain.policies.task_state_machine import TaskStateMachine
from taskflow.domain.ports.ports import TaskRepository, UnitOfWork
from taskflow.domain.value_objects.enums import ActorType, TaskStatus

log = structlog.get_logger()


class ManageTaskUseCase:
    """UC-3 — Gerenciamento de tarefas com machine de estados e undo.

    Esta classe consolida as operações de criação, atualização, transição e
    reversão de estado, mantendo o histórico completo para auditoria.
    """

    def __init__(
        self,
        task_repo: TaskRepository,
        uow: UnitOfWork,
        state_machine: TaskStateMachine | None = None,
    ) -> None:
        self._repo = task_repo
        self._uow = uow
        self._sm = state_machine or TaskStateMachine()

    # ─── Criação ─────────────────────────────────────────────────────────────

    async def create(self, cmd: CreateTaskCommand) -> TaskView:
        """Cria uma nova tarefa manualmente."""
        task = Task(
            id=uuid.uuid4(),
            title=cmd.title,
            description=cmd.description,
            priority=cmd.priority,
            due_date=cmd.due_date,
            project_id=cmd.project_id,
            parent_task_id=cmd.parent_task_id,
            status=TaskStatus.INBOX,
            auto_created=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            last_activity_at=datetime.utcnow(),
        )
        initial_history = TaskStatusHistory(
            task_id=task.id,
            from_status=None,
            to_status=TaskStatus.INBOX,
            actor=ActorType.USER,
            reason="criação manual",
        )
        task.status_history.append(initial_history)

        async with self._uow:
            await self._repo.save(task)
            await self._uow.commit()

        log.info("task.created", task_id=str(task.id), title=task.title)
        return self._to_view(task)

    # ─── Atualização ─────────────────────────────────────────────────────────

    async def update(self, cmd: UpdateTaskCommand) -> TaskView:
        """Atualiza campos de uma tarefa existente."""
        task = await self._get_or_raise(cmd.task_id)

        if cmd.title is not None:
            task.title = cmd.title
        if cmd.description is not None:
            task.description = cmd.description
        if cmd.priority is not None:
            task.priority = cmd.priority
        if cmd.due_date is not None:
            task.due_date = cmd.due_date
            task.due_date_source = "manual"
        if cmd.project_id is not None:
            task.project_id = cmd.project_id
        if cmd.waiting_on_id is not None:
            task.waiting_on_id = cmd.waiting_on_id
        if cmd.snooze_until is not None:
            task.snooze_until = cmd.snooze_until

        task.updated_at = datetime.utcnow()
        task.last_activity_at = datetime.utcnow()

        async with self._uow:
            await self._repo.save(task)
            await self._uow.commit()

        log.info("task.updated", task_id=str(task.id))
        return self._to_view(task)

    # ─── Transição de Estado ─────────────────────────────────────────────────

    async def transition(self, cmd: TransitionTaskCommand) -> TaskView:
        """Transiciona o estado de uma tarefa — valida via TaskStateMachine."""
        task = await self._get_or_raise(cmd.task_id)

        # Valida a transição — levanta InvalidTransitionError se inválida
        self._sm.validate(task.status, cmd.to_status)

        snapshot = task.snapshot_dict()
        history = TaskStatusHistory(
            task_id=task.id,
            from_status=task.status,
            to_status=cmd.to_status,
            actor=ActorType.USER,
            reason=cmd.reason,
            signal_id=cmd.signal_id,
            snapshot=snapshot,
        )
        task.status = cmd.to_status
        task.status_history.append(history)
        task.updated_at = datetime.utcnow()
        task.last_activity_at = datetime.utcnow()

        if cmd.to_status == TaskStatus.DONE:
            task.completed_at = datetime.utcnow()

        async with self._uow:
            await self._repo.save(task)
            await self._uow.commit()

        log.info(
            "task.transitioned",
            task_id=str(task.id),
            from_status=history.from_status,
            to_status=cmd.to_status.value,
        )
        return self._to_view(task)

    # ─── Undo ─────────────────────────────────────────────────────────────────

    async def undo_last_transition(self, cmd: UndoLastTransitionCommand) -> TaskView:
        """Reverte a última transição de estado — RF-D.3.

        Usa o snapshot guardado no TaskStatusHistory para restaurar o estado anterior.
        Apenas a transição mais recente pode ser revertida (single-step undo).
        """
        task = await self._get_or_raise(cmd.task_id)

        # Filtra histórico não desfeito
        undoable = [h for h in task.status_history if not h.is_undone and h.from_status is not None]

        if not undoable:
            raise ValueError(f"Tarefa {task.id} não tem transições revertíveis.")

        # Pega a última inserida (evita problemas com timestamps idênticos em testes)
        last = undoable[-1]
        last.is_undone = True
        last.undone_at = datetime.utcnow()

        # Restaura do snapshot
        if last.snapshot:
            try:
                task.status = TaskStatus(last.snapshot["status"])
            except (KeyError, ValueError):
                task.status = last.from_status  # type: ignore[assignment]
        else:
            task.status = last.from_status  # type: ignore[assignment]

        task.updated_at = datetime.utcnow()
        task.last_activity_at = datetime.utcnow()

        # Registra o undo no histórico
        undo_record = TaskStatusHistory(
            task_id=task.id,
            from_status=last.to_status,
            to_status=task.status,
            actor=ActorType.USER,
            reason=f"undo de transição {last.id}",
        )
        task.status_history.append(undo_record)

        async with self._uow:
            await self._repo.save(task)
            await self._uow.commit()

        log.info("task.undo", task_id=str(task.id), restored_status=task.status.value)
        return self._to_view(task)

    # ─── Helpers ─────────────────────────────────────────────────────────────

    async def _get_or_raise(self, task_id: uuid.UUID) -> Task:
        """Busca uma tarefa ou levanta ValueError."""
        task = await self._repo.get_by_id(task_id)
        if task is None:
            raise ValueError(f"Tarefa {task_id} não encontrada.")
        return task  # type: ignore[return-value]

    def _to_view(self, task: Task) -> TaskView:
        """Converte entidade para DTO de leitura."""
        return TaskView(
            id=task.id,
            title=task.title,
            description=task.description,
            status=task.status,
            priority=task.priority,
            due_date=task.due_date,
            project_id=task.project_id,
            waiting_on_id=task.waiting_on_id,
            last_activity_at=task.last_activity_at,
            created_at=task.created_at,
            updated_at=task.updated_at,
            evidence_count=len(task.evidence),
            update_count=len(task.updates),
        )
