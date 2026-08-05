"""Testes unitários para PrivacyRedactionPolicy — RF-F.3, NF-4.

★ Teste de PROPRIEDADE: nenhum SourceItem com sensitivity private/confidential
   pode alcançar o payload enviado ao LLMProvider.
★ Falha no build se essa invariante for violada.
"""

import uuid
from datetime import datetime

import pytest

from taskflow.domain.entities.source import CalendarEvent, SourceItem
from taskflow.domain.policies.privacy_redaction import PrivacyRedactionPolicy
from taskflow.domain.value_objects.enums import CalendarSensitivity, ProcessingStatus, SourceKind

policy = PrivacyRedactionPolicy()


def make_source_item(**kwargs) -> SourceItem:
    return SourceItem(
        id=uuid.uuid4(),
        kind=SourceKind.CALENDAR_EVENT,
        channel="calendar",
        external_id="evt-001",
        revision_hash="abc",
        title=kwargs.get("title", "Reunião Importante"),
        body_preview=kwargs.get("body_preview", "Conteúdo da reunião"),
        body_full=kwargs.get("body_full", "Conteúdo completo"),
        participants=kwargs.get("participants", [{"email": "a@b.com"}]),
        author_email=kwargs.get("author_email", "org@empresa.com"),
        author_name=kwargs.get("author_name", "Organizador"),
        occurred_at=datetime.utcnow(),
        is_redacted=kwargs.get("is_redacted", False),
    )


def make_calendar_event(sensitivity: CalendarSensitivity, show_as: str = "busy") -> CalendarEvent:
    return CalendarEvent(
        source_item_id=uuid.uuid4(),
        graph_event_id="g-001",
        starts_at=datetime.utcnow(),
        ends_at=datetime.utcnow(),
        sensitivity=sensitivity,
        show_as=show_as,
    )


class TestShouldRedact:
    """Verifica quando a redação deve ser aplicada."""

    def test_private_sensitivity_requires_redaction(self) -> None:
        event = make_calendar_event(CalendarSensitivity.PRIVATE)
        assert policy.should_redact(event) is True

    def test_confidential_sensitivity_requires_redaction(self) -> None:
        event = make_calendar_event(CalendarSensitivity.CONFIDENTIAL)
        assert policy.should_redact(event) is True

    def test_personal_sensitivity_no_redaction(self) -> None:
        event = make_calendar_event(CalendarSensitivity.PERSONAL)
        assert policy.should_redact(event) is False

    def test_normal_sensitivity_no_redaction(self) -> None:
        event = make_calendar_event(CalendarSensitivity.NORMAL)
        assert policy.should_redact(event) is False

    def test_oof_show_as_requires_redaction(self) -> None:
        event = make_calendar_event(CalendarSensitivity.NORMAL, show_as="oof")
        assert policy.should_redact(event) is True

    def test_busy_show_as_no_redaction(self) -> None:
        event = make_calendar_event(CalendarSensitivity.NORMAL, show_as="busy")
        assert policy.should_redact(event) is False


class TestRedaction:
    """Verifica que a redação remove campos sensíveis."""

    def test_private_event_title_is_null(self) -> None:
        item = make_source_item()
        event = make_calendar_event(CalendarSensitivity.PRIVATE)
        redacted = policy.redact(item, event)
        assert redacted.title is None

    def test_private_event_body_preview_is_null(self) -> None:
        item = make_source_item()
        event = make_calendar_event(CalendarSensitivity.PRIVATE)
        redacted = policy.redact(item, event)
        assert redacted.body_preview is None

    def test_private_event_body_full_is_null(self) -> None:
        item = make_source_item()
        event = make_calendar_event(CalendarSensitivity.PRIVATE)
        redacted = policy.redact(item, event)
        assert redacted.body_full is None

    def test_private_event_participants_are_empty(self) -> None:
        item = make_source_item()
        event = make_calendar_event(CalendarSensitivity.PRIVATE)
        redacted = policy.redact(item, event)
        assert redacted.participants == []

    def test_private_event_author_email_is_null(self) -> None:
        item = make_source_item()
        event = make_calendar_event(CalendarSensitivity.PRIVATE)
        redacted = policy.redact(item, event)
        assert redacted.author_email is None

    def test_private_event_is_redacted_flag_set(self) -> None:
        item = make_source_item()
        event = make_calendar_event(CalendarSensitivity.PRIVATE)
        redacted = policy.redact(item, event)
        assert redacted.is_redacted is True

    def test_private_event_status_filtered(self) -> None:
        item = make_source_item()
        event = make_calendar_event(CalendarSensitivity.PRIVATE)
        redacted = policy.redact(item, event)
        assert redacted.processing_status == ProcessingStatus.FILTERED

    def test_normal_event_not_redacted(self) -> None:
        item = make_source_item()
        event = make_calendar_event(CalendarSensitivity.NORMAL)
        result = policy.redact(item, event)
        assert result.title == "Reunião Importante"
        assert result.is_redacted is False


class TestLLMPayloadProperty:
    """★ Teste de PROPRIEDADE — RF-F.3, NF-4, Seção 14.3.

    Nenhum SourceItem redatado pode alcançar o payload enviado ao LLMProvider.
    Este teste FALHA o build se a invariante for violada.
    """

    def test_redacted_item_raises_on_llm_payload(self) -> None:
        """★ PROPRIEDADE: item redatado NÃO pode ser enviado ao LLM."""
        item = make_source_item(is_redacted=True)
        with pytest.raises(ValueError, match="redatado"):
            policy.build_llm_payload(item)

    def test_normal_item_payload_is_safe(self) -> None:
        item = make_source_item(is_redacted=False)
        payload = policy.build_llm_payload(item)
        assert "content" in payload
        assert payload.get("content") != ""

    def test_private_then_redact_then_payload_raises(self) -> None:
        """Ciclo completo: evento privado → redação → tentativa de envio → erro."""
        item = make_source_item()
        event = make_calendar_event(CalendarSensitivity.PRIVATE)
        redacted = policy.redact(item, event)
        # ★ PROPRIEDADE: item após redação nunca pode chegar ao LLM
        with pytest.raises(ValueError):
            policy.build_llm_payload(redacted)

    def test_get_content_for_llm_empty_for_redacted(self) -> None:
        """SourceItem.get_content_for_llm() retorna vazio para redatados."""
        item = make_source_item(is_redacted=True)
        assert item.get_content_for_llm() == ""

    def test_get_content_for_llm_returns_content_for_normal(self) -> None:
        item = make_source_item(is_redacted=False, body_preview="Texto da reuniao", body_full=None)
        assert item.get_content_for_llm() == "Texto da reuniao"
