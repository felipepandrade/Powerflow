import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# ═══════════════════════════════════════════════════════════════════
#  ESTRUTURA ORGANIZACIONAL
# ═══════════════════════════════════════════════════════════════════

class AreaORM(Base):
    __tablename__ = "areas"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    parent_area_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("areas.id", ondelete="SET NULL"), nullable=True)
    kind: Mapped[str] = mapped_column(String(50), nullable=False)  # own_team|peer_area|management|external|vendor
    is_own_team: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PortfolioORM(Base):
    __tablename__ = "portfolios"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class StakeholderORM(Base):
    __tablename__ = "stakeholders"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    job_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    department: Mapped[str | None] = mapped_column(String(200), nullable=True)
    area_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("areas.id", ondelete="SET NULL"), nullable=True, index=True)
    area_source: Mapped[str | None] = mapped_column(String(50), nullable=True)  # graph|manual
    graph_user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avg_response_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProjectORM(Base):
    __tablename__ = "projects"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("portfolios.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    owner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("stakeholders.id"), nullable=True)
    area_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("areas.id"), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    color: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MilestoneORM(Base):
    __tablename__ = "milestones"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    target_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("stakeholders.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="planned", index=True)  # planned|at_risk|met|missed|cancelled
    completed_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")
    signal_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════
#  INGESTÃO & CALENDÁRIO
# ═══════════════════════════════════════════════════════════════════

class SourceItemORM(Base):
    __tablename__ = "source_items"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    external_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    conversation_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    revision_hash: Mapped[str] = mapped_column(String, nullable=False)
    author_email: Mapped[str | None] = mapped_column(String, nullable=True)
    author_name: Mapped[str | None] = mapped_column(String, nullable=True)
    participants: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    body_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_full: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    has_attachments: Mapped[bool] = mapped_column(Boolean, default=False)
    importance: Mapped[str | None] = mapped_column(String(50), nullable=True)
    web_link: Mapped[str | None] = mapped_column(String, nullable=True)
    is_redacted: Mapped[bool] = mapped_column(Boolean, default=False)
    processing_status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    filtered_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    blocked_by_safety: Mapped[bool] = mapped_column(Boolean, default=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CalendarEventORM(Base):
    __tablename__ = "calendar_events"
    source_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("source_items.id", ondelete="CASCADE"), primary_key=True)
    graph_event_id: Mapped[str] = mapped_column(String, nullable=False)
    series_master_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    instance_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    body_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_all_day: Mapped[bool] = mapped_column(Boolean, default=False)
    timezone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    is_online: Mapped[bool] = mapped_column(Boolean, default=False)
    join_url: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    linked_chat_id: Mapped[str | None] = mapped_column(String, nullable=True)
    organizer_email: Mapped[str | None] = mapped_column(String, nullable=True)
    my_response: Mapped[str | None] = mapped_column(String(50), nullable=True)
    show_as: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sensitivity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_cancelled: Mapped[bool] = mapped_column(Boolean, default=False)
    recurrence_rule: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    attendee_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    categories: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    meeting_class: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    has_agenda: Mapped[bool] = mapped_column(Boolean, default=False)
    produced_action_items: Mapped[bool] = mapped_column(Boolean, default=False)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    attributed_project_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    attributed_area_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)


class SyncStateORM(Base):
    __tablename__ = "sync_state"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[str] = mapped_column(String, nullable=False)
    delta_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    window_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    window_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    state: Mapped[str] = mapped_column(String(50), default="healthy")

    __table_args__ = (UniqueConstraint("channel", "resource_id", name="uq_sync_channel_resource"),)


class IngestionRunORM(Base):
    __tablename__ = "ingestion_runs"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    channel: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    items_seen: Mapped[int] = mapped_column(Integer, default=0)
    items_filtered: Mapped[int] = mapped_column(Integer, default=0)
    items_extracted: Mapped[int] = mapped_column(Integer, default=0)
    items_failed: Mapped[int] = mapped_column(Integer, default=0)
    success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String, nullable=True)


# ═══════════════════════════════════════════════════════════════════
#  SINAIS E CORRELAÇÃO
# ═══════════════════════════════════════════════════════════════════

