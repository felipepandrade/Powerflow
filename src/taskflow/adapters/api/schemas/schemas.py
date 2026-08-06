import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from taskflow.domain.value_objects.enums import (
    Priority,
    ProposalKind,
    ProposalStatus,
    SourceKind,
    TaskStatus,
)

# --- Ingestion Schemas ---

class IngestSourceRequest(BaseModel):
    content: str = Field(..., description="Texto bruto a ser ingerido (ex: corpo do email, mensagem)")
    kind: SourceKind = SourceKind.EMAIL
    external_id: str | None = None
    revision_hash: str | None = None
    occurred_at: datetime | None = None
    title: str | None = None
    author_email: str | None = Field(None, description="Email do autor")
    author_name: str | None = Field(None, description="Nome do autor")
    channel: str = Field("api", description="Canal de origem (ex: api, email, calendar)")


class IngestSourceResponse(BaseModel):
    source_item_id: str
    status: str
    message: str


class PowerAutomateWebhookRequest(BaseModel):
    subject: str | None = Field(None, description="Assunto do e-mail ou título da mensagem")
    body: str | None = Field(None, description="Corpo do e-mail ou mensagem")
    sender_email: str | None = Field(None, description="E-mail do remetente")
    sender_name: str | None = Field(None, description="Nome do remetente")
    message_id: str | None = Field(None, description="ID exclusivo da mensagem")
    received_time: str | None = Field(None, description="Data/hora de recebimento (ISO 8601)")


# --- Signal Schemas ---

class CorrelateSignalResponse(BaseModel):
    signal_id: str
    action_taken: str
    message: str
    correlation_run_id: uuid.UUID
    decision_kind: str
    policy_rule_id: str
    confidence: float
    applied_task_id: uuid.UUID | None = None
    proposal_id: uuid.UUID | None = None


class TriageProposalRequest(BaseModel):
    action: str = Field(..., description="Ação escolhida: apply, discard, ou delegate")
    task_id: str | None = Field(None, description="ID da tarefa (obrigatório se action=apply)")
    modifications: dict[str, Any] | None = Field(None, description="Campos modificados manualmente pelo usuário")


class TriageProposalResponse(BaseModel):
    success: bool
    message: str


# --- Task Schemas ---

class ManageTaskRequest(BaseModel):
    status: TaskStatus | None = None
    title: str | None = Field(None, description="Novo título")
    description: str | None = Field(None, description="Nova descrição")

    due_date: date | None = None
    waiting_on_id: uuid.UUID | None = None
    priority: Priority | None = None

class ManageTaskResponse(BaseModel):
    success: bool
    message: str


class FollowUpResponse(BaseModel):
    draft_text: str
    task_id: str


# --- Read/List Schemas ---



class TaskSchema(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None = None
    status: TaskStatus
    priority: Priority
    due_date: date | None = None
    project_id: uuid.UUID | None = None
    waiting_on_id: uuid.UUID | None = None
    last_activity_at: datetime
    created_at: datetime
    updated_at: datetime
    evidence_count: int = 0
    update_count: int = 0

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

class TaskListResponse(BaseModel):
    data: list[TaskSchema]
    count: int

class TriageItemSchema(BaseModel):
    id: uuid.UUID
    signal_id: uuid.UUID
    proposal_kind: ProposalKind
    status: ProposalStatus
    payload: dict[str, Any]
    candidate_tasks: list[dict[str, Any]] | None = None
    confidence: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

class TriageListResponse(BaseModel):
    data: list[TriageItemSchema]
    count: int


# --- Org & Structure Schemas ---

class AreaSchema(BaseModel):
    id: uuid.UUID
    name: str
    short_name: str | None = None
    parent_area_id: uuid.UUID | None = None
    kind: str
    is_own_team: bool = False

    model_config = ConfigDict(from_attributes=True)


class AreaCreateRequest(BaseModel):
    name: str
    short_name: str | None = None
    parent_area_id: uuid.UUID | None = None
    kind: str = "peer_area"
    is_own_team: bool = False


class PortfolioSchema(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    owner_id: uuid.UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class PortfolioCreateRequest(BaseModel):
    name: str
    description: str | None = None
    owner_id: uuid.UUID | None = None


class StakeholderSchema(BaseModel):
    id: uuid.UUID
    email: str | None = None
    display_name: str
    job_title: str | None = None
    department: str | None = None
    area_id: uuid.UUID | None = None
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class StakeholderCreateRequest(BaseModel):
    email: str | None = None
    display_name: str
    job_title: str | None = None
    department: str | None = None
    area_id: uuid.UUID | None = None


class ProjectSchema(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    status: str
    portfolio_id: uuid.UUID | None = None
    owner_id: uuid.UUID | None = None
    area_id: uuid.UUID | None = None
    color: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ProjectCreateRequest(BaseModel):
    name: str
    description: str | None = None
    status: str = "active"
    portfolio_id: uuid.UUID | None = None
    owner_id: uuid.UUID | None = None
    area_id: uuid.UUID | None = None
    color: str | None = None


class MilestoneSchema(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    target_date: date | str
    status: str

    model_config = ConfigDict(from_attributes=True)


class MilestoneCreateRequest(BaseModel):
    project_id: uuid.UUID
    name: str
    target_date: str
    status: str = "planned"

