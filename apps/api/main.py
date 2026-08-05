from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from apps.api.routers.health import router as health_router
from taskflow.config.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gerencia ciclo de vida da aplicação FastAPI."""
    configure_logging()
    yield


def create_app() -> FastAPI:
    """Factory de inicialização da aplicação FastAPI."""
    app = FastAPI(
        title="TaskFlow API",
        description="Sistema Pessoal de Captura Autônoma e Gestão Correlacionada de Tarefas",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.include_router(health_router)
    return app


app = create_app()
