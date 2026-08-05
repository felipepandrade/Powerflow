"""Testes de integração para a API do Cockpit e Analytics."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_analytics_endpoints(async_client: AsyncClient) -> None:
    # 1. Gerar Snapshots
    snap_resp = await async_client.post("/api/analytics/snapshots")
    assert snap_resp.status_code == 200
    assert snap_resp.json()["status"] == "success"

    # 2. Calcular Métricas
    comp_resp = await async_client.post("/api/analytics/compute", json={})
    assert comp_resp.status_code == 200
    assert comp_resp.json()["status"] == "success"

    # 3. Listar Métricas
    metrics_resp = await async_client.get("/api/analytics/metrics")
    assert metrics_resp.status_code == 200
    assert len(metrics_resp.json()) >= 10
