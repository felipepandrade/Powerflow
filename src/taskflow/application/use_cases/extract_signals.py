"""Structured extraction with literal-evidence and privacy guardrails."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import structlog

from taskflow.domain.entities.source import Signal, SourceItem
from taskflow.domain.policies.privacy_redaction import PrivacyRedactionPolicy
from taskflow.domain.ports.ports import LLMProvider, Queue, SignalRepository, UnitOfWork
from taskflow.domain.value_objects.enums import ProcessingStatus, SignalState, SignalType

log = structlog.get_logger()


class ExtractSignalsUseCase:
    """Convert one safe source payload into validated, versioned signals."""

    def __init__(
        self,
        signal_repo: SignalRepository,
        llm: LLMProvider,
        queue: Queue,
        uow: UnitOfWork,
        privacy_policy: PrivacyRedactionPolicy | None = None,
    ) -> None:
        self._signal_repo = signal_repo
        self._llm = llm
        self._queue = queue
        self._uow = uow
        self._privacy = privacy_policy or PrivacyRedactionPolicy()

    async def execute(self, source_item_id: uuid.UUID) -> list[uuid.UUID]:
        item = await self._signal_repo.get_source_item_by_id(source_item_id)
        if item is None:
            raise ValueError(f"SourceItem {source_item_id} not found")
        if item.is_redacted:
            log.warning("extract.private_source_blocked", source_item_id=str(source_item_id))
            return []

        llm_payload = self._privacy.build_llm_payload(item)
        text = str(llm_payload["content"])
        if not text:
            await self._mark_item(item, ProcessingStatus.FILTERED, "empty_content")
            return []

        context: dict[str, Any] = {
            "schema_version": "signal-extraction/v1",
            "source_kind": item.kind.value,
            "author_name": item.author_name,
            "author_email": item.author_email,
            "subject": item.title,
            "occurred_at": item.occurred_at.isoformat(),
        }

        try:
            classification = await self._llm.classify(text, context)
            if not bool(classification.get("has_commitment", True)):
                await self._mark_item(item, ProcessingStatus.FILTERED, "no_actionable_signal")
                return []

            response = await self._llm.extract(text, context)
            if bool(response.get("blocked_by_safety", False)):
                item.blocked_by_safety = True
                safety_signal = Signal(
                    source_item_id=item.id,
                    signal_type=SignalType.CONTEXT,
                    payload={"blocked_by_safety": True, "schema_version": "signal/v1"},
                    evidence_quote=text[: min(len(text), 200)],
                    extraction_conf=0.0,
                )
                async with self._uow:
                    await self._signal_repo.save(item)
                    await self._signal_repo.save(safety_signal)
                    await self._uow.commit()
                await self._queue.enqueue(
                    "correlate_signal",
                    {"signal_id": str(safety_signal.id), "force_triage": True},
                )
                return [safety_signal.id]

            raw_signals = response.get("signals")
            if not isinstance(raw_signals, list):
                raise TypeError("LLM extraction must return a signals list")

            signals: list[Signal] = []
            for raw in raw_signals:
                signal = self._build_signal(item, text, raw)
                if signal is not None:
                    signals.append(signal)

            item.processing_status = ProcessingStatus.EXTRACTED
            item.processed_at = datetime.utcnow()
            async with self._uow:
                await self._signal_repo.save(item)
                for signal in signals:
                    await self._signal_repo.save(signal)
                await self._uow.commit()

            for signal in signals:
                await self._queue.enqueue(
                    "correlate_signal", {"signal_id": str(signal.id)}
                )
            return [signal.id for signal in signals]
        except Exception:
            item.processing_status = ProcessingStatus.FAILED
            item.processed_at = datetime.utcnow()
            async with self._uow:
                await self._signal_repo.save(item)
                await self._uow.commit()
            log.exception("extract.failed", source_item_id=str(source_item_id))
            raise

    @staticmethod
    def _build_signal(
        item: SourceItem, source_text: str, raw: object
    ) -> Signal | None:
        if not isinstance(raw, dict):
            return None
        evidence = raw.get("evidence_quote")
        if not isinstance(evidence, str) or not evidence or evidence not in source_text:
            log.warning("extract.invalid_literal_evidence", source_item_id=str(item.id))
            return None
        confidence_raw = raw.get("extraction_confidence", raw.get("confidence"))
        if not isinstance(confidence_raw, (int, float)):
            return None
        confidence = float(confidence_raw)
        if not 0.0 <= confidence <= 1.0:
            return None
        try:
            signal_type = SignalType(str(raw.get("signal_type", "")))
        except ValueError:
            return None
        payload_raw = raw.get("payload")
        if not isinstance(payload_raw, dict):
            return None
        payload = {str(key): value for key, value in payload_raw.items()}
        payload.setdefault("schema_version", "signal/v1")
        return Signal(
            id=uuid.uuid4(),
            source_item_id=item.id,
            signal_type=signal_type,
            payload=payload,
            evidence_quote=evidence,
            extraction_conf=confidence,
            state=SignalState.PENDING_CORRELATION,
            created_at=datetime.utcnow(),
        )

    async def _mark_item(
        self, item: SourceItem, status: ProcessingStatus, reason: str
    ) -> None:
        item.processing_status = status
        item.filtered_reason = reason
        item.processed_at = datetime.utcnow()
        async with self._uow:
            await self._signal_repo.save(item)
            await self._uow.commit()
