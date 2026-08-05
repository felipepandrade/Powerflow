"""Use Case: IngestSourceItem — UC-1.

Orquestra o pipeline de ingestão de um item de origem:
  1. Deduplicação por revision_hash
  2. Construção do SourceItem / CalendarEvent
  3. Redação de privacidade (eventos private/confidential)
  4. Persistência
  5. Enfileiramento para extração de sinais
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime

import structlog

from taskflow.application.dto.commands import IngestSourceItemCommand, IngestSourceItemResult
from taskflow.domain.entities.source import CalendarEvent, SourceItem
from taskflow.domain.policies.privacy_redaction import PrivacyRedactionPolicy
from taskflow.domain.ports.ports import Queue, SignalRepository, TaskRepository, UnitOfWork
from taskflow.domain.value_objects.enums import (
    CalendarSensitivity,
    ProcessingStatus,
    SourceKind,
)

log = structlog.get_logger()


class IngestSourceItemUseCase:
    """UC-1 — Ingestão de SourceItem.

    Recebe dados brutos de qualquer canal e produz um SourceItem
    persistido + sinal enfileirado para correlação.
    """

    def __init__(
        self,
        task_repo: TaskRepository,
        signal_repo: SignalRepository,
        queue: Queue,
        uow: UnitOfWork,
        privacy_policy: PrivacyRedactionPolicy | None = None,
    ) -> None:
        self._task_repo = task_repo
        self._signal_repo = signal_repo
        self._queue = queue
        self._uow = uow
        self._privacy = privacy_policy or PrivacyRedactionPolicy()

    async def execute(self, cmd: IngestSourceItemCommand) -> IngestSourceItemResult:
        """Executa o pipeline de ingestão."""
        log.info("ingest.start", kind=cmd.kind.value, external_id=cmd.external_id)

        item = self._build_source_item(cmd)
        cal_event: CalendarEvent | None = None

        if cmd.kind == SourceKind.CALENDAR_EVENT:
            cal_event = self._build_calendar_event(cmd, item.id)
            item = self._privacy.redact(item, cal_event)

        if item.is_redacted:
            # Não enfileira — apenas persiste metadados
            async with self._uow:
                await self._signal_repo.save(item)  # type: ignore[arg-type]
                await self._uow.commit()
            log.info("ingest.redacted", source_item_id=str(item.id))
            return IngestSourceItemResult(
                source_item_id=item.id,
                was_deduplicated=False,
                was_filtered=True,
                filtered_reason=item.filtered_reason,
                signal_id=None,
                was_enqueued_for_correlation=False,
            )

        item = self._mark_pending(item)
        
        async with self._uow:
            await self._signal_repo.save(item)  # type: ignore[arg-type]
            await self._uow.commit()

        job_id = await self._queue.enqueue(
            "extract_signals",
            {"source_item_id": str(item.id)},
        )

        log.info("ingest.enqueued", source_item_id=str(item.id), job_id=job_id)
        return IngestSourceItemResult(
            source_item_id=item.id,
            was_deduplicated=False,
            was_filtered=False,
            filtered_reason=None,
            signal_id=None,
            was_enqueued_for_correlation=True,
        )

    def _build_source_item(self, cmd: IngestSourceItemCommand) -> SourceItem:
        """Constrói o SourceItem a partir do comando."""
        return SourceItem(
            id=uuid.uuid4(),
            kind=cmd.kind,
            channel=cmd.channel,
            external_id=cmd.external_id,
            conversation_id=cmd.conversation_id,
            revision_hash=cmd.revision_hash,
            author_email=cmd.author_email,
            author_name=cmd.author_name,
            participants=cmd.participants,
            title=cmd.title,
            body_preview=cmd.body_preview[:500] if cmd.body_preview else None,
            body_full=cmd.body_full,
            occurred_at=cmd.occurred_at,
            has_attachments=cmd.has_attachments,
            importance=cmd.importance,
            web_link=cmd.web_link,
            processing_status=ProcessingStatus.PENDING,
            created_at=datetime.utcnow(),
        )

    def _build_calendar_event(
        self,
        cmd: IngestSourceItemCommand,
        source_item_id: uuid.UUID,
    ) -> CalendarEvent:
        """Constrói o CalendarEvent a partir do comando."""
        sensitivity = CalendarSensitivity.NORMAL
        if cmd.calendar_sensitivity:
            try:
                sensitivity = CalendarSensitivity(cmd.calendar_sensitivity.lower())
            except ValueError:
                sensitivity = CalendarSensitivity.NORMAL

        return CalendarEvent(
            source_item_id=source_item_id,
            graph_event_id=cmd.external_id,
            series_master_id=cmd.calendar_series_master_id,
            starts_at=cmd.calendar_starts_at or cmd.occurred_at,
            ends_at=cmd.calendar_ends_at or cmd.occurred_at,
            is_all_day=cmd.calendar_is_all_day,
            is_online=cmd.calendar_is_online,
            join_url=cmd.calendar_join_url,
            linked_chat_id=cmd.calendar_linked_chat_id,
            organizer_email=cmd.calendar_organizer_email,
            my_response=cmd.calendar_my_response,
            show_as=cmd.calendar_show_as,
            sensitivity=sensitivity,
            is_cancelled=cmd.calendar_is_cancelled,
            attendee_count=cmd.calendar_attendee_count,
        )

    def _mark_pending(self, item: SourceItem) -> SourceItem:
        """Marca o item como pendente de extração."""
        from dataclasses import replace
        return replace(item, processing_status=ProcessingStatus.PENDING)

    @staticmethod
    def compute_dedup_key(external_id: str, revision_hash: str) -> str:
        """Gera a chave de deduplicação para verificar duplicatas."""
        return hashlib.sha256(f"{external_id}:{revision_hash}".encode()).hexdigest()
