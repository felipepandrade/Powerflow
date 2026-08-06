"""Testes adicionais para TriageProposalUseCase — cobrindo branches de P1.

Complementa tests/unit/application/test_triage_proposal.py.
Cobre: accept UPDATE, TRANSITION, MERGE, fallback SPLIT/outros;
erros de not-found, already-resolved; resolução de signal associado.
"""

from __future__ import annotations

import uuid
from datetime import date

import pytest

from taskflow.application.dto.commands import AcceptProposalCommand, RejectProposalCommand
from taskflow.application.use_cases.triage_proposal import TriageProposalUseCase
from taskflow.domain.entities.source import Signal
from taskflow.domain.entities.task import Task, TaskProposal
from taskflow.domain.policies.task_state_machine import TaskStateMachine
from taskflow.domain.value_objects.enums import (
    Priority,
    ProposalKind,
    ProposalStatus,
    SignalState,
    SignalType,
    TaskStatus,
)
from tests.fakes import FakeSignalRepository, FakeTaskRepository, FakeUnitOfWork


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_uc() -> tuple[TriageProposalUseCase, FakeSignalRepository, FakeTaskRepository]:
    task_repo = FakeTaskRepository()
    sig_repo = FakeSignalRepository()
    uow = FakeUnitOfWork()
    uc = TriageProposalUseCase(
        task_repo=task_repo,
        signal_repo=sig_repo,
        uow=uow,
        state_machine=TaskStateMachine(),
    )
    return uc, sig_repo, task_repo


def make_task(status: TaskStatus = TaskStatus.INBOX) -> Task:
    return Task(id=uuid.uuid4(), title="Tarefa Existente", status=status)


def make_proposal(
    kind: ProposalKind,
    payload: dict,
    signal_id: uuid.UUID | None = None,
    status: ProposalStatus = ProposalStatus.PENDING,
) -> TaskProposal:
    return TaskProposal(
        id=uuid.uuid4(),
        signal_id=signal_id or uuid.uuid4(),
        proposal_kind=kind,
        payload=payload,
        confidence=0.85,
        status=status,
    )


def make_signal(signal_id: uuid.UUID) -> Signal:
    return Signal(
        id=signal_id,
        source_item_id=uuid.uuid4(),
        signal_type=SignalType.COMMITMENT,
        extraction_conf=0.9,
        state=SignalState.PENDING_CORRELATION,
        payload={},
    )


# ── Accept: UPDATE / TRANSITION ───────────────────────────────────────────────

class TestAcceptUpdate:
    @pytest.mark.asyncio
    async def test_accept_update_applies_fields_to_existing_task(self) -> None:
        uc, sig_repo, task_repo = make_uc()
        task = make_task()
        await task_repo.save(task)

        prop = make_proposal(
            ProposalKind.UPDATE,
            payload={
                "task_id": str(task.id),
                "title": "Título Atualizado",
                "description": "Nova descrição",
                "due_date": "2026-12-31",
            },
        )
        await sig_repo.save(prop)

        res = await uc.accept(AcceptProposalCommand(proposal_id=prop.id))

        assert res.action == "accepted"
        assert res.task_id == task.id
        updated = await task_repo.get_by_id(task.id)
        assert updated is not None
        assert updated.title == "Título Atualizado"
        assert updated.description == "Nova descrição"
        assert updated.due_date == date(2026, 12, 31)

    @pytest.mark.asyncio
    async def test_accept_transition_changes_task_status(self) -> None:
        uc, sig_repo, task_repo = make_uc()
        # INBOX → OPEN → in_progress: state machine exige OPEN antes de in_progress
        task = make_task(status=TaskStatus.OPEN)
        await task_repo.save(task)

        prop = make_proposal(
            ProposalKind.TRANSITION,
            payload={"task_id": str(task.id), "to_status": "in_progress"},
        )
        await sig_repo.save(prop)

        res = await uc.accept(AcceptProposalCommand(proposal_id=prop.id))

        assert res.action == "accepted"
        updated = await task_repo.get_by_id(task.id)
        assert updated is not None
        assert updated.status == TaskStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_accept_transition_to_done_sets_completed_at(self) -> None:
        uc, sig_repo, task_repo = make_uc()
        # IN_PROGRESS → DONE é uma transição válida
        task = make_task(status=TaskStatus.IN_PROGRESS)
        await task_repo.save(task)

        prop = make_proposal(
            ProposalKind.TRANSITION,
            payload={"task_id": str(task.id), "to_status": "done"},
        )
        await sig_repo.save(prop)

        await uc.accept(AcceptProposalCommand(proposal_id=prop.id))

        updated = await task_repo.get_by_id(task.id)
        assert updated is not None
        assert updated.status == TaskStatus.DONE
        assert updated.completed_at is not None

    @pytest.mark.asyncio
    async def test_accept_update_missing_task_id_raises(self) -> None:
        uc, sig_repo, _ = make_uc()
        # payload sem task_id
        prop = make_proposal(ProposalKind.UPDATE, payload={"title": "X"})
        await sig_repo.save(prop)

        with pytest.raises(ValueError, match="requires task_id"):
            await uc.accept(AcceptProposalCommand(proposal_id=prop.id))

    @pytest.mark.asyncio
    async def test_accept_update_task_not_found_raises(self) -> None:
        uc, sig_repo, _ = make_uc()
        prop = make_proposal(
            ProposalKind.UPDATE,
            payload={"task_id": str(uuid.uuid4()), "title": "X"},
        )
        await sig_repo.save(prop)

        with pytest.raises(ValueError, match="not found"):
            await uc.accept(AcceptProposalCommand(proposal_id=prop.id))


