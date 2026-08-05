import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_live(async_client: AsyncClient) -> None:
    """Verifica que GET /health/live retorna status 200 e status=alive."""
    response = await async_client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert "env" in data
    assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_health_ready(async_client: AsyncClient) -> None:
    """Verifica que GET /health/ready retorna status 200 e status=ready."""
    response = await async_client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "env" in data
    assert data["version"] == "0.1.0"