class SignalORM(Base):
    __tablename__ = "signals"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("source_items.id", ondelete="CASCADE"), index=True)
    signal_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    extraction_conf: Mapped[float] = mapped_column(Float, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    evidence_quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    demand_origin: Mapped[str | None] = mapped_column(String(50), nullable=True)
    decision_kind: Mapped[str | None] = mapped_column(String(50), nullable=True)
    decision_conf: Mapped[float | None] = mapped_column(Float, nullable=True)
    resolved_task_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class CorrelationRunORM(Base):
    __tablename__ = "correlation_runs"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    signal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("signals.id", ondelete="CASCADE"), index=True)
    candidates: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    llm_assessments: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    final_decision: Mapped[str] = mapped_column(String(50), nullable=False)
    final_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    applied: Mapped[bool] = mapped_column(Boolean, default=False)
    routed_to_triage: Mapped[bool] = mapped_column(Boolean, default=False)
    policy_rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    guardrail_blocks: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    skipped_llm: Mapped[bool] = mapped_column(Boolean, default=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════
#  DOMÍNIO DE TAREFAS
# ═══════════════════════════════════════════════════════════════════

class TaskORM(Base):
    __tablename__ = "tasks"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="inbox", index=True)
    priority: Mapped[str] = mapped_column(String(50), nullable=False, default="medium")
    task_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    demand_origin: Mapped[str | None] = mapped_column(String(50), nullable=True)
    requester_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("stakeholders.id"), nullable=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    milestone_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("milestones.id", ondelete="SET NULL"), nullable=True)
    parent_task_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)
    waiting_on_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("stakeholders.id"), nullable=True, index=True)
    due_date: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    due_date_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    original_due_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    due_date_change_count: Mapped[int] = mapped_column(Integer, default=0)
    estimated_effort_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    snooze_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    auto_created: Mapped[bool] = mapped_column(Boolean, default=False)
    llm_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_interaction_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TaskEvidenceORM(Base):
    __tablename__ = "task_evidences"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    source_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("source_items.id", ondelete="CASCADE"), index=True)
    signal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("signals.id", ondelete="SET NULL"), nullable=True)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # origin|update|completion_signal|context|meeting_agenda
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TaskStatusHistoryORM(Base):
    __tablename__ = "task_status_histories"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    from_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    to_status: Mapped[str] = mapped_column(String(50), nullable=False)
    actor: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    signal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("signals.id"), nullable=True)
    is_undone: Mapped[bool] = mapped_column(Boolean, default=False)
    undone_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class TaskUpdateORM(Base):
    __tablename__ = "task_updates"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_item_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("source_items.id"), nullable=True)
    signal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("signals.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TaskStakeholderORM(Base):
    __tablename__ = "task_stakeholders"
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)
    stakeholder_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stakeholders.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(String(50), primary_key=True)  # requester|assignee|informed


class TaskMeetingLinkORM(Base):
    __tablename__ = "task_meeting_links"
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)
    source_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("source_items.id", ondelete="CASCADE"), primary_key=True)
    link_type: Mapped[str] = mapped_column(String(50), primary_key=True)  # prep_for|discussed_in|forum_for|deadline_anchor
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_user_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)


class StakeholderInteractionORM(Base):
    __tablename__ = "stakeholder_interactions"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    stakeholder_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stakeholders.id", ondelete="CASCADE"), index=True)
    task_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True, index=True)
    source_item_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("source_items.id", ondelete="SET NULL"), nullable=True)
    interaction_type: Mapped[str] = mapped_column(String(50), nullable=False)  # email_in|email_out|chat|meeting_held|nudge_sent
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════
#  TRIAGEM E FOLLOW-UP
# ═══════════════════════════════════════════════════════════════════

class TaskProposalORM(Base):
    __tablename__ = "task_proposals"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    signal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("signals.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # pending|accepted|rejected|merged|expired
    target_task_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tasks.id"), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    candidate_tasks: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    user_edits: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class FollowUpORM(Base):
    __tablename__ = "follow_ups"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    channel: Mapped[str] = mapped_column(String(50), default="email")  # email|teams|bring_to_meeting
    target_meeting_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("source_items.id"), nullable=True)
    suggested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    draft_subject: Mapped[str | None] = mapped_column(String, nullable=True)
    draft_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="suggested")  # suggested|sent|dismissed|snoozed
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# ═══════════════════════════════════════════════════════════════════
#  READ MODEL ANALÍTICO (SNAPSHOTS & METRICS)
# ═══════════════════════════════════════════════════════════════════

class DailyTaskSnapshotORM(Base):
    __tablename__ = "daily_task_snapshots"
    snapshot_date: Mapped[date] = mapped_column(Date, primary_key=True, index=True)
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    priority: Mapped[str | None] = mapped_column(String(50), nullable=True)
    task_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    demand_origin: Mapped[str | None] = mapped_column(String(50), nullable=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    portfolio_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    milestone_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    requester_area_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    waiting_on_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    waiting_on_area_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    original_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    age_days: Mapped[int] = mapped_column(Integer, nullable=False)
    days_in_status: Mapped[int] = mapped_column(Integer, nullable=False)
    cum_days_open: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cum_days_in_progress: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cum_days_waiting: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cum_days_blocked: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_overdue: Mapped[bool] = mapped_column(Boolean, default=False)
    is_at_risk: Mapped[bool] = mapped_column(Boolean, default=False)
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_today: Mapped[bool] = mapped_column(Boolean, default=False)
    created_today: Mapped[bool] = mapped_column(Boolean, default=False)
    estimated_effort_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)


