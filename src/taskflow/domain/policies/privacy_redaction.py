"""PrivacyRedactionPolicy — RF-F.3 e NF-4.

Garante que eventos de calendário com sensitivity 'private' ou 'confidential'
NUNCA alcancem o payload enviado ao provedor de LLM.

Esta política é o único ponto de controle de privacidade de calendário
e deve ser testada com teste de propriedade que falha o build se
qualquer conteúdo sensível vazar.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from taskflow.domain.entities.source import CalendarEvent, SourceItem
from taskflow.domain.value_objects.enums import CalendarSensitivity, ProcessingStatus


class PrivacyRedactionPolicy:
    """Aplica redação de privacidade em itens de calendário sensíveis.

    Regra inviolável (RF-F.3, NF-4):
    - Eventos com sensitivity IN ('private', 'confidential') ou showAs='oof'
      são ingeridos APENAS como bloco de tempo ocupado: start, end, busy_status.
    - Assunto, corpo e participantes permanecem nulos.
    - NUNCA enviados ao LLM.
    """

    SENSITIVE_SENSITIVITIES: frozenset[CalendarSensitivity] = frozenset({
        CalendarSensitivity.PRIVATE,
        CalendarSensitivity.CONFIDENTIAL,
    })

    PRIVATE_SHOW_AS_VALUES: frozenset[str] = frozenset({"oof"})

    def should_redact(self, event: CalendarEvent) -> bool:
        """Retorna True se o evento deve ser redatado."""
        if event.sensitivity in self.SENSITIVE_SENSITIVITIES:
            return True
        if event.show_as and event.show_as.lower() in self.PRIVATE_SHOW_AS_VALUES:
            return True
        return False

    def redact(self, source_item: SourceItem, event: CalendarEvent) -> SourceItem:
        """Retorna SourceItem redatado — apenas start, end e busy_status.

        O SourceItem resultante tem ``is_redacted=True``, título, corpo
        e participantes nulos. NUNCA deve ser enviado ao LLM.
        """
        if not self.should_redact(event):
            return source_item

        return replace(
            source_item,
            title=None,
            body_preview=None,
            body_full=None,
            participants=[],
            author_email=None,
            author_name=None,
            is_redacted=True,
            processing_status=ProcessingStatus.FILTERED,
            filtered_reason="privacy_redaction",
        )

    def redact_calendar_metadata(self, event: CalendarEvent) -> CalendarEvent:
        """Keep only opaque identity, time window, timezone and busy status."""
        if not self.should_redact(event):
            return event
        return replace(
            event,
            series_master_id=None,
            instance_type=None,
            body_hash=None,
            location=None,
            is_online=False,
            join_url=None,
            linked_chat_id=None,
            organizer_email=None,
            my_response=None,
            recurrence_rule=None,
            attendee_count=None,
            categories=[],
        )
    def build_llm_payload(
        self,
        source_item: SourceItem,
        include_full_body: bool = False,
    ) -> dict[str, Any]:
        """Monta o payload seguro para envio ao LLM.

        Levanta ValueError se tentar construir payload de item redatado.
        """
        if source_item.is_redacted:
            raise ValueError(
                f"SourceItem {source_item.id} é redatado (privacidade) "
                "e NÃO pode ser enviado ao LLM."
            )

        content = (
            source_item.body_full
            if include_full_body and source_item.body_full
            else source_item.body_preview or ""
        )

        return {
            "id": str(source_item.id),
            "kind": source_item.kind.value,
            "title": source_item.title,
            "content": content,
            "author_email": source_item.author_email,
            "occurred_at": source_item.occurred_at.isoformat(),
        }
