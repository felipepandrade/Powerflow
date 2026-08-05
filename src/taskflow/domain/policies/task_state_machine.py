"""Máquina de estados de tarefas — RF-D.1.

Transições validadas por tabela estática e determinística.
Transição inválida levanta ``InvalidTransitionError``.
"""

from __future__ import annotations

from taskflow.domain.value_objects.enums import TaskStatus

# Tabela de transições permitidas: {from_status: {to_status, ...}}
VALID_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.INBOX: frozenset({
        TaskStatus.OPEN,
        TaskStatus.CANCELLED,
    }),
    TaskStatus.OPEN: frozenset({
        TaskStatus.IN_PROGRESS,
        TaskStatus.WAITING_ON_OTHERS,
        TaskStatus.BLOCKED,
        TaskStatus.DONE,
        TaskStatus.CANCELLED,
    }),
    TaskStatus.IN_PROGRESS: frozenset({
        TaskStatus.WAITING_ON_OTHERS,
        TaskStatus.BLOCKED,
        TaskStatus.DONE,
        TaskStatus.CANCELLED,
        TaskStatus.OPEN,
    }),
    TaskStatus.WAITING_ON_OTHERS: frozenset({
        TaskStatus.IN_PROGRESS,
        TaskStatus.BLOCKED,
        TaskStatus.DONE,
        TaskStatus.CANCELLED,
        TaskStatus.OPEN,
    }),
    TaskStatus.BLOCKED: frozenset({
        TaskStatus.IN_PROGRESS,
        TaskStatus.WAITING_ON_OTHERS,
        TaskStatus.DONE,
        TaskStatus.CANCELLED,
        TaskStatus.OPEN,
    }),
    TaskStatus.DONE: frozenset({
        TaskStatus.OPEN,    # Reabertura via undo
    }),
    TaskStatus.CANCELLED: frozenset({
        TaskStatus.OPEN,    # Reabertura via undo
    }),
}


class InvalidTransitionError(Exception):
    """Levantada quando se tenta uma transição inválida de estado."""

    def __init__(self, from_status: TaskStatus, to_status: TaskStatus) -> None:
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(
            f"Transição inválida: {from_status.value!r} → {to_status.value!r}"
        )


class TaskStateMachine:
    """Validador de transições de estado de tarefas — RF-D.1.

    Implementação determinística, testável sem qualquer I/O.
    """

    def validate(self, from_status: TaskStatus, to_status: TaskStatus) -> None:
        """Valida se a transição ``from_status`` → ``to_status`` é permitida.

        Raises:
            InvalidTransitionError: Se a transição não é permitida.
        """
        allowed = VALID_TRANSITIONS.get(from_status, frozenset())
        if to_status not in allowed:
            raise InvalidTransitionError(from_status, to_status)

    def is_valid(self, from_status: TaskStatus, to_status: TaskStatus) -> bool:
        """Retorna True se a transição é permitida, False caso contrário."""
        allowed = VALID_TRANSITIONS.get(from_status, frozenset())
        return to_status in allowed

    def allowed_transitions(self, from_status: TaskStatus) -> frozenset[TaskStatus]:
        """Retorna o conjunto de transições permitidas a partir de ``from_status``."""
        return VALID_TRANSITIONS.get(from_status, frozenset())
