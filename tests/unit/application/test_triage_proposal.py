"""Testes de integração para TriageProposalUseCase — UC-4."""

import uuid

import pytest

from taskflow.application.dto.commands import AcceptProposalCommand, RejectProposalCommand
from taskflow.application.use_cases.triage_proposal import TriageProposalUseCase
from taskflow.domain.entities.task import TaskProposal
from taskflow.domain.policies.task_state_machine import TaskStateMachine
from taskflow.domain.value_objects.enums import Priority, ProposalKind, ProposalStatus, TaskStatus
from tests.fakes import FakeSignalRepository, FakeTaskRepository, FakeUnitOfWork


def make_uc() -> tuple[TriageProposalUseCase, FakeSignalRepository, FakeTaskRepository]:
    task_repo = FakeTaskRepository()
    sig_repo = FakeSignalRepository()
    uow = FakeUnitOfWork()
    sm = TaskStateMachine()
    uc = TriageProposalUseCase(
        task_repo=task_repo,
        signal_repo=sig_repo,
        uow=uow,
        state_machine=sm,
    )
    return uc, sig_repo, task_repo


class TestTriageProposal:
    """Testes da UC-4 (Triagem)."""

    @pytest.mark.asyncio
    async def test_accept_new_task_creates_task(self) -> None:
        """Aceitar proposta de NEW_TASK deve criar uma nova tarefa."""
        uc, sig_repo, task_repo = make_uc()

        prop = TaskProposal(
            id=uuid.uuid4(),
            signal_id=uuid.uuid4(),
            proposal_kind=ProposalKind.NEW_TASK,
            payload={"title": "Comprar pão", "priority": "high"},
            confidence=0.8,
            status=ProposalStatus.PENDING,
        )
        await sig_repo.save(prop)

        res = await uc.accept(AcceptProposalCommand(proposal_id=prop.id))

        assert res.action == "accepted"
        assert res.task_id is not None

        task = await task_repo.get_by_id(res.task_id)
        assert task.title == "Comprar pão"
        assert task.priority == Priority.HIGH
        assert task.status == TaskStatus.INBOX
        assert prop.status == ProposalStatus.ACCEPTED

    @pytest.mark.asyncio
    async def test_accept_with_user_edits(self) -> None:
        """Edições do usuário (RF-C.6) devem ser aplicadas e salvas na proposta."""
        uc, sig_repo, task_repo = make_uc()

        prop = TaskProposal(
            id=uuid.uuid4(),
            signal_id=uuid.uuid4(),
            proposal_kind=ProposalKind.NEW_TASK,
            payload={"title": "Comprar pão", "priority": "high"},
            confidence=0.8,
            status=ProposalStatus.PENDING,
        )
        await sig_repo.save(prop)

        res = await uc.accept(
            AcceptProposalCommand(
                proposal_id=prop.id,
                user_edits={"title": "Comprar pão francês", "priority": "low"},
            )
        )

        task = await task_repo.get_by_id(res.task_id)  # type: ignore[arg-type]
        assert task.title == "Comprar pão francês"
        assert task.priority == Priority.LOW
        assert "title" in res.updated_fields
        assert "priority" in res.updated_fields

        # Verifica se as edições foram salvas para o loop de feedback
        saved_prop = next(p for p in sig_repo._items if p.id == prop.id)
        assert saved_prop.user_edits == {"title": "Comprar pão francês", "priority": "low"}

    @pytest.mark.asyncio
    async def test_reject_proposal(self) -> None:
        """Rejeitar proposta apenas atualiza o status."""
        uc, sig_repo, _ = make_uc()

        prop = TaskProposal(
            id=uuid.uuid4(),
            signal_id=uuid.uuid4(),
            proposal_kind=ProposalKind.NEW_TASK,
            payload={"title": "Lixo"},
            confidence=0.3,
            status=ProposalStatus.PENDING,
        )
        await sig_repo.save(prop)

        res = await uc.reject(RejectProposalCommand(proposal_id=prop.id, reason="Não é tarefa"))

        assert res.action == "rejected"
        assert res.task_id is None

        saved_prop = next(p for p in sig_repo._items if p.id == prop.id)
        assert saved_prop.status == ProposalStatus.REJECTED
        assert saved_prop.rejection_reason == "Não é tarefa"
