from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from taskflow.config.container import Container, get_container

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    env: str
    version: str = "0.1.0"


@router.get("/health/live", response_model=HealthResponse)
async def health_live(container: Container = Depends(get_container)) -> dict[str, Any]:
    """Endpoint Liveness para checagem rápida de integridade da API."""
    return {
        "status": "alive",
        "env": container.settings.APP_ENV,
        "version": "0.1.0",
    }


@router.get("/health/ready", response_model=HealthResponse)
async def health_ready(container: Container = Depends(get_container)) -> dict[str, Any]:
    """Endpoint Readiness para checagem de prontidão do serviço."""
    return {
        "status": "ready",
        "env": container.settings.APP_ENV,
        "version": "0.1.0",
    }