# ── Accept: MERGE ─────────────────────────────────────────────────────────────

class TestAcceptMerge:
    @pytest.mark.asyncio
    async def test_accept_merge_returns_primary_task_id(self) -> None:
        uc, sig_repo, task_repo = make_uc()
        primary = make_task()
        await task_repo.save(primary)

        prop = make_proposal(
            ProposalKind.MERGE,
            payload={"primary_task_id": str(primary.id)},
        )
        await sig_repo.save(prop)

        res = await uc.accept(AcceptProposalCommand(proposal_id=prop.id))
        assert res.action == "accepted"
        assert res.task_id == primary.id

    @pytest.mark.asyncio
    async def test_accept_merge_missing_primary_raises(self) -> None:
        uc, sig_repo, _ = make_uc()
        prop = make_proposal(ProposalKind.MERGE, payload={})
        await sig_repo.save(prop)

        with pytest.raises(ValueError, match="primary_task_id"):
            await uc.accept(AcceptProposalCommand(proposal_id=prop.id))

    @pytest.mark.asyncio
    async def test_accept_merge_primary_not_found_raises(self) -> None:
        uc, sig_repo, _ = make_uc()
        prop = make_proposal(
            ProposalKind.MERGE,
            payload={"primary_task_id": str(uuid.uuid4())},
        )
        await sig_repo.save(prop)

        with pytest.raises(ValueError, match="not found"):
            await uc.accept(AcceptProposalCommand(proposal_id=prop.id))


# ── Accept: SPLIT / DISAMBIGUATE (fallback else-branch) ──────────────────────

class TestAcceptFallback:
    @pytest.mark.asyncio
    async def test_accept_split_without_task_id_returns_none_task(self) -> None:
        uc, sig_repo, _ = make_uc()
        prop = make_proposal(ProposalKind.SPLIT, payload={"description": "Dividir em subtarefas"})
        await sig_repo.save(prop)

        res = await uc.accept(AcceptProposalCommand(proposal_id=prop.id))
        assert res.action == "accepted"
        # sem task_id no payload → task_id no resultado é None
        assert res.task_id is None

    @pytest.mark.asyncio
    async def test_accept_split_with_task_id_returns_it(self) -> None:
        uc, sig_repo, task_repo = make_uc()
        task = make_task()
        await task_repo.save(task)

        prop = make_proposal(
            ProposalKind.SPLIT,
            payload={"task_id": str(task.id)},
        )
        await sig_repo.save(prop)

        res = await uc.accept(AcceptProposalCommand(proposal_id=prop.id))
        assert res.task_id == task.id


# ── _get_pending: erros ───────────────────────────────────────────────────────

class TestGetPending:
    @pytest.mark.asyncio
    async def test_proposal_not_found_raises(self) -> None:
        uc, sig_repo, _ = make_uc()
        with pytest.raises(ValueError, match="not found"):
            await uc.accept(AcceptProposalCommand(proposal_id=uuid.uuid4()))

    @pytest.mark.asyncio
    async def test_already_resolved_proposal_raises(self) -> None:
        uc, sig_repo, _ = make_uc()
        prop = make_proposal(
            ProposalKind.NEW_TASK,
            payload={"title": "X"},
            status=ProposalStatus.ACCEPTED,
        )
        await sig_repo.save(prop)

        with pytest.raises(ValueError, match="already resolved"):
            await uc.accept(AcceptProposalCommand(proposal_id=prop.id))


