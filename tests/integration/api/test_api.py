from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from taskflow.application.dto.commands import ScanStaleItemsResult
from taskflow.main import app


@pytest.fixture
async def async_client():
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

    mock_result = IngestSourceItemResult(
        source_item_id=uuid.uuid4(),
        was_deduplicated=False,
        was_filtered=False,
        filtered_reason=None,
        signal_id=None,
        was_enqueued_for_correlation=True,
    )

    with patch(
        "taskflow.application.use_cases.ingest_source_item.IngestSourceItemUseCase.execute",
        new_callable=AsyncMock,
    ) as mock_exec:
        mock_exec.return_value = mock_result
        response = await async_client.post(
            "/api/signals",
            json={"content": "Lembrar de revisar o PR", "channel": "api"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "accepted"
    assert "source_item_id" in data


@pytest.mark.asyncio
async def test_scan_stale_endpoint(async_client: AsyncClient) -> None:
    result = ScanStaleItemsResult(
        total_scanned=3,
        stale_count=2,
        follow_ups_created=1,
        reports=[],
    )
    with patch(
        "taskflow.application.use_cases.scan_stale_items.ScanStaleItemsUseCase.execute",
        new_callable=AsyncMock,
        return_value=result,
    ) as mock_exec:
        response = await async_client.post("/api/system/scan-stale")

    assert response.status_code == 200
    assert response.json()["scanned_tasks_count"] == 3
    mock_exec.assert_awaited_once()