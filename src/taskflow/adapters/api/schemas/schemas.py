from typing import Any

from pydantic import BaseModel, Field

# --- Ingestion Schemas ---

class IngestSourceRequest(BaseModel):
    content: str = Field(..., description="Texto bruto a ser ingerido (ex: corpo do email, mensagem)")
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


class TriageProposalRequest(BaseModel):
    action: str = Field(..., description="Ação escolhida: apply, discard, ou delegate")
    task_id: str | None = Field(None, description="ID da tarefa (obrigatório se action=apply)")
    modifications: dict[str, Any] | None = Field(None, description="Campos modificados manualmente pelo usuário")


class TriageProposalResponse(BaseModel):
    success: bool
    message: str


# --- Task Schemas ---

class ManageTaskRequest(BaseModel):
    status: str | None = Field(None, description="Novo status (ex: completed, blocked, cancelled)")
    title: str | None = Field(None, description="Novo título")
    description: str | None = Field(None, description="Nova descrição")


class ManageTaskResponse(BaseModel):
    success: bool
    message: str


class FollowUpResponse(BaseModel):
    draft_text: str
    task_id: str


# --- Read/List Schemas ---

import uuid


class TaskSchema(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None = None
    status: str | Any
    priority: str | Any
    due_date: str | Any | None = None
    project_id: uuid.UUID | Any | None = None
    waiting_on_id: uuid.UUID | Any | None = None
    last_activity_at: str | Any | None = None
    
    class Config:
        from_attributes = True
        use_enum_values = True

class TaskListResponse(BaseModel):
    data: list[TaskSchema]
    count: int

class TriageItemSchema(BaseModel):
    id: uuid.UUID
    source_item_id: uuid.UUID
    signal_type: str | Any
    state: str | Any
    payload: dict[str, Any]
    decision_conf: float | None = None
    created_at: str | Any | None = None
    
    class Config:
        from_attributes = True
        use_enum_values = True

class TriageListResponse(BaseModel):
    data: list[TriageItemSchema]
    count: int