class DailyProjectSnapshotORM(Base):
    __tablename__ = "daily_project_snapshots"
    snapshot_date: Mapped[date] = mapped_column(Date, primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)
    portfolio_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    tasks_total: Mapped[int | None] = mapped_column(Integer, default=0)
    tasks_open: Mapped[int | None] = mapped_column(Integer, default=0)
    tasks_in_progress: Mapped[int | None] = mapped_column(Integer, default=0)
    tasks_waiting: Mapped[int | None] = mapped_column(Integer, default=0)
    tasks_blocked: Mapped[int | None] = mapped_column(Integer, default=0)
    tasks_done: Mapped[int | None] = mapped_column(Integer, default=0)
    tasks_overdue: Mapped[int | None] = mapped_column(Integer, default=0)
    milestones_total: Mapped[int | None] = mapped_column(Integer, default=0)
    milestones_at_risk: Mapped[int | None] = mapped_column(Integer, default=0)
    milestones_missed: Mapped[int | None] = mapped_column(Integer, default=0)
    days_since_activity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    oldest_blocked_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    health_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    health_components: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class DailyCalendarSnapshotORM(Base):
    __tablename__ = "daily_calendar_snapshots"
    snapshot_date: Mapped[date] = mapped_column(Date, primary_key=True)
    total_meeting_minutes: Mapped[int | None] = mapped_column(Integer, default=0)
    meeting_count: Mapped[int | None] = mapped_column(Integer, default=0)
    recurring_count: Mapped[int | None] = mapped_column(Integer, default=0)
    external_count: Mapped[int | None] = mapped_column(Integer, default=0)
    with_agenda_count: Mapped[int | None] = mapped_column(Integer, default=0)
    produced_actions_count: Mapped[int | None] = mapped_column(Integer, default=0)
    largest_free_block_min: Mapped[int | None] = mapped_column(Integer, default=0)
    free_blocks_ge_90min: Mapped[int | None] = mapped_column(Integer, default=0)
    available_minutes: Mapped[int | None] = mapped_column(Integer, default=0)
    utilization_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    declined_count: Mapped[int | None] = mapped_column(Integer, default=0)
    minutes_by_class: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    minutes_by_project: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class MetricDefinitionORM(Base):
    __tablename__ = "metric_definitions"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    perspective: Mapped[str] = mapped_column(String(50), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    formula: Mapped[str] = mapped_column(Text, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    direction: Mapped[str | None] = mapped_column(String(50), nullable=True)  # higher_is_better|lower_is_better|neutral
    grain: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    dimensions: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    limitations: Mapped[str] = mapped_column(Text, nullable=False)
    coverage_basis: Mapped[str | None] = mapped_column(String(200), nullable=True)
    expected_action: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str] = mapped_column(String(100), nullable=False)
    data_origin: Mapped[str] = mapped_column(String(50), nullable=False)  # derived|manual|imported|mixed
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MetricValueORM(Base):
    __tablename__ = "metric_values"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    metric_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    metric_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    grain: Mapped[str] = mapped_column(String(20), nullable=False)  # day|week|month|quarter
    period_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    dimension_key: Mapped[str] = mapped_column(String(200), nullable=False, default="_total")
    dimension_value: Mapped[str | None] = mapped_column(String(200), nullable=True)
    value: Mapped[float | None] = mapped_column(Numeric(14, 4), nullable=True)
    numerator: Mapped[float | None] = mapped_column(Numeric(14, 4), nullable=True)
    denominator: Mapped[float | None] = mapped_column(Numeric(14, 4), nullable=True)
    sample_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    coverage_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    coverage_level: Mapped[str | None] = mapped_column(String(20), nullable=True)  # high|medium|low
    is_suppressed: Mapped[bool] = mapped_column(Boolean, default=False)
    suppression_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "metric_id", "metric_version", "grain", "period_start", "dimension_key",
            name="uq_metric_lookup"
        ),
    )


class MetricRunORM(Base):
    __tablename__ = "metric_runs"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    metrics_count: Mapped[int | None] = mapped_column(Integer, default=0)
    values_written: Mapped[int | None] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String, nullable=True)


class ManualMetricEntryORM(Base):
    __tablename__ = "manual_metric_entries"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    metric_id: Mapped[str] = mapped_column(String(100), nullable=False)
    grain: Mapped[str] = mapped_column(String(20), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    dimension_key: Mapped[str] = mapped_column(String(200), default="_total")
    value: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    declared_source: Mapped[str] = mapped_column(String(200), nullable=False)
    entered_by: Mapped[str] = mapped_column(String(100), nullable=False)
    import_batch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("manual_metric_entries.id"), nullable=True)


