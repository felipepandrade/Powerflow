from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from taskflow.main import app


@pytest.fixture
async def async_client():
    # Mock do LLM Provider para não tentar instanciar o Gemini real sem chave
    from taskflow.config.container import get_llm_provider
    from taskflow.domain.ports.ports import LLMProvider
    
    mock_llm = AsyncMock(spec=LLMProvider)
    
    app.dependency_overrides[get_llm_provider] = lambda: mock_llm

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient) -> None:
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}


@pytest.mark.asyncio
async def test_ingest_source_endpoint(async_client: AsyncClient) -> None:
    import uuid
    from taskflow.application.dto.commands import IngestSourceItemResult
    item_id = uuid.uuid4()
    mock_result = IngestSourceItemResult(
        source_item_id=item_id,
        was_deduplicated=False,
        was_filtered=False,
        filtered_reason=None,
        signal_id=None,
        was_enqueued_for_correlation=True,
    )

    with patch("taskflow.application.use_cases.ingest_source_item.IngestSourceItemUseCase.execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = mock_result
        
        payload = {
            "content": "Lembrar de revisar o PR",
            "channel": "api"
        }
        
        response = await async_client.post("/api/signals", json=payload)
        
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "accepted"
        assert "source_item_id" in data


@pytest.mark.asyncio
async def test_scan_stale_endpoint(async_client: AsyncClient) -> None:
    with patch("taskflow.application.use_cases.scan_stale_items.ScanStaleItemsUseCase.execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = [1, 2, 3] # Simula 3 tarefas afetadas
        
        response = await async_client.post("/api/system/scan-stale")
        assert response.status_code == 200
        data = response.json()
        assert data["scanned_tasks_count"] == 3
