import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taskflow.adapters.persistence.models import CorrelationRunORM, SignalORM, SourceItemORM
from taskflow.domain.entities.source import Signal, SourceItem
from taskflow.domain.ports.ports import SignalRepository
from taskflow.domain.value_objects.enums import SignalState, SignalType


class SqlAlchemySignalRepository(SignalRepository):
    """Implementação do repositório de sinais com SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain_signal(self, orm: SignalORM) -> Signal:
        return Signal(
            id=orm.id,
            source_item_id=orm.source_item_id,
            signal_type=SignalType(orm.signal_type),
            state=SignalState(orm.state),
            extraction_conf=orm.extraction_conf,
            payload=orm.payload,
            decision_kind=None,  # ignorado no mapeamento básico
            decision_conf=orm.decision_conf,
            resolved_task_id=orm.resolved_task_id,
            resolved_at=orm.resolved_at,
            created_at=orm.created_at,
        )

    async def save(self, item: Any) -> None:
        # Usa duck-typing simples para gravar Signal ou SourceItem.
        if isinstance(item, Signal):
            orm = SignalORM(
                id=item.id,
                source_item_id=item.source_item_id,
                signal_type=item.signal_type.value,
                state=item.state.value,
                extraction_conf=item.extraction_conf,
                payload=item.payload,
                decision_kind=item.decision_kind.value if item.decision_kind else None,
                decision_conf=item.decision_conf,
                resolved_task_id=item.resolved_task_id,
                resolved_at=item.resolved_at,
                created_at=item.created_at,
            )
            await self.session.merge(orm)
            await self.session.flush()

        elif isinstance(item, SourceItem):
            orm_si = SourceItemORM(
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
            await self.session.merge(orm_si)
            await self.session.flush()

    async def get_source_item_by_id(self, item_id: uuid.UUID) -> SourceItem | None:
        stmt = select(SourceItemORM).where(SourceItemORM.id == item_id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        if not orm:
            return None
        from taskflow.domain.value_objects.enums import SourceKind, ProcessingStatus
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

    async def get_pending(self, limit: int = 50) -> Sequence[Signal]:
        stmt = select(SignalORM).where(SignalORM.state == SignalState.PENDING_CORRELATION.value).limit(limit)
        result = await self.session.execute(stmt)
        return [self._to_domain_signal(r) for r in result.scalars().all()]

    async def get_orphan_signals(self, since: datetime, limit: int = 100) -> Sequence[Signal]:
        stmt = select(SignalORM).where(SignalORM.state == SignalState.PENDING_CORRELATION.value).where(SignalORM.created_at >= since).limit(limit)
        result = await self.session.execute(stmt)
        return [self._to_domain_signal(r) for r in result.scalars().all()]

    async def save_correlation_run(self, run: Any) -> None:
        orm = CorrelationRunORM(
            id=run.id,
            signal_id=run.signal_id,
            candidates=run.candidates,
            llm_assessments=run.llm_assessments,
            final_decision=run.final_decision,
            final_confidence=run.final_confidence,
            applied=run.applied,
            routed_to_triage=run.routed_to_triage,
            policy_rule_id=run.policy_rule_id,
            skipped_llm=run.skipped_llm,
            latency_ms=run.latency_ms,
            created_at=run.created_at,
        )
        await self.session.merge(orm)
        await self.session.flush()
