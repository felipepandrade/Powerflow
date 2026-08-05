"""Testes de integração para os endpoints de Alertas e Registro de Decisões."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_alerts_and_decisions_endpoints(async_client: AsyncClient) -> None:
    # 1. Buscar Alertas
    alerts_resp = await async_client.get("/api/alerts")
    assert alerts_resp.status_code == 200
    alerts = alerts_resp.json()
    assert isinstance(alerts, list)

    if len(alerts) > 0:
        alert_id = alerts[0]["id"]
        ack_resp = await async_client.post(f"/api/alerts/{alert_id}/acknowledge")
        assert ack_resp.status_code == 200

    # 2. Registrar Decisão Gerencial
    dec_resp = await async_client.post(
        "/api/decisions",
        json={
            "title": "Redução do limite de WIP",
            "decision_text": "Limitado o WIP máximo por projeto a 5 tarefas para destravar gargalo de testes.",
            "rationale": "Métrica flow.wip estava acima do limite crítico de 5.0 tarefas.",
            "expected_impact": "Redução prevista do Lead Time p85 em 25%.",
        },
    )
    assert dec_resp.status_code == 201
    assert dec_resp.json()["status"] == "success"

    # 3. Listar Decisões Registradas
    list_dec = await async_client.get("/api/decisions")
    assert list_dec.status_code == 200
    assert len(list_dec.json()) >= 1
