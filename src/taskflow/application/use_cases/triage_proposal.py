"""Use Case: TriageProposal — UC-4.

Gerencia o fluxo de triagem: aceitar, rejeitar ou desambiguar propostas.
Inclui registro de edições do usuário para o feedback loop (RF-C.6).
"""

from __future__ import annotations

import uuid
from datetime import datetime

import structlog

from taskflow.application.dto.commands import (
    AcceptProposalCommand,
    RejectProposalCommand,
    TriageResult,
)
from taskflow.domain.entities.task import Task, TaskProposal
from taskflow.domain.policies.task_state_machine import TaskStateMachine
from taskflow.domain.ports.ports import SignalRepository, TaskRepository, UnitOfWork
from taskflow.domain.value_objects.enums import (
    ActorType,
    Priority,
    ProposalStatus,
    TaskStatus,
)

log = structlog.get_logger()


class TriageProposalUseCase:
    """UC-4 — Triagem de propostas pelo usuário.

    O usuário pode aceitar (com ou sem edições) ou rejeitar uma proposta.
    Edições são registradas para o feedback loop (RF-C.6) que retreina
    os limiares da CorrelationPolicy.
    """

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
        self._sm = state_machine or TaskStateMachine()

    async def accept(self, cmd: AcceptProposalCommand) -> TriageResult:
        """Aceita uma proposta, criando ou atualizando a tarefa correspondente."""
        proposal = await self._get_proposal_or_raise(cmd.proposal_id)

        updated_fields: list[str] = []
        task_id: uuid.UUID | None = None

        # Mescla edições do usuário com o payload original
        final_payload = {**proposal.payload}
        if cmd.user_edits:
            final_payload.update(cmd.user_edits)
            updated_fields = list(cmd.user_edits.keys())
            proposal.user_edits = cmd.user_edits  # Registra para feedback RF-C.6

        from taskflow.domain.value_objects.enums import ProposalKind
        async with self._uow:
            if proposal.proposal_kind == ProposalKind.NEW_TASK:
                task = self._build_task_from_payload(final_payload)
                await self._task_repo.save(task)
                task_id = task.id

            elif proposal.proposal_kind in (ProposalKind.UPDATE, ProposalKind.TRANSITION):
                task_id_raw = final_payload.get("task_id")
                if task_id_raw:
                    task = await self._task_repo.get_by_id(uuid.UUID(task_id_raw))
                    if task is not None:
                        task_id = await self._apply_payload_to_task(task, final_payload)
                        updated_fields = list(final_payload.keys())

            elif proposal.proposal_kind == ProposalKind.MERGE:
                task_id = await self._merge_tasks(final_payload)

            # Atualiza status da proposta
            proposal.status = ProposalStatus.ACCEPTED
            proposal.resolved_task_id = task_id
            proposal.resolved_at = datetime.utcnow()
            
            # [MVP BYPASS] Se a proposal for na verdade um Signal mockado,
            # atualiza o estado do Signal original para removê-lo da triagem
            from taskflow.domain.entities.source import Signal
            from taskflow.domain.value_objects.enums import SignalState
            
            # Busca o Signal original no banco de dados para alterar seu state
            # já que o SqlAlchemySignalRepository.save só aceita Signal ou SourceItem.
            signals = await self._signal_repo.get_pending(limit=1000)
            for s in signals:
                if s.id == proposal.id:
                    s.state = SignalState.RESOLVED
                    s.resolved_task_id = task_id
                    s.resolved_at = datetime.utcnow()
                    await self._signal_repo.save(s)  # type: ignore[arg-type]
                    break
            
            await self._uow.commit()

        log.info("triage.accepted", proposal_id=str(cmd.proposal_id), task_id=str(task_id))
        return TriageResult(
            proposal_id=cmd.proposal_id,
            task_id=task_id,
            action="accepted",
            updated_fields=updated_fields,
        )

    async def reject(self, cmd: RejectProposalCommand) -> TriageResult:
        """Rejeita uma proposta e registra o motivo."""
        proposal = await self._get_proposal_or_raise(cmd.proposal_id)

        async with self._uow:
            proposal.status = ProposalStatus.REJECTED
            proposal.rejection_reason = cmd.reason
            proposal.resolved_at = datetime.utcnow()
            
            # [MVP BYPASS] Atualiza o Signal original para removê-lo da triagem
            from taskflow.domain.value_objects.enums import SignalState
            signals = await self._signal_repo.get_pending(limit=1000)
            for s in signals:
                if s.id == proposal.id:
                    s.state = SignalState.DISCARDED
                    s.resolved_at = datetime.utcnow()
                    await self._signal_repo.save(s)  # type: ignore[arg-type]
                    break
                    
            await self._uow.commit()

        log.info("triage.rejected", proposal_id=str(cmd.proposal_id), reason=cmd.reason)
        return TriageResult(
            proposal_id=cmd.proposal_id,
            task_id=None,
            action="rejected",
            updated_fields=[],
        )

    async def _get_proposal_or_raise(self, proposal_id: uuid.UUID) -> TaskProposal:
        """Busca a proposta pelo ID — mock via signal_repo por ora."""
        # Em produção: ProposalRepository separado
        # Por ora, delegamos ao adaptador que implementa a interface
        proposals = await self._signal_repo.get_pending(limit=1000)
        for p in proposals:
            if p.id == proposal_id:
                if not hasattr(p, "proposal_kind"):
                    from taskflow.domain.value_objects.enums import ProposalKind
                    # [MVP BYPASS] Converte o Signal PENDING_CORRELATION para uma Proposal fake
                    return TaskProposal(
                        id=p.id, # type: ignore
                        signal_id=p.id, # type: ignore
                        proposal_kind=ProposalKind.NEW_TASK,
                        payload=getattr(p, "payload", {}),
                        confidence=1.0
                    )
                return p  # type: ignore[return-value]
        raise ValueError(f"Proposta {proposal_id} não encontrada.")

    def _build_task_from_payload(self, payload: dict) -> Task:
        """Constrói uma tarefa a partir do payload aceito."""
        priority = Priority.MEDIUM
        priority_raw = payload.get("priority")
        if priority_raw:
            try:
                priority = Priority(priority_raw)
            except ValueError:
                pass

        return Task(
            id=uuid.uuid4(),
            title=payload.get("title", "Tarefa sem título"),
            description=payload.get("description"),
            priority=priority,
            status=TaskStatus.INBOX,
            auto_created=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            last_activity_at=datetime.utcnow(),
        )

    async def _apply_payload_to_task(self, task: Task, payload: dict) -> uuid.UUID:
        """Aplica as mudanças do payload a uma tarefa existente."""
        from taskflow.domain.entities.task import TaskStatusHistory

        if "to_status" in payload:
            try:
                new_status = TaskStatus(payload["to_status"])
                self._sm.validate(task.status, new_status)
                history = TaskStatusHistory(
                    task_id=task.id,
                    from_status=task.status,
                    to_status=new_status,
                    actor=ActorType.USER,
                    reason="triagem",
                    snapshot=task.snapshot_dict(),
                )
                task.status = new_status
                task.status_history.append(history)
            except Exception as e:  # noqa: BLE001
                log.warning("triage.invalid_transition", error=str(e))

        if "title" in payload:
            task.title = payload["title"]
        if "description" in payload:
            task.description = payload["description"]
        if "due_date" in payload:
            import datetime as dt
            raw = payload["due_date"]
            if isinstance(raw, str):
                task.due_date = dt.date.fromisoformat(raw)
            elif isinstance(raw, dt.date):
                task.due_date = raw

        task.updated_at = datetime.utcnow()
        task.last_activity_at = datetime.utcnow()
        await self._task_repo.save(task)
        return task.id

    async def _merge_tasks(self, payload: dict) -> uuid.UUID | None:
        """Funde duas tarefas duplicadas mantendo a primária."""
        primary_id_raw = payload.get("primary_task_id")
        if not primary_id_raw:
            return None
        try:
            primary_id = uuid.UUID(primary_id_raw)
        except ValueError:
            return None
        task = await self._task_repo.get_by_id(primary_id)
        if task is None:
            return None
        task.updated_at = datetime.utcnow()
        await self._task_repo.save(task)
        return task.id  # type: ignore[union-attr]
