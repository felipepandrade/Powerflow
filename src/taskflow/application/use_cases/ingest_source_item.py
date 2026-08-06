"""Safe canonical source ingestion."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime

import structlog

from taskflow.application.dto.commands import IngestSourceItemCommand, IngestSourceItemResult
from taskflow.domain.entities.source import CalendarEvent, SourceItem
from taskflow.domain.policies.privacy_redaction import PrivacyRedactionPolicy
from taskflow.domain.ports.ports import Queue, SignalRepository, TaskRepository, UnitOfWork
from taskflow.domain.value_objects.enums import CalendarSensitivity, ProcessingStatus, SourceKind

log = structlog.get_logger()


class IngestSourceItemUseCase:
    """Persist one canonical revision, redact it, then enqueue extraction."""

    def __init__(
        self,
        task_repo: TaskRepository,
        signal_repo: SignalRepository,
        queue: Queue,
        uow: UnitOfWork,
        privacy_policy: PrivacyRedactionPolicy | None = None,
    ) -> None:
        self._signal_repo = signal_repo
        self._queue = queue
        self._uow = uow
        self._privacy = privacy_policy or PrivacyRedactionPolicy()

    async def execute(self, cmd: IngestSourceItemCommand) -> IngestSourceItemResult:
        if not cmd.external_id.strip() or not cmd.revision_hash.strip():
            raise ValueError("external_id and revision_hash are required")

        async with self._uow:
            existing = await self._signal_repo.get_source_item_by_dedup_key(
                cmd.kind.value, cmd.external_id, cmd.revision_hash
            )
            if existing is not None:
                await self._uow.commit()
                return IngestSourceItemResult(
                    source_item_id=existing.id,
                    was_deduplicated=True,
                    was_filtered=existing.processing_status == ProcessingStatus.FILTERED,
                    filtered_reason=existing.filtered_reason,
                    signal_id=None,
                    was_enqueued_for_correlation=False,
                )

            item = self._build_source_item(cmd)
            calendar_event: CalendarEvent | None = None
            if cmd.kind == SourceKind.CALENDAR_EVENT:
                calendar_event = self._build_calendar_event(cmd, item.id)
                item = self._privacy.redact(item, calendar_event)

            await self._signal_repo.save(item)
            if calendar_event is not None:
                await self._signal_repo.save_calendar_event(calendar_event)
            await self._uow.commit()

        if item.is_redacted:
            log.info("ingest.redacted", source_item_id=str(item.id))
            return IngestSourceItemResult(
                source_item_id=item.id,
                was_deduplicated=False,
                was_filtered=True,
                filtered_reason=item.filtered_reason,
                signal_id=None,
                was_enqueued_for_correlation=False,
            )

        job_id = await self._queue.enqueue(
            "extract_signals", {"source_item_id": str(item.id)}
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

    @staticmethod
    def _build_source_item(cmd: IngestSourceItemCommand) -> SourceItem:
        preview_source = cmd.body_preview or cmd.body_full
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
            body_preview=preview_source[:500] if preview_source else None,
            body_full=cmd.body_full if cmd.store_full_body else None,
            occurred_at=cmd.occurred_at,
            has_attachments=cmd.has_attachments,
            importance=cmd.importance,
            web_link=cmd.web_link,
            processing_status=ProcessingStatus.PENDING,
            created_at=datetime.utcnow(),
        )

    @staticmethod
    def _build_calendar_event(
        cmd: IngestSourceItemCommand, source_item_id: uuid.UUID
    ) -> CalendarEvent:
        try:
            sensitivity = CalendarSensitivity(
                (cmd.calendar_sensitivity or CalendarSensitivity.NORMAL.value).lower()
            )
        except ValueError:
            sensitivity = CalendarSensitivity.NORMAL

        return CalendarEvent(
            source_item_id=source_item_id,
            graph_event_id=cmd.external_id,
            series_master_id=cmd.calendar_series_master_id,
            instance_type=cmd.calendar_instance_type,
            body_hash=cmd.calendar_body_hash,
            starts_at=cmd.calendar_starts_at or cmd.occurred_at,
            ends_at=cmd.calendar_ends_at or cmd.occurred_at,
            is_all_day=cmd.calendar_is_all_day,
            timezone=cmd.calendar_timezone,
            location=cmd.calendar_location,
            is_online=cmd.calendar_is_online,
            join_url=cmd.calendar_join_url,
            linked_chat_id=cmd.calendar_linked_chat_id,
            organizer_email=cmd.calendar_organizer_email,
            my_response=cmd.calendar_my_response,
            show_as=cmd.calendar_show_as,
            sensitivity=sensitivity,
            is_cancelled=cmd.calendar_is_cancelled,
            attendee_count=cmd.calendar_attendee_count,
            categories=cmd.calendar_categories,
        )

    @staticmethod
    def compute_dedup_key(external_id: str, revision_hash: str) -> str:
        """Stable diagnostic key; database uniqueness remains authoritative."""
        return hashlib.sha256(f"{external_id}:{revision_hash}".encode()).hexdigest()
