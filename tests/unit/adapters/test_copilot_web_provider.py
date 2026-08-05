import pytest
from taskflow.adapters.llm.copilot_web_provider import CopilotWebLLMProvider


@pytest.mark.asyncio
async def test_copilot_web_provider_classify():
    provider = CopilotWebLLMProvider()
    res = await provider.classify("Reunião de alinhamento com a diretoria amanhã às 14h", {})
    assert "has_actionable_commitment" in res
    assert isinstance(res["has_actionable_commitment"], bool)


@pytest.mark.asyncio
async def test_copilot_web_provider_extract():
    provider = CopilotWebLLMProvider()
    res = await provider.extract("Enviar relatório mensal de vendas até sexta")
    assert "title" in res
    assert "description" in res
