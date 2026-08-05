import pytest
from datetime import datetime, timedelta
from taskflow.adapters.llm.chatgpt_subscription import (
    ChatGPTSubscriptionLLMProvider,
    generate_pkce_pair,
)


def test_generate_pkce_pair():
    verifier, challenge = generate_pkce_pair()
    assert len(verifier) > 30
    assert len(challenge) > 20
    assert verifier != challenge


@pytest.mark.asyncio
async def test_chatgpt_subscription_provider_tokens():
    provider = ChatGPTSubscriptionLLMProvider(
        access_token="test_at",
        refresh_token="test_rt",
        expires_at=datetime.utcnow() + timedelta(hours=1),
    )

    token = await provider._ensure_valid_token()
    assert token == "test_at"


@pytest.mark.asyncio
async def test_chatgpt_subscription_extract_fallback():
    provider = ChatGPTSubscriptionLLMProvider(
        access_token="test_at",
        expires_at=datetime.utcnow() + timedelta(hours=1),
    )

    result = await provider.extract("Enviar relatório mensal até sexta-feira")
    assert "title" in result
    assert "description" in result
