from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from taskflow.adapters.llm.gemini_provider import GeminiProvider
from taskflow.adapters.llm.ollama_provider import OllamaProvider


@pytest.mark.asyncio
async def test_ollama_provider_classify() -> None:
    provider = OllamaProvider(base_url="http://fake", model_name="test-model")
    
    with patch("httpx.AsyncClient.post") as mock_post:
        # Em httpx, response.json() é síncrono e response.raise_for_status() também.
        class FakeResponse:
            def raise_for_status(self) -> None: pass
            def json(self) -> dict[str, Any]: return {"response": '{"is_actionable": true, "confidence": 0.9}'}
            
        mock_post.return_value = FakeResponse()

        res = await provider.classify("Lembrar de comprar leite", {})
        assert res.get("is_actionable") is True
        assert res.get("confidence") == 0.9


@pytest.mark.asyncio
async def test_gemini_provider_extract() -> None:
    # Mesmo sem API Key o client inicializa
    provider = GeminiProvider(api_key="fake-key")
    
    # Mockando a dependência interna de chamadas do genai
    with patch.object(provider.client.aio.models, "generate_content", new_callable=AsyncMock) as mock_gen:
        mock_response = AsyncMock()
        mock_response.text = '{"title": "Comprar leite", "priority": "high"}'
        mock_gen.return_value = mock_response

        res = await provider.extract("Lembrar de comprar leite urgente", {})
        assert res.get("title") == "Comprar leite"
        assert res.get("priority") == "high"