class MetricTargetORM(Base):
    __tablename__ = "metric_targets"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    metric_id: Mapped[str] = mapped_column(String(100), nullable=False)
    grain: Mapped[str] = mapped_column(String(20), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    target_value: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    origin: Mapped[str] = mapped_column(String(50), nullable=False)  # self|management|contractual
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ContextAnnotationORM(Base):
    __tablename__ = "context_annotations"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    occurred_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    ends_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    scope: Mapped[str] = mapped_column(String(50), default="global")
    scope_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════
#  DASHBOARDS, ALERTAS, INSIGHTS E DECISÕES
# ═══════════════════════════════════════════════════════════════════

class DashboardORM(Base):
    __tablename__ = "dashboards"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    perspective: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    default_filters: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DashboardWidgetORM(Base):
    __tablename__ = "dashboard_widgets"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    dashboard_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("dashboards.id", ondelete="CASCADE"), index=True)
    metric_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    metric_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    widget_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    grain: Mapped[str | None] = mapped_column(String(20), nullable=True)
    dimension: Mapped[str | None] = mapped_column(String(100), nullable=True)
    comparison: Mapped[str | None] = mapped_column(String(50), nullable=True)
    grid_x: Mapped[int] = mapped_column(Integer, nullable=False)
    grid_y: Mapped[int] = mapped_column(Integer, nullable=False)
    grid_w: Mapped[int] = mapped_column(Integer, nullable=False)
    grid_h: Mapped[int] = mapped_column(Integer, nullable=False)
    config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SavedViewORM(Base):
    __tablename__ = "saved_views"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    dashboard_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("dashboards.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    filters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AlertRuleORM(Base):
    __tablename__ = "alert_rules"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    rule_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(50), nullable=False)  # threshold|anomaly|staleness|milestone
    metric_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dimension_key: Mapped[str | None] = mapped_column(String(200), nullable=True)
    grain: Mapped[str | None] = mapped_column(String(20), nullable=True)
    operator: Mapped[str | None] = mapped_column(String(10), nullable=True)
    threshold_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    persistence_periods: Mapped[int] = mapped_column(Integer, default=1)
    anomaly_sigma: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_periods: Mapped[int] = mapped_column(Integer, default=8)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)  # info|medium|high|critical
    channels: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    explanation_template: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    fired_count: Mapped[int] = mapped_column(Integer, default=0)
    actioned_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AlertORM(Base):
    __tablename__ = "alerts"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    rule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("alert_rules.id", ondelete="CASCADE"), index=True)
    metric_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dimension_key: Mapped[str | None] = mapped_column(String(200), nullable=True)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    triggered_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    deviation: Mapped[float | None] = mapped_column(Float, nullable=True)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="open", index=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    dismissed_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner: Mapped[str | None] = mapped_column(String(100), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    decision_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    drill_down_query: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class InsightORM(Base):
    __tablename__ = "insights"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    scope: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    filters: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    headline: Mapped[str | None] = mapped_column(String(300), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    findings: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    suggested_actions: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    data_caveats: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    numeric_guard_passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    guard_failures: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    is_suppressed: Mapped[bool] = mapped_column(Boolean, default=False)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DecisionLogORM(Base):
    __tablename__ = "decision_log"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    context: Mapped[str] = mapped_column(Text, nullable=False)
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner: Mapped[str | None] = mapped_column(String(100), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expected_outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    metric_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    metric_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    alert_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("alerts.id", ondelete="SET NULL"), nullable=True)
    insight_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("insights.id", ondelete="SET NULL"), nullable=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    created_task_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    review_due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    review_status: Mapped[str] = mapped_column(String(50), default="pending", index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    outcome_assessment: Mapped[str | None] = mapped_column(String(50), nullable=True)
    outcome_metric_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    outcome_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════
#  RELATÓRIOS & EXPORTAÇÃO
# ═══════════════════════════════════════════════════════════════════

class ReportTemplateORM(Base):
    __tablename__ = "report_templates"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    scope: Mapped[str] = mapped_column(String(50), nullable=False)
    sections: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    include_insight: Mapped[bool] = mapped_column(Boolean, default=True)
    formats: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    schedule_cron: Mapped[str | None] = mapped_column(String(100), nullable=True)
    recipients: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ReportRunORM(Base):
    __tablename__ = "report_runs"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("report_templates.id", ondelete="SET NULL"), nullable=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    filters: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    insight_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("insights.id"), nullable=True)
    coverage_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    artifacts: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    generated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    exported_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ExportRunORM(Base):
    __tablename__ = "export_runs"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    export_type: Mapped[str] = mapped_column(String(50), nullable=False)
    dataset_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    filters: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requested_by: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CredentialORM(Base):
    __tablename__ = "credentials"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
