"""Entidades do domínio TaskFlow — Task, Project, Stakeholder."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from taskflow.domain.value_objects.enums import (
    ActorType,
    EvidenceRole,
    FollowUpChannel,
    FollowUpStatus,
    InteractionType,
    Priority,
    ProposalKind,
    ProposalStatus,
    StakeholderRole,
    TaskStatus,
    TaskType,
)


@dataclass
class Stakeholder:
    """Representa uma pessoa que interage com o usuário nas tarefas."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    email: str | None = None
    display_name: str = ""
    job_title: str | None = None
    department: str | None = None
    graph_user_id: str | None = None
    avg_response_hours: float | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if not self.display_name and not self.email:
            raise ValueError("Stakeholder deve ter ao menos email ou display_name.")


@dataclass
class TaskEvidence:
    """Evidência que vincula uma tarefa ao seu item de origem."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    task_id: uuid.UUID = field(default_factory=uuid.uuid4)
    source_item_id: uuid.UUID = field(default_factory=uuid.uuid4)
    signal_id: uuid.UUID | None = None
    quote: str = ""
    role: EvidenceRole = EvidenceRole.ORIGIN
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if not self.quote:
            raise ValueError("TaskEvidence.quote não pode ser vazio.")


@dataclass
class TaskStatusHistory:
    """Registro imutável de mudança de estado — RF-D.2."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    task_id: uuid.UUID = field(default_factory=uuid.uuid4)
    from_status: TaskStatus | None = None
    to_status: TaskStatus = TaskStatus.INBOX
    actor: ActorType = ActorType.USER
    reason: str | None = None
    signal_id: uuid.UUID | None = None
    is_undone: bool = False
    undone_at: datetime | None = None
    snapshot: dict[str, Any] | None = None  # Estado anterior completo para undo
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TaskUpdate:
    """Nota de progresso adicionada à tarefa."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    task_id: uuid.UUID = field(default_factory=uuid.uuid4)
    content: str = ""
    source: str = "manual"  # manual | extracted
    source_item_id: uuid.UUID | None = None
    signal_id: uuid.UUID | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Task:
    """Entidade central de tarefa — representa um compromisso acionável."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    title: str = ""
    description: str | None = None
    status: TaskStatus = TaskStatus.INBOX
    priority: Priority = Priority.MEDIUM
    task_type: TaskType | None = None
    project_id: uuid.UUID | None = None
    parent_task_id: uuid.UUID | None = None
    waiting_on_id: uuid.UUID | None = None
    due_date: date | None = None
    due_date_source: str = "manual"  # explicit | inferred | manual
    estimated_effort_minutes: int | None = None
    snooze_until: datetime | None = None
    auto_created: bool = False
    llm_confidence: float | None = None
    last_activity_at: datetime = field(default_factory=datetime.utcnow)
    last_interaction_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # Coleções em memória (carregadas pela camada de aplicação)
    evidence: list[TaskEvidence] = field(default_factory=list)
    status_history: list[TaskStatusHistory] = field(default_factory=list)
    updates: list[TaskUpdate] = field(default_factory=list)
    stakeholders: list[tuple[Stakeholder, StakeholderRole]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.title:
            raise ValueError("Task.title não pode ser vazio.")

    def snapshot_dict(self) -> dict[str, Any]:
        """Retorna snapshot do estado atual para suporte a undo — RF-D.3."""
        return {
            "status": self.status.value,
            "priority": self.priority.value,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "waiting_on_id": str(self.waiting_on_id) if self.waiting_on_id else None,
            "description": self.description,
        }


@dataclass
class Project:
    """Agregador de tarefas relacionadas — RF-D.4."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = ""
    description: str | None = None
    status: str = "active"  # active | on_hold | completed | cancelled
    target_date: date | None = None
    color: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Project.name não pode ser vazio.")


@dataclass
class FollowUp:
    """Sugestão de follow-up para tarefas aguardando terceiros — RF-E.1."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    task_id: uuid.UUID = field(default_factory=uuid.uuid4)
    rule_id: str = ""
    channel: FollowUpChannel = FollowUpChannel.EMAIL
    target_meeting_id: uuid.UUID | None = None
    suggested_at: datetime = field(default_factory=datetime.utcnow)
    draft_subject: str | None = None
    draft_body: str | None = None
    status: FollowUpStatus = FollowUpStatus.SUGGESTED
    sent_at: datetime | None = None


@dataclass
class StakeholderInteraction:
    """Touchpoint registrado no ledger de interações — RF-G.11."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    stakeholder_id: uuid.UUID = field(default_factory=uuid.uuid4)
    task_id: uuid.UUID | None = None
    source_item_id: uuid.UUID | None = None
    interaction_type: InteractionType = InteractionType.EMAIL_IN
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TaskProposal:
    """Proposta de triagem — aceite, rejeição ou ambiguidade — RF-D.6."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    signal_id: uuid.UUID = field(default_factory=uuid.uuid4)
    proposal_kind: ProposalKind = ProposalKind.NEW_TASK
    payload: dict[str, Any] = field(default_factory=dict[str, Any])
    candidate_tasks: list[Any] | None = None
    confidence: float = 0.0
    status: ProposalStatus = ProposalStatus.PENDING
    resolved_task_id: uuid.UUID | None = None
    rejection_reason: str | None = None
    user_edits: dict[str, Any] | None = None  # Feedback loop — RF-C.6
    created_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: datetime | None = None
