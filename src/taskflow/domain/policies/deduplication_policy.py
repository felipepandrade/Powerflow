"""Política de deduplicação de itens de origem e sinais — RF-B.3 e RF-F.4."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence

from taskflow.domain.entities.source import CalendarEvent, SourceItem


class DeduplicationPolicy:
    """Política de deduplicação determinística.

    Impede o reprocessamento de e-mails, chats ou instâncias de eventos recorrentes
    cujo conteúdo não sofreu alteração.
    """

    @staticmethod
    def compute_content_hash(text: str) -> str:
        """Calcula o hash SHA256 do conteúdo textual limpo."""
        normalized = " ".join(text.strip().split()).lower()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def is_duplicate_source_item(
        new_item: SourceItem,
        existing_items: Sequence[SourceItem],
    ) -> bool:
        """Verifica se um SourceItem é duplicado com base em (external_id, revision_hash)."""
        for item in existing_items:
            if (
                item.external_id == new_item.external_id
                and item.revision_hash == new_item.revision_hash
            ):
                return True
        return False

    @staticmethod
    def is_duplicate_calendar_event(
        new_event: CalendarEvent,
        existing_events: Sequence[CalendarEvent],
    ) -> bool:
        """Verifica se uma instância de evento recorrente é duplicada pelo body_hash."""
        if not new_event.body_hash:
            return False
        for evt in existing_events:
            if (
                evt.series_master_id == new_event.series_master_id
                and evt.starts_at == new_event.starts_at
                and evt.body_hash == new_event.body_hash
            ):
                return True
        return False
