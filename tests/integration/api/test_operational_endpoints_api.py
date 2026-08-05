"""Testes de integração para os endpoints operacionais (timeline, undo, stale e capacity)."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_operational_endpoints(async_client: AsyncClient) -> None:
    # 1. Capacidade Diária
    cap_resp = await async_client.get("/api/system/capacity")
    assert cap_resp.status_code == 200
    assert cap_resp.json()["focus_time_available"] == 4.5

    # 2. Tarefas Envelhecidas
    stale_resp = await async_client.get("/api/tasks/stale")
    assert stale_resp.status_code == 200
    assert isinstance(stale_resp.json(), list)

    # 3. Lista de tarefas para buscar um ID
    tasks_resp = await async_client.get("/api/tasks")
    assert tasks_resp.status_code == 200
    tasks = tasks_resp.json()["data"]

    if len(tasks) > 0:
        task_id = tasks[0]["id"]
        # Timeline
        tl_resp = await async_client.get(f"/api/tasks/{task_id}/timeline")
        assert tl_resp.status_code == 200
        assert "timeline" in tl_resp.json()