# ── Resolução de signal associado ─────────────────────────────────────────────

class TestSignalResolution:
    @pytest.mark.asyncio
    async def test_accept_resolves_associated_signal(self) -> None:
        uc, sig_repo, _ = make_uc()
        signal_id = uuid.uuid4()
        signal = make_signal(signal_id)
        await sig_repo.save(signal)

        prop = make_proposal(
            ProposalKind.NEW_TASK,
            payload={"title": "Nova tarefa"},
            signal_id=signal_id,
        )
        await sig_repo.save(prop)

        await uc.accept(AcceptProposalCommand(proposal_id=prop.id))

        saved_signal = await sig_repo.get_signal_by_id(signal_id)
        assert saved_signal is not None
        assert saved_signal.state == SignalState.RESOLVED
        assert saved_signal.resolved_task_id is not None
        assert saved_signal.resolved_at is not None

    @pytest.mark.asyncio
    async def test_reject_discards_associated_signal(self) -> None:
        uc, sig_repo, _ = make_uc()
        signal_id = uuid.uuid4()
        signal = make_signal(signal_id)
        await sig_repo.save(signal)

        prop = make_proposal(
            ProposalKind.NEW_TASK,
            payload={"title": "Spam"},
            signal_id=signal_id,
        )
        await sig_repo.save(prop)

        await uc.reject(RejectProposalCommand(proposal_id=prop.id, reason="Irrelevante"))

        saved_signal = await sig_repo.get_signal_by_id(signal_id)
        assert saved_signal is not None
        assert saved_signal.state == SignalState.DISCARDED

    @pytest.mark.asyncio
    async def test_accept_without_linked_signal_does_not_raise(self) -> None:
        """Se não houver sinal associado, deve completar normalmente."""
        uc, sig_repo, _ = make_uc()
        # signal_id aponta para sinal inexistente
        prop = make_proposal(
            ProposalKind.NEW_TASK,
            payload={"title": "Tarefa órfã"},
            signal_id=uuid.uuid4(),
        )
        await sig_repo.save(prop)

        res = await uc.accept(AcceptProposalCommand(proposal_id=prop.id))
        assert res.action == "accepted"

    @pytest.mark.asyncio
    async def test_uow_is_committed_on_accept(self) -> None:
        task_repo = FakeTaskRepository()
        sig_repo = FakeSignalRepository()
        uow = FakeUnitOfWork()
        uc = TriageProposalUseCase(task_repo=task_repo, signal_repo=sig_repo, uow=uow)

        prop = make_proposal(ProposalKind.NEW_TASK, payload={"title": "T"})
        await sig_repo.save(prop)

        await uc.accept(AcceptProposalCommand(proposal_id=prop.id))
        assert uow.committed is True

    @pytest.mark.asyncio
    async def test_uow_is_committed_on_reject(self) -> None:
        task_repo = FakeTaskRepository()
        sig_repo = FakeSignalRepository()
        uow = FakeUnitOfWork()
        uc = TriageProposalUseCase(task_repo=task_repo, signal_repo=sig_repo, uow=uow)

        prop = make_proposal(ProposalKind.NEW_TASK, payload={"title": "T"})
        await sig_repo.save(prop)

        await uc.reject(RejectProposalCommand(proposal_id=prop.id, reason="Reason"))
        assert uow.committed is True


# ── _build_task: prioridade inválida ─────────────────────────────────────────

class TestBuildTask:
    @pytest.mark.asyncio
    async def test_invalid_priority_falls_back_to_medium(self) -> None:
        uc, sig_repo, task_repo = make_uc()
        prop = make_proposal(
            ProposalKind.NEW_TASK,
            payload={"title": "T", "priority": "ultra_high_invalid"},
        )
        await sig_repo.save(prop)

        res = await uc.accept(AcceptProposalCommand(proposal_id=prop.id))
        task = await task_repo.get_by_id(res.task_id)  # type: ignore[arg-type]
        assert task is not None
        assert task.priority == Priority.MEDIUM

    @pytest.mark.asyncio
    async def test_build_task_with_due_date(self) -> None:
        uc, sig_repo, task_repo = make_uc()
        prop = make_proposal(
            ProposalKind.NEW_TASK,
            payload={"title": "Com prazo", "due_date": "2026-11-30"},
        )
        await sig_repo.save(prop)

        res = await uc.accept(AcceptProposalCommand(proposal_id=prop.id))
        task = await task_repo.get_by_id(res.task_id)  # type: ignore[arg-type]
        assert task is not None
        assert task.due_date == date(2026, 11, 30)
