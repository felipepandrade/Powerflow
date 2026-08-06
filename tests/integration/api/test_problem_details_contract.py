import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_not_found_uses_stable_problem_details(async_client: AsyncClient) -> None:
    response = await async_client.get("/route-that-does-not-exist")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json() == {
        "type": "about:blank",
        "title": "Request failed",
        "status": 404,
        "detail": "Not Found",
        "instance": "/route-that-does-not-exist",
    }


@pytest.mark.asyncio
async def test_readiness_checks_database(async_client: AsyncClient) -> None:
    response = await async_client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["dependencies"] == {"database": "ready"}
