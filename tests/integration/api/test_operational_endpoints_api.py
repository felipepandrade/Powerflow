"""Integration tests for honest operational endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_operational_endpoints(async_client: AsyncClient) -> None:
    capacity_response = await async_client.get("/api/system/capacity")
    assert capacity_response.status_code == 200
    capacity = capacity_response.json()
    assert capacity["state"] in {"known", "unknown"}
    assert capacity["provenance"] == "daily_calendar_snapshots"
    if capacity["state"] == "unknown":
        assert capacity["meeting_minutes"] is None
        assert capacity["available_minutes"] is None

    stale_response = await async_client.get("/api/tasks/stale")
    assert stale_response.status_code == 200
    assert isinstance(stale_response.json(), list)

    tasks_response = await async_client.get("/api/tasks")
    assert tasks_response.status_code == 200
    tasks = tasks_response.json()["data"]
    if tasks:
        task_id = tasks[0]["id"]
        timeline_response = await async_client.get(f"/api/tasks/{task_id}/timeline")
        assert timeline_response.status_code == 200
        assert "timeline" in timeline_response.json()