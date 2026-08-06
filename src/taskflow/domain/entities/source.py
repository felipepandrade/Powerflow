"""Entidades de ingestão: SourceItem, CalendarEvent, Signal, CorrelationRun."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from taskflow.domain.value_objects.enums import (
    CalendarSensitivity,
    DecisionKind,
    ProcessingStatus,
    SignalState,
    SignalType,
    SourceKind,
)


@dataclass
class SourceItem:
    """Unidade canônica de ingestão — e-mail, chat ou evento de calendário.

    Abstração única sobre todos os canais com discriminador ``kind``.
    Toda evidência aponta para source_items, independentemente do canal.
    """

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    kind: SourceKind = SourceKind.EMAIL
    channel: str = ""
    external_id: str = ""
    conversation_id: str | None = None  # threadId | chatId | seriesMasterId
    revision_hash: str = ""
    author_email: str | None = None
    author_name: str | None = None
    participants: list[dict[str, Any]] = field(default_factory=list[dict[str, Any]])
    title: str | None = None
    body_preview: str | None = None  # Sempre os primeiros 500 chars
    body_full: str | None = None  # Só se STORE_FULL_BODY=true
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    has_attachments: bool = False
    importance: str | None = None
    web_link: str | None = None
    is_redacted: bool = False  # True para eventos privados
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    filtered_reason: str | None = None
    blocked_by_safety: bool = False
    processed_at: datetime | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def get_content_for_llm(self) -> str:
        """Retorna o conteúdo adequado para envio ao LLM.

        Nunca retorna corpo de eventos redatados (private/confidential).
        """
        if self.is_redacted:
            return ""
        return self.body_full or self.body_preview or ""


@dataclass
class CalendarEvent:
    """Dados específicos de evento de calendário (1:1 com SourceItem)."""

    source_item_id: uuid.UUID = field(default_factory=uuid.uuid4)
    graph_event_id: str = ""
    series_master_id: str | None = None
    instance_type: str | None = None  # singleInstance | occurrence | exception
    body_hash: str | None = None  # Para dedup de instâncias de série
    starts_at: datetime = field(default_factory=datetime.utcnow)
    ends_at: datetime = field(default_factory=datetime.utcnow)
    is_all_day: bool = False
    timezone: str | None = None
    location: str | None = None
    is_online: bool = False
    join_url: str | None = None
    linked_chat_id: str | None = None  # Correlação com Teams
    organizer_email: str | None = None
    my_response: str | None = None  # accepted | tentative | declined | none
    show_as: str | None = None  # free | busy | oof | workingElsewhere
    sensitivity: CalendarSensitivity = CalendarSensitivity.NORMAL
    is_cancelled: bool = False
    recurrence_rule: dict[str, Any] | None = None
    attendee_count: int | None = None
    categories: list[str] = field(default_factory=list[str])

    @property
    def is_private(self) -> bool:
        """Retorna True se o evento é privado ou confidencial — RF-F.3."""
        return self.sensitivity in (
            CalendarSensitivity.PRIVATE,
            CalendarSensitivity.CONFIDENTIAL,
        )

    @property
    def duration_minutes(self) -> float:
        """Retorna a duração do evento em minutos."""
        delta = self.ends_at - self.starts_at
        return delta.total_seconds() / 60


@dataclass
class Signal:
    """Fato extraído de um SourceItem, ainda não correlacionado.

    Um Signal é uma afirmação candidata — ainda não resolvida contra o
    estado atual das tarefas. Mediador entre extração e correlação.
    """

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    source_item_id: uuid.UUID = field(default_factory=uuid.uuid4)
    signal_type: SignalType = SignalType.COMMITMENT
    payload: dict[str, Any] = field(default_factory=dict[str, Any])  # Schema RF-C.2
    evidence_quote: str | None = None
    extraction_conf: float | None = None
    state: SignalState = SignalState.PENDING_CORRELATION
    decision_kind: DecisionKind | None = None
    decision_conf: float | None = None
    resolved_task_id: uuid.UUID | None = None
    retry_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: datetime | None = None


@dataclass
class CorrelationRun:
    """Auditoria completa de cada decisão de correlação — RF-D.6, NF-5."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    signal_id: uuid.UUID = field(default_factory=uuid.uuid4)
    candidates: list[dict[str, Any]] = field(default_factory=list[dict[str, Any]])  # [{task_id, retriever, rank, score, fused_score}]
    llm_assessments: dict[str, Any] | None = None  # Saída bruta do G2
    final_decision: str = ""
    final_confidence: float | None = None
    applied: bool = False
    routed_to_triage: bool = False
    policy_rule_id: str = ""  # Qual linha da matriz RF-G.8 decidiu
    guardrail_blocks: list[dict[str, Any]] = field(default_factory=list)
    skipped_llm: bool = False
    latency_ms: int | None = None
    correlation_id: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
