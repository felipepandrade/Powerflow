from unittest.mock import AsyncMock

import pytest

from taskflow.adapters.llm.copilot_web_provider import CopilotWebLLMProvider


@pytest.mark.asyncio
async def test_copilot_web_provider_classify(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = CopilotWebLLMProvider()
    send = AsyncMock(return_value="SIM")
    monkeypatch.setattr(provider, "_send_copilot_prompt", send)

    result = await provider.classify("Reunião de alinhamento amanhã", {})

    assert result == {"has_actionable_commitment": True, "confidence": 0.85}
    send.assert_awaited_once()


@pytest.mark.asyncio
async def test_copilot_web_provider_extract(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = CopilotWebLLMProvider()
    send = AsyncMock(return_value='{"title":"Relatório","description":"Enviar sexta"}')
    monkeypatch.setattr(provider, "_send_copilot_prompt", send)

    result = await provider.extract("Enviar relatório mensal de vendas até sexta")

    assert result == {"title": "Relatório", "description": "Enviar sexta"}
    send.assert_awaited_once()


@pytest.mark.asyncio
async def test_copilot_web_provider_fails_closed_without_browser(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = CopilotWebLLMProvider()
    monkeypatch.setattr(
        provider,
        "_send_copilot_prompt",
        AsyncMock(side_effect=RuntimeError("browser unavailable")),
    )

    with pytest.raises(RuntimeError, match="browser unavailable"):
        await provider.classify("texto", {})