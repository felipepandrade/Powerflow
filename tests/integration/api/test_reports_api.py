"""Testes de integração para Relatórios, Entrada Manual e Import/Export CSV."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_reports_and_import_export_endpoints(async_client: AsyncClient) -> None:
    # 1. Gerar Relatório One-Pager
    op_resp = await async_client.get("/api/reports/one-pager")
    assert op_resp.status_code == 200
    assert "markdown" in op_resp.json()

    # 2. Inserir Métrica Manual (Épico K)
    man_resp = await async_client.post(
        "/api/reports/manual-metric",
        json={
            "metric_id": "manual.satisfacao_time",
            "value": 9.5,
            "note": "Pesquisa quinzenal de clima e satisfação",
        },
    )
    assert man_resp.status_code == 201
    assert man_resp.json()["metric_id"] == "manual.satisfacao_time"

    # 3. Exportar Tarefas em CSV
    exp_resp = await async_client.get("/api/reports/export/csv")
    assert exp_resp.status_code == 200
    assert "text/csv" in exp_resp.headers["content-type"]
    assert "id,title,status,priority" in exp_resp.text

    # 4. Importar Tarefas via CSV
    csv_file_content = "title,description,status,priority\nTarefa Importada Teste,Descrição Importada,inbox,high\n"
    files = {"file": ("tasks_import.csv", csv_file_content, "text/csv")}
    imp_resp = await async_client.post("/api/reports/import/csv", files=files)
    assert imp_resp.status_code == 200
    assert imp_resp.json()["imported_tasks"] == 1
