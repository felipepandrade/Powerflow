"""Human triage for durable task proposals."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from taskflow.application.dto.commands import (
    AcceptProposalCommand,
    RejectProposalCommand,
    TriageResult,
)
from taskflow.domain.entities.task import Task, TaskProposal, TaskStatusHistory
from taskflow.domain.policies.task_state_machine import TaskStateMachine
from taskflow.domain.ports.ports import SignalRepository, TaskRepository, UnitOfWork
from taskflow.domain.value_objects.enums import (
    ActorType,
    Priority,
    ProposalKind,
    ProposalStatus,
    SignalState,
    TaskStatus,
)


class TriageProposalUseCase:
    """Apply or reject a persisted proposal without signal/proposal type confusion."""

    def __init__(
        self,
        task_repo: TaskRepository,
        signal_repo: SignalRepository,
        uow: UnitOfWork,
        state_machine: TaskStateMachine | None = None,
    ) -> None:
        self._task_repo = task_repo
        self._signal_repo = signal_repo
        self._uow = uow
        self._state_machine = state_machine or TaskStateMachine()

    async def accept(self, cmd: AcceptProposalCommand) -> TriageResult:
        proposal = await self._get_pending(cmd.proposal_id)
        payload = dict(proposal.payload)
        edits = dict(cmd.user_edits or {})
        payload.update(edits)
        task_id: uuid.UUID | None = None

        async with self._uow:
            if proposal.proposal_kind == ProposalKind.NEW_TASK:
                task = self._build_task(payload)
                await self._task_repo.save(task)
                task_id = task.id
            elif proposal.proposal_kind in (
                ProposalKind.UPDATE,
                ProposalKind.TRANSITION,
            ):
                raw_task_id = payload.get("task_id")
                if raw_task_id is None:
                    raise ValueError("Triage update requires task_id")
                existing_task = await self._task_repo.get_by_id(uuid.UUID(str(raw_task_id)))
                if existing_task is None:
                    raise ValueError(f"Task {raw_task_id} not found")
                task_id = await self._apply_to_task(existing_task, payload)
            elif proposal.proposal_kind == ProposalKind.MERGE:
                raw_primary = payload.get("primary_task_id")
                if raw_primary is None:
                    raise ValueError("Merge requires primary_task_id")
                primary = await self._task_repo.get_by_id(uuid.UUID(str(raw_primary)))
                if primary is None:
                    raise ValueError(f"Task {raw_primary} not found")
                task_id = primary.id
            else:
                raw_task_id = payload.get("task_id")
                task_id = uuid.UUID(str(raw_task_id)) if raw_task_id else None

            proposal.status = ProposalStatus.ACCEPTED
            proposal.resolved_task_id = task_id
            proposal.user_edits = edits or None
            proposal.resolved_at = datetime.utcnow()
            await self._signal_repo.save(proposal)
            signal = await self._signal_repo.get_signal_by_id(proposal.signal_id)
            if signal is not None:
                signal.state = SignalState.RESOLVED
                signal.resolved_task_id = task_id
                signal.resolved_at = datetime.utcnow()
                await self._signal_repo.save(signal)
            await self._uow.commit()

        return TriageResult(
            proposal_id=proposal.id,
            task_id=task_id,
            action="accepted",
            updated_fields=list(edits),
        )

    async def reject(self, cmd: RejectProposalCommand) -> TriageResult:
        proposal = await self._get_pending(cmd.proposal_id)
        async with self._uow:
            proposal.status = ProposalStatus.REJECTED
            proposal.rejection_reason = cmd.reason
            proposal.resolved_at = datetime.utcnow()
            await self._signal_repo.save(proposal)
            signal = await self._signal_repo.get_signal_by_id(proposal.signal_id)
            if signal is not None:
                signal.state = SignalState.DISCARDED
                signal.resolved_at = datetime.utcnow()
                await self._signal_repo.save(signal)
            await self._uow.commit()
        return TriageResult(proposal.id, None, "rejected", [])

    async def _get_pending(self, proposal_id: uuid.UUID) -> TaskProposal:
        proposal = await self._signal_repo.get_proposal_by_id(proposal_id)
        if proposal is None:
            raise ValueError(f"Proposal {proposal_id} not found")
        if proposal.status != ProposalStatus.PENDING:
            raise ValueError(f"Proposal {proposal_id} is already resolved")
        return proposal

    @staticmethod
    def _build_task(payload: dict[str, Any]) -> Task:
        try:
            priority = Priority(str(payload.get("priority", Priority.MEDIUM.value)))
        except ValueError:
            priority = Priority.MEDIUM
        due_raw = payload.get("due_date")
        task = Task(
            title=str(payload.get("title") or "Untitled task"),
            description=str(payload["description"]) if payload.get("description") else None,
            priority=priority,
            due_date=date.fromisoformat(str(due_raw)) if due_raw else None,
            auto_created=True,
        )
        task.status_history.append(TaskStatusHistory(
            task_id=task.id,
            from_status=None,
            to_status=task.status,
            actor=ActorType.USER,
            reason="accepted triage proposal",
        ))
        return task

    async def _apply_to_task(
        self, task: Task, payload: dict[str, Any]
    ) -> uuid.UUID:
        status_raw = payload.get("to_status")
        if status_raw is not None:
            next_status = TaskStatus(str(status_raw))
            self._state_machine.validate(task.status, next_status)
            task.status_history.append(TaskStatusHistory(
                task_id=task.id,
                from_status=task.status,
                to_status=next_status,
                actor=ActorType.USER,
                reason="accepted triage proposal",
                snapshot=task.snapshot_dict(),
            ))
            task.status = next_status
            task.completed_at = datetime.utcnow() if next_status == TaskStatus.DONE else None
        if payload.get("title") is not None:
            task.title = str(payload["title"])
        if payload.get("description") is not None:
            task.description = str(payload["description"])
        if payload.get("due_date") is not None:
            task.due_date = date.fromisoformat(str(payload["due_date"]))
        task.updated_at = datetime.utcnow()
        task.last_activity_at = datetime.utcnow()
        await self._task_repo.save(task)
        return task.id
