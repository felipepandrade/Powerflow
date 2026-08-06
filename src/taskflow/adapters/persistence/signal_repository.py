from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taskflow.adapters.persistence.models import (
    CalendarEventORM,
    CorrelationRunORM,
    SignalORM,
    SourceItemORM,
    TaskProposalORM,
)
from taskflow.domain.entities.source import CalendarEvent, CorrelationRun, Signal, SourceItem
from taskflow.domain.entities.task import TaskProposal
from taskflow.domain.ports.ports import SignalRepository
from taskflow.domain.value_objects.enums import (
    DecisionKind,
    ProcessingStatus,
    ProposalKind,
    ProposalStatus,
    SignalState,
    SignalType,
    SourceKind,
)


class SqlAlchemySignalRepository(SignalRepository):
    """Durable repository for every artifact in the safe vertical pipeline."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _to_domain_signal(orm: SignalORM) -> Signal:
        return Signal(
            id=orm.id,
            source_item_id=orm.source_item_id,
            signal_type=SignalType(orm.signal_type),
            payload=orm.payload,
            evidence_quote=orm.evidence_quote,
            extraction_conf=orm.extraction_conf,
            state=SignalState(orm.state),
            decision_kind=DecisionKind(orm.decision_kind) if orm.decision_kind else None,
            decision_conf=orm.decision_conf,
            resolved_task_id=orm.resolved_task_id,
            retry_count=orm.retry_count,
            resolved_at=orm.resolved_at,
            created_at=orm.created_at,
        )

    @staticmethod
    def _to_domain_source(orm: SourceItemORM) -> SourceItem:
        return SourceItem(
            id=orm.id,
            kind=SourceKind(orm.kind),
            channel=orm.channel,
            external_id=orm.external_id,
            conversation_id=orm.conversation_id,
            revision_hash=orm.revision_hash,
            author_email=orm.author_email,
            author_name=orm.author_name,
            participants=orm.participants,
            title=orm.title,
            body_preview=orm.body_preview,
            body_full=orm.body_full,
            occurred_at=orm.occurred_at,
            has_attachments=orm.has_attachments,
            importance=orm.importance,
            web_link=orm.web_link,
            is_redacted=orm.is_redacted,
            processing_status=ProcessingStatus(orm.processing_status),
            filtered_reason=orm.filtered_reason,
            blocked_by_safety=orm.blocked_by_safety,
            processed_at=orm.processed_at,
            created_at=orm.created_at,
        )

    @staticmethod
    def _to_domain_proposal(orm: TaskProposalORM) -> TaskProposal:
        return TaskProposal(
            id=orm.id,
            signal_id=orm.signal_id,
            proposal_kind=ProposalKind(orm.kind),
            payload=orm.payload,
            candidate_tasks=orm.candidate_tasks,
            confidence=orm.confidence,
            status=ProposalStatus(orm.status),
            resolved_task_id=orm.target_task_id,
            rejection_reason=orm.rejection_reason,
            user_edits=orm.user_edits,
            created_at=orm.created_at,
            resolved_at=orm.resolved_at,
        )

    async def save(self, item: Signal | SourceItem | TaskProposal) -> None:
        if isinstance(item, Signal):
            await self.session.merge(
                SignalORM(
                    id=item.id,
                    source_item_id=item.source_item_id,
                    signal_type=item.signal_type.value,
                    state=item.state.value,
                    extraction_conf=item.extraction_conf,
                    payload=item.payload,
                    evidence_quote=item.evidence_quote,
                    decision_kind=item.decision_kind.value if item.decision_kind else None,
                    decision_conf=item.decision_conf,
                    resolved_task_id=item.resolved_task_id,
                    retry_count=item.retry_count,
                    resolved_at=item.resolved_at,
                    created_at=item.created_at,
                )
            )
        elif isinstance(item, SourceItem):
            await self.session.merge(
                SourceItemORM(
                    id=item.id,
                    kind=item.kind.value,
                    channel=item.channel,
                    external_id=item.external_id,
                    conversation_id=item.conversation_id,
                    revision_hash=item.revision_hash,
                    author_email=item.author_email,
                    author_name=item.author_name,
                    participants=item.participants,
                    title=item.title,
                    body_preview=item.body_preview,
                    body_full=item.body_full,
                    occurred_at=item.occurred_at,
                    has_attachments=item.has_attachments,
                    importance=item.importance,
                    web_link=item.web_link,
                    is_redacted=item.is_redacted,
                    processing_status=item.processing_status.value,
                    filtered_reason=item.filtered_reason,
                    blocked_by_safety=item.blocked_by_safety,
                    processed_at=item.processed_at,
                    created_at=item.created_at,
                )
            )
        elif isinstance(item, TaskProposal):
            await self.session.merge(
                TaskProposalORM(
                    id=item.id,
                    signal_id=item.signal_id,
                    kind=item.proposal_kind.value,
                    status=item.status.value,
                    target_task_id=item.resolved_task_id,
                    payload=item.payload,
                    candidate_tasks=item.candidate_tasks,
                    confidence=item.confidence,
                    user_edits=item.user_edits,
                    rejection_reason=item.rejection_reason,
                    created_at=item.created_at,
                    resolved_at=item.resolved_at,
                )
            )
        else:
            raise TypeError(f"Unsupported pipeline artifact: {type(item).__name__}")
        await self.session.flush()

    async def save_calendar_event(self, event: CalendarEvent) -> None:
        await self.session.merge(
            CalendarEventORM(
                source_item_id=event.source_item_id,
                graph_event_id=event.graph_event_id,
                series_master_id=event.series_master_id,
                instance_type=event.instance_type,
                body_hash=event.body_hash,
                starts_at=event.starts_at,
                ends_at=event.ends_at,
                duration_minutes=round(event.duration_minutes),
                is_all_day=event.is_all_day,
                timezone=event.timezone,
                location=event.location,
                is_online=event.is_online,
                join_url=event.join_url,
                linked_chat_id=event.linked_chat_id,
                organizer_email=event.organizer_email,
                my_response=event.my_response,
                show_as=event.show_as,
                sensitivity=event.sensitivity.value,
                is_cancelled=event.is_cancelled,
                recurrence_rule=event.recurrence_rule,
                attendee_count=event.attendee_count,
                categories=event.categories,
            )
        )
        await self.session.flush()

    async def get_signal_by_id(self, signal_id: uuid.UUID) -> Signal | None:
        result = await self.session.execute(select(SignalORM).where(SignalORM.id == signal_id))
        row = result.scalar_one_or_none()
        return None if row is None else self._to_domain_signal(row)

    async def get_source_item_by_id(self, item_id: uuid.UUID) -> SourceItem | None:
        result = await self.session.execute(
            select(SourceItemORM).where(SourceItemORM.id == item_id)
        )
        row = result.scalar_one_or_none()
        return None if row is None else self._to_domain_source(row)

    async def get_source_item_by_dedup_key(
        self, kind: str, external_id: str, revision_hash: str
    ) -> SourceItem | None:
        result = await self.session.execute(
            select(SourceItemORM).where(
                SourceItemORM.kind == kind,
                SourceItemORM.external_id == external_id,
                SourceItemORM.revision_hash == revision_hash,
            )
        )
        row = result.scalar_one_or_none()
        return None if row is None else self._to_domain_source(row)

    async def get_pending(self, limit: int = 50) -> Sequence[Signal]:
        result = await self.session.execute(
            select(SignalORM)
            .where(SignalORM.state == SignalState.PENDING_CORRELATION.value)
            .order_by(SignalORM.created_at, SignalORM.id)
            .limit(limit)
        )
        return [self._to_domain_signal(row) for row in result.scalars().all()]

    async def get_proposal_by_id(self, proposal_id: uuid.UUID) -> TaskProposal | None:
        result = await self.session.execute(
            select(TaskProposalORM).where(TaskProposalORM.id == proposal_id)
        )
        row = result.scalar_one_or_none()
        return None if row is None else self._to_domain_proposal(row)

    async def get_pending_proposals(self, limit: int = 50) -> Sequence[TaskProposal]:
        result = await self.session.execute(
            select(TaskProposalORM)
            .where(TaskProposalORM.status == ProposalStatus.PENDING.value)
            .order_by(TaskProposalORM.created_at, TaskProposalORM.id)
            .limit(limit)
        )
        return [self._to_domain_proposal(row) for row in result.scalars().all()]

    async def save_correlation_run(self, run: CorrelationRun) -> None:
        await self.session.merge(
            CorrelationRunORM(
                id=run.id,
                signal_id=run.signal_id,
                candidates=run.candidates,
                llm_assessments=run.llm_assessments,
                final_decision=run.final_decision,
                final_confidence=run.final_confidence,
                applied=run.applied,
                routed_to_triage=run.routed_to_triage,
                policy_rule_id=run.policy_rule_id,
                guardrail_blocks=run.guardrail_blocks,
                skipped_llm=run.skipped_llm,
                latency_ms=run.latency_ms,
                correlation_id=run.correlation_id,
                created_at=run.created_at,
            )
        )
        await self.session.flush()

    async def get_orphan_signals(
        self, since: datetime, limit: int = 100
    ) -> Sequence[Signal]:
        result = await self.session.execute(
            select(SignalORM)
            .where(
                SignalORM.state == SignalState.PENDING_CORRELATION.value,
                SignalORM.created_at <= since,
            )
            .order_by(SignalORM.created_at, SignalORM.id)
            .limit(limit)
        )
        return [self._to_domain_signal(row) for row in result.scalars().all()]
