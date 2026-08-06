"""Testes de integração para a API do Cockpit e Analytics."""

import pytest
from httpx import AsyncClient

from taskflow.config.container import get_llm_provider
from taskflow.main import app


@pytest.mark.asyncio
async def test_analytics_endpoints(async_client: AsyncClient) -> None:
    # 1. Gerar Snapshots
    snap_resp = await async_client.post("/api/analytics/snapshots")
    assert snap_resp.status_code == 200
    assert snap_resp.json()["status"] == "success"

    # 2. Calcular Métricas
    class LLMSpy:
        def __init__(self) -> None:
            self.calls = 0

        async def draft_follow_up(self, *args: object, **kwargs: object) -> str:
            self.calls += 1
            raise AssertionError("Metric computation must never call an LLM")

    spy = LLMSpy()
    app.dependency_overrides[get_llm_provider] = lambda: spy
    try:
        comp_resp = await async_client.post("/api/analytics/compute", json={})
    finally:
        app.dependency_overrides.pop(get_llm_provider, None)
    assert spy.calls == 0
    assert comp_resp.status_code == 200
    assert comp_resp.json()["status"] == "success"

    # 3. Listar Métricas
    metrics_resp = await async_client.get("/api/analytics/metrics")
    assert metrics_resp.status_code == 200
    assert len(metrics_resp.json()) >= 10

    metric = next(item for item in metrics_resp.json() if item["metric_id"] == "flow.throughput")
    required = {
        "value",
        "coverage",
        "sample_size",
        "is_suppressed",
        "suppression_reason",
        "caveat",
        "period_comparison",
        "numerator",
        "denominator",
        "formula",
        "provenance",
    }
    assert required <= metric.keys()

    today = metric["period_start"]
    drilldown = await async_client.get(
        f"/api/analytics/metrics/{metric['metric_id']}/drilldown",
        params={"period_start": today, "period_end": metric["period_end"]},
    )
    assert drilldown.status_code == 200
    assert drilldown.json()["reconciliation"]["reconciles"] is True

    calendar = await async_client.get(
        "/api/analytics/calendar",
        params={"start_date": today, "end_date": today},
    )
    assert calendar.status_code == 200
    calendar_payload = calendar.json()
    assert calendar_payload["state"] == "known"
    assert calendar_payload["coverage"] == {
        "expected_days": 1,
        "covered_days": 1,
        "missing_dates": [],
    }
    assert calendar_payload["provenance"] == (
        "calendar_events + daily_calendar_snapshots"
    )
