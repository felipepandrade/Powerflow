"""Testes de integração para ManageTaskUseCase — UC-3.

100% em memória via Fakes. Zero I/O.
"""

import uuid
from datetime import date

import pytest

from taskflow.application.dto.commands import (
    CreateTaskCommand,
    TransitionTaskCommand,
    UndoLastTransitionCommand,
    UpdateTaskCommand,
)
from taskflow.application.use_cases.manage_task import ManageTaskUseCase
from taskflow.domain.policies.task_state_machine import InvalidTransitionError
from taskflow.domain.value_objects.enums import TaskStatus
from tests.fakes import FakeTaskRepository, FakeUnitOfWork


def make_uc() -> tuple[ManageTaskUseCase, FakeTaskRepository, FakeUnitOfWork]:
    repo = FakeTaskRepository()
    uow = FakeUnitOfWork()
    uc = ManageTaskUseCase(task_repo=repo, uow=uow)
    return uc, repo, uow


class TestCreateTask:
    """Testes de criação de tarefa."""

    @pytest.mark.asyncio
    async def test_creates_task_in_inbox(self) -> None:
        uc, repo, _ = make_uc()
        cmd = CreateTaskCommand(title="Enviar relatório")
        view = await uc.create(cmd)

        assert view.status == TaskStatus.INBOX
        assert view.title == "Enviar relatório"
        assert repo._tasks[view.id] is not None

    @pytest.mark.asyncio
    async def test_initial_history_recorded(self) -> None:
        uc, repo, _ = make_uc()
        cmd = CreateTaskCommand(title="Revisar proposta")
        view = await uc.create(cmd)

        task = repo._tasks[view.id]
        assert len(task.status_history) == 1
        assert task.status_history[0].to_status == TaskStatus.INBOX
        assert task.status_history[0].from_status is None

    @pytest.mark.asyncio
    async def test_empty_title_raises(self) -> None:
        uc, _, _ = make_uc()
        with pytest.raises(ValueError):
            await uc.create(CreateTaskCommand(title=""))

    @pytest.mark.asyncio
    async def test_creates_with_due_date(self) -> None:
        uc, repo, _ = make_uc()
        due = date(2026, 9, 30)
        view = await uc.create(CreateTaskCommand(title="Reunião trimestral", due_date=due))
        assert repo._tasks[view.id].due_date == due


class TestUpdateTask:
    """Testes de atualização de tarefa."""

    @pytest.mark.asyncio
    async def test_updates_title(self) -> None:
        uc, _repo, _ = make_uc()
        view = await uc.create(CreateTaskCommand(title="Antigo título"))
        updated = await uc.update(UpdateTaskCommand(task_id=view.id, title="Novo título"))
        assert updated.title == "Novo título"

    @pytest.mark.asyncio
    async def test_update_nonexistent_raises(self) -> None:
        uc, _, _ = make_uc()
        with pytest.raises(ValueError, match="não encontrada"):
            await uc.update(UpdateTaskCommand(task_id=uuid.uuid4()))


class TestTransitionTask:
    """Testes de transição de estado."""

    @pytest.mark.asyncio
    async def test_valid_transition_inbox_to_open(self) -> None:
        uc, _repo, _ = make_uc()
        view = await uc.create(CreateTaskCommand(title="Estudar"))
        transitioned = await uc.transition(
            TransitionTaskCommand(task_id=view.id, to_status=TaskStatus.OPEN)
        )
        assert transitioned.status == TaskStatus.OPEN

    @pytest.mark.asyncio
    async def test_transition_records_history(self) -> None:
        uc, repo, _ = make_uc()
        view = await uc.create(CreateTaskCommand(title="Estudar"))
        await uc.transition(TransitionTaskCommand(task_id=view.id, to_status=TaskStatus.OPEN))
        task = repo._tasks[view.id]
        # 1 registro inicial (inbox) + 1 transição
        assert len(task.status_history) == 2
        assert task.status_history[1].to_status == TaskStatus.OPEN

    @pytest.mark.asyncio
    async def test_invalid_transition_raises(self) -> None:
        uc, _, _ = make_uc()
        view = await uc.create(CreateTaskCommand(title="X"))
        with pytest.raises(InvalidTransitionError):
            await uc.transition(
                TransitionTaskCommand(task_id=view.id, to_status=TaskStatus.IN_PROGRESS)
            )

    @pytest.mark.asyncio
    async def test_done_sets_completed_at(self) -> None:
        uc, repo, _ = make_uc()
        view = await uc.create(CreateTaskCommand(title="Finalizar"))
        await uc.transition(TransitionTaskCommand(task_id=view.id, to_status=TaskStatus.OPEN))
        await uc.transition(TransitionTaskCommand(task_id=view.id, to_status=TaskStatus.DONE))
        task = repo._tasks[view.id]
        assert task.completed_at is not None


class TestUndoTransition:
    """Testes de reversão de transição — RF-D.3."""

    @pytest.mark.asyncio
    async def test_undo_restores_previous_status(self) -> None:
        uc, _repo, _ = make_uc()
        view = await uc.create(CreateTaskCommand(title="Reverter"))
        await uc.transition(TransitionTaskCommand(task_id=view.id, to_status=TaskStatus.OPEN))
        await uc.transition(TransitionTaskCommand(task_id=view.id, to_status=TaskStatus.IN_PROGRESS))

        undone = await uc.undo_last_transition(UndoLastTransitionCommand(task_id=view.id))
        assert undone.status == TaskStatus.OPEN

    @pytest.mark.asyncio
    async def test_undo_marks_history_as_undone(self) -> None:
        uc, repo, _ = make_uc()
        view = await uc.create(CreateTaskCommand(title="X"))
        await uc.transition(TransitionTaskCommand(task_id=view.id, to_status=TaskStatus.OPEN))
        await uc.undo_last_transition(UndoLastTransitionCommand(task_id=view.id))
        task = repo._tasks[view.id]
        undone_records = [h for h in task.status_history if h.is_undone]
        assert len(undone_records) >= 1

    @pytest.mark.asyncio
    async def test_undo_with_no_history_raises(self) -> None:
        uc, _, _ = make_uc()
        view = await uc.create(CreateTaskCommand(title="Vazio"))
        with pytest.raises(ValueError):
            await uc.undo_last_transition(UndoLastTransitionCommand(task_id=view.id))
