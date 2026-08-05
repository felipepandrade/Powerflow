import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass

class TaskORM(Base):
    __tablename__ = "tasks"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="inbox")
    priority: Mapped[str] = mapped_column(String(50), nullable=False, default="medium")
    task_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    due_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class TaskStatusHistoryORM(Base):
    __tablename__ = "task_status_histories"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id"), index=True)
    from_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    to_status: Mapped[str] = mapped_column(String(50), nullable=False)
    actor: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    signal_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    is_undone: Mapped[bool] = mapped_column(Boolean, default=False)
    undone_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class TaskUpdateORM(Base):
    __tablename__ = "task_updates"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id"), index=True)
    content: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_item_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    signal_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class TaskEvidenceORM(Base):
    __tablename__ = "task_evidences"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id"), index=True)
    source_item_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    signal_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    quote: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class TaskProposalORM(Base):
    __tablename__ = "task_proposals"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    signal_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    target_task_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    user_edits: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class SourceItemORM(Base):
    __tablename__ = "source_items"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    external_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    conversation_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    revision_hash: Mapped[str] = mapped_column(String, nullable=False)
    author_email: Mapped[str | None] = mapped_column(String, nullable=True)
    author_name: Mapped[str | None] = mapped_column(String, nullable=True)
    participants: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    body_preview: Mapped[str | None] = mapped_column(String, nullable=True)
    body_full: Mapped[str | None] = mapped_column(String, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    has_attachments: Mapped[bool] = mapped_column(Boolean, default=False)
    importance: Mapped[str | None] = mapped_column(String(50), nullable=True)
    web_link: Mapped[str | None] = mapped_column(String, nullable=True)
    is_redacted: Mapped[bool] = mapped_column(Boolean, default=False)
    processing_status: Mapped[str] = mapped_column(String(50), nullable=False)
    filtered_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    blocked_by_safety: Mapped[bool] = mapped_column(Boolean, default=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class SignalORM(Base):
    __tablename__ = "signals"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("source_items.id"), index=True)
    signal_type: Mapped[str] = mapped_column(String(50), nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False)
    extraction_conf: Mapped[float] = mapped_column(Float, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    decision_kind: Mapped[str | None] = mapped_column(String(50), nullable=True)
    decision_conf: Mapped[float | None] = mapped_column(Float, nullable=True)
    resolved_task_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class CorrelationRunORM(Base):
    __tablename__ = "correlation_runs"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    signal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("signals.id"), index=True)
    candidates: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    llm_assessments: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    final_decision: Mapped[str] = mapped_column(String(50), nullable=False)
    final_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    applied: Mapped[bool] = mapped_column(Boolean, default=False)
    routed_to_triage: Mapped[bool] = mapped_column(Boolean, default=False)
    policy_rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    skipped_llm: Mapped[bool] = mapped_column(Boolean, default=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class CredentialORM(Base):
    __tablename__ = "credentials"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
