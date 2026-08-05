"""Testes unitários para TaskStateMachine — RF-D.1.

Cobre a matriz completa de transições válidas e inválidas.
Zero I/O — 100% em memória.
"""

import pytest

from taskflow.domain.policies.task_state_machine import (
    InvalidTransitionError,
    TaskStateMachine,
)
from taskflow.domain.value_objects.enums import TaskStatus

machine = TaskStateMachine()


class TestValidTransitions:
    """Verifica todas as transições PERMITIDAS da máquina de estados."""

    @pytest.mark.parametrize("to_status", [TaskStatus.OPEN, TaskStatus.CANCELLED])
    def test_from_inbox(self, to_status: TaskStatus) -> None:
        machine.validate(TaskStatus.INBOX, to_status)

    @pytest.mark.parametrize("to_status", [
        TaskStatus.IN_PROGRESS, TaskStatus.WAITING_ON_OTHERS,
        TaskStatus.BLOCKED, TaskStatus.DONE, TaskStatus.CANCELLED,
    ])
    def test_from_open(self, to_status: TaskStatus) -> None:
        machine.validate(TaskStatus.OPEN, to_status)

    @pytest.mark.parametrize("to_status", [
        TaskStatus.WAITING_ON_OTHERS, TaskStatus.BLOCKED,
        TaskStatus.DONE, TaskStatus.CANCELLED, TaskStatus.OPEN,
    ])
    def test_from_in_progress(self, to_status: TaskStatus) -> None:
        machine.validate(TaskStatus.IN_PROGRESS, to_status)

    @pytest.mark.parametrize("to_status", [
        TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED,
        TaskStatus.DONE, TaskStatus.CANCELLED, TaskStatus.OPEN,
    ])
    def test_from_waiting_on_others(self, to_status: TaskStatus) -> None:
        machine.validate(TaskStatus.WAITING_ON_OTHERS, to_status)

    @pytest.mark.parametrize("to_status", [
        TaskStatus.IN_PROGRESS, TaskStatus.WAITING_ON_OTHERS,
        TaskStatus.DONE, TaskStatus.CANCELLED, TaskStatus.OPEN,
    ])
    def test_from_blocked(self, to_status: TaskStatus) -> None:
        machine.validate(TaskStatus.BLOCKED, to_status)

    def test_from_done_to_open_reopen(self) -> None:
        """Reabertura via undo."""
        machine.validate(TaskStatus.DONE, TaskStatus.OPEN)

    def test_from_cancelled_to_open_reopen(self) -> None:
        """Reabertura via undo."""
        machine.validate(TaskStatus.CANCELLED, TaskStatus.OPEN)


class TestInvalidTransitions:
    """Verifica que transições inválidas levantam InvalidTransitionError."""

    def test_inbox_to_in_progress(self) -> None:
        with pytest.raises(InvalidTransitionError):
            machine.validate(TaskStatus.INBOX, TaskStatus.IN_PROGRESS)

    def test_inbox_to_done(self) -> None:
        with pytest.raises(InvalidTransitionError):
            machine.validate(TaskStatus.INBOX, TaskStatus.DONE)

    def test_done_to_done(self) -> None:
        with pytest.raises(InvalidTransitionError):
            machine.validate(TaskStatus.DONE, TaskStatus.DONE)

    def test_done_to_in_progress(self) -> None:
        with pytest.raises(InvalidTransitionError):
            machine.validate(TaskStatus.DONE, TaskStatus.IN_PROGRESS)

    def test_cancelled_to_done(self) -> None:
        with pytest.raises(InvalidTransitionError):
            machine.validate(TaskStatus.CANCELLED, TaskStatus.DONE)

    def test_cancelled_to_in_progress(self) -> None:
        with pytest.raises(InvalidTransitionError):
            machine.validate(TaskStatus.CANCELLED, TaskStatus.IN_PROGRESS)

    def test_invalid_transition_error_message(self) -> None:
        err = InvalidTransitionError(TaskStatus.INBOX, TaskStatus.IN_PROGRESS)
        assert "inbox" in str(err).lower()
        assert "in_progress" in str(err).lower()


class TestIsValid:
    """Verifica o método is_valid() sem levantar exceção."""

    def test_valid_returns_true(self) -> None:
        assert machine.is_valid(TaskStatus.OPEN, TaskStatus.IN_PROGRESS) is True

    def test_invalid_returns_false(self) -> None:
        assert machine.is_valid(TaskStatus.DONE, TaskStatus.BLOCKED) is False

    def test_self_transition_invalid(self) -> None:
        assert machine.is_valid(TaskStatus.OPEN, TaskStatus.OPEN) is False


class TestAllowedTransitions:
    """Verifica o método allowed_transitions()."""

    def test_inbox_transitions(self) -> None:
        allowed = machine.allowed_transitions(TaskStatus.INBOX)
        assert TaskStatus.OPEN in allowed
        assert TaskStatus.CANCELLED in allowed
        assert TaskStatus.IN_PROGRESS not in allowed

    def test_done_transitions(self) -> None:
        allowed = machine.allowed_transitions(TaskStatus.DONE)
        assert TaskStatus.OPEN in allowed
        assert len(allowed) == 1
