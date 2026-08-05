"""Testes de integração para a API de estrutura organizacional."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_org_endpoints(async_client: AsyncClient) -> None:
    # 1. Criar e listar Área
    area_resp = await async_client.post("/api/org/areas", json={"name": "Engenharia", "kind": "own_team", "is_own_team": True})
    assert area_resp.status_code == 201
    area_data = area_resp.json()
    assert area_data["name"] == "Engenharia"

    areas_list = await async_client.get("/api/org/areas")
    assert areas_list.status_code == 200
    assert len(areas_list.json()) >= 1

    # 2. Criar e listar Portfólio
    port_resp = await async_client.post("/api/org/portfolios", json={"name": "Estratégia 2026"})
    assert port_resp.status_code == 201
    port_data = port_resp.json()

    # 3. Criar e listar Projeto
    proj_resp = await async_client.post("/api/org/projects", json={"name": "PowerFlow SaaS", "portfolio_id": port_data["id"]})
    assert proj_resp.status_code == 201
    proj_data = proj_resp.json()

    # 4. Criar e listar Marco
    ms_resp = await async_client.post("/api/org/milestones", json={"project_id": proj_data["id"], "name": "Sprint 1", "target_date": "2026-08-30"})
    assert ms_resp.status_code == 201

    ms_list = await async_client.get(f"/api/org/projects/{proj_data['id']}/milestones")
    assert ms_list.status_code == 200
    assert len(ms_list.json()) == 1

    import uuid
    unique_email = f"carlos_{uuid.uuid4().hex[:6]}@example.com"
    st_resp = await async_client.post("/api/org/stakeholders", json={"display_name": "Carlos Souza", "email": unique_email, "area_id": area_data["id"]})
    assert st_resp.status_code == 201
