"""DTOs de entrada e saída da camada de aplicação."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from taskflow.domain.value_objects.enums import (
    DecisionKind,
    FollowUpChannel,
    Priority,
    ProposalKind,
    SourceKind,
    TaskStatus,
)

# ─── Ingestão ────────────────────────────────────────────────────────────────


@dataclass
class IngestSourceItemCommand:
    """Comando para ingerir um item de origem (e-mail, chat ou evento)."""

    kind: SourceKind
    channel: str
    external_id: str
    occurred_at: datetime
    revision_hash: str
    conversation_id: str | None = None
    title: str | None = None
    body_preview: str | None = None
    body_full: str | None = None
    author_email: str | None = None
    author_name: str | None = None
    participants: list[dict[str, Any]] = field(default_factory=list)
    has_attachments: bool = False
    importance: str | None = None
    web_link: str | None = None
    # Campos específicos de CalendarEvent
    calendar_starts_at: datetime | None = None
    calendar_ends_at: datetime | None = None
    calendar_sensitivity: str | None = None
    calendar_show_as: str | None = None
    calendar_series_master_id: str | None = None
    calendar_organizer_email: str | None = None
    calendar_is_all_day: bool = False
    calendar_is_online: bool = False
    calendar_join_url: str | None = None
    calendar_linked_chat_id: str | None = None
    calendar_my_response: str | None = None
    calendar_is_cancelled: bool = False
    calendar_attendee_count: int | None = None


@dataclass
class IngestSourceItemResult:
    """Resultado da ingestão de um item de origem."""

    source_item_id: uuid.UUID
    was_deduplicated: bool
    was_filtered: bool
    filtered_reason: str | None
    signal_id: uuid.UUID | None
    was_enqueued_for_correlation: bool


# ─── Correlação ──────────────────────────────────────────────────────────────


@dataclass
class CorrelateSignalCommand:
    """Comando para correlacionar um sinal pendente."""

    signal_id: uuid.UUID
    force_triage: bool = False   # Override da política → sempre triage


@dataclass
class CorrelationRunResult:
    """Resultado da execução de correlação de um sinal."""

    signal_id: uuid.UUID
    correlation_run_id: uuid.UUID
    decision_kind: DecisionKind
    policy_rule_id: str
    action: str          # "apply" | "triage" | "discard"
    confidence: float
    applied_task_id: uuid.UUID | None
    proposal_id: uuid.UUID | None
    latency_ms: int


# ─── Triagem ─────────────────────────────────────────────────────────────────


@dataclass
class AcceptProposalCommand:
    """Comando para aceitar uma proposta de triagem (com ou sem edições)."""

    proposal_id: uuid.UUID
    user_edits: dict[str, Any] | None = None  # Edições do usuário (feedback RF-C.6)


@dataclass
class RejectProposalCommand:
    """Comando para rejeitar uma proposta de triagem."""

    proposal_id: uuid.UUID
    reason: str | None = None


@dataclass
class TriageResult:
    """Resultado de uma ação de triagem."""

    proposal_id: uuid.UUID
    task_id: uuid.UUID | None
    action: str                # "accepted" | "rejected" | "merged"
    updated_fields: list[str]  # Campos que foram atualizados


# ─── Tarefas ─────────────────────────────────────────────────────────────────


@dataclass
class CreateTaskCommand:
    """Comando para criar uma tarefa manualmente."""

    title: str
    description: str | None = None
    priority: Priority = Priority.MEDIUM
    due_date: date | None = None
    project_id: uuid.UUID | None = None
    parent_task_id: uuid.UUID | None = None


@dataclass
class UpdateTaskCommand:
    """Comando para atualizar uma tarefa manualmente."""

    task_id: uuid.UUID
    title: str | None = None
    description: str | None = None
    priority: Priority | None = None
    due_date: date | None = None
    project_id: uuid.UUID | None = None
    waiting_on_id: uuid.UUID | None = None
    snooze_until: datetime | None = None


@dataclass
class TransitionTaskCommand:
    """Comando para transicionar o estado de uma tarefa."""

    task_id: uuid.UUID
    to_status: TaskStatus
    reason: str | None = None
    signal_id: uuid.UUID | None = None


@dataclass
class UndoLastTransitionCommand:
    """Comando para reverter a última transição de estado — RF-D.3."""

    task_id: uuid.UUID


@dataclass
class TaskView:
    """DTO de leitura de uma tarefa."""

    id: uuid.UUID
    title: str
    description: str | None
    status: TaskStatus
    priority: Priority
    due_date: date | None
    project_id: uuid.UUID | None
    waiting_on_id: uuid.UUID | None
    last_activity_at: datetime
    created_at: datetime
    updated_at: datetime
    evidence_count: int = 0
    update_count: int = 0


# ─── Estagnação / Follow-up ──────────────────────────────────────────────────


@dataclass
class ScanStaleItemsCommand:
    """Comando para varrer tarefas estagnadas — RF-E.1."""

    dry_run: bool = False  # Se True, apenas reporta sem criar follow-ups


@dataclass
class StaleTaskReport:
    """Relatório de uma tarefa estagnada detectada."""

    task_id: uuid.UUID
    task_title: str
    stale_reason: str
    recommended_channel: FollowUpChannel | None
    follow_up_id: uuid.UUID | None        # Criado se dry_run=False
    suggest_bring_to_meeting: bool = False
    meeting_source_id: str | None = None


@dataclass
class ScanStaleItemsResult:
    """Resultado da varredura de estagnação."""

    total_scanned: int
    stale_count: int
    follow_ups_created: int
    reports: list[StaleTaskReport]


@dataclass
class SuggestFollowUpCommand:
    """Comando para gerar um rascunho de nudge — RF-E.2."""

    task_id: uuid.UUID
    channel: FollowUpChannel
    tone: str = "professional"   # professional | friendly | formal


@dataclass
class FollowUpDraft:
    """Rascunho de mensagem de follow-up."""

    task_id: uuid.UUID
    channel: FollowUpChannel
    subject: str | None
    body: str
    tone: str


# ─── Propostas de Tarefa ─────────────────────────────────────────────────────


@dataclass
class ProposalView:
    """DTO de leitura de uma proposta de triagem pendente."""

    id: uuid.UUID
    signal_id: uuid.UUID
    proposal_kind: ProposalKind
    payload: dict[str, Any]
    confidence: float
    candidate_tasks: list[Any] | None
    created_at: datetime
