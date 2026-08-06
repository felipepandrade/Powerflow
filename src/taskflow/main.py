"""Production composition root shared by local execution and containers."""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from taskflow.adapters.api.routers import (
    alerts_router,
    analytics_router,
    auth_router,
    oauth_openai,
    org_router,
    reports_router,
    signals_router,
    system_router,
    tasks_router,
    webhook_router,
)
from taskflow.config.container import engine
from taskflow.config.logging import configure_logging
from taskflow.config.settings import get_settings

logger = logging.getLogger(__name__)
_VERSION = "0.1.0"


def _problem(
    request: Request,
    *,
    status: int,
    title: str,
    detail: str,
    problem_type: str = "about:blank",
    extensions: dict[str, Any] | None = None,
) -> JSONResponse:
    payload: dict[str, Any] = {
        "type": problem_type,
        "title": title,
        "status": status,
        "detail": detail,
        "instance": request.url.path,
    }
    if extensions:
        payload.update(extensions)
    return JSONResponse(payload, status_code=status, media_type="application/problem+json")


async def _cancel_tasks(tasks: list[asyncio.Task[None]]) -> None:
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize only environment-safe services; schema is managed by Alembic."""
    configure_logging()
    settings = get_settings()
    background_tasks: list[asyncio.Task[None]] = []

    if settings.ENABLE_LOCAL_WINDOWS_WATCHERS:
        if settings.APP_ENV.lower() not in {"local", "test"} or os.name != "nt":
            raise RuntimeError("Local Windows watchers require local/test mode on Windows")
        from taskflow.adapters.workers.outlook_watcher import watch_outlook
        from taskflow.adapters.workers.teams_watcher import watch_teams

        interval = max(settings.SYNC_INTERVAL_MINUTES * 60, 30)
        background_tasks.extend(
            [
                asyncio.create_task(watch_outlook(interval_seconds=interval)),
                asyncio.create_task(watch_teams(interval_seconds=interval)),
            ]
        )

    try:
        yield
    finally:
        await _cancel_tasks(background_tasks)
        await engine.dispose()


def create_app() -> FastAPI:
    """Build the single HTTP application used by every runtime entrypoint."""
    settings = get_settings()
    application = FastAPI(
        title="Powerflow API",
        description="Reliable personal workflow and managerial analytics",
        version=_VERSION,
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-LLM-Provider", "X-LLM-API-Key"],
    )

    routers = (
        signals_router.router,
        tasks_router.router,
        system_router.router,
        auth_router.router,
        webhook_router.router,
        org_router.router,
        analytics_router.router,
        alerts_router.router,
        reports_router.router,
        oauth_openai.router,
    )
    for router in routers:
        application.include_router(router)

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        invalid_params = [
            {"location": ".".join(str(part) for part in error["loc"]), "code": error["type"]}
            for error in exc.errors()
        ]
        return _problem(
            request,
            status=422,
            title="Request validation failed",
            detail="One or more request fields are invalid.",
            extensions={"invalid_params": invalid_params},
        )

    @application.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code >= 500:
            safe_detail = "The request could not be completed."
        else:
            safe_detail = (
                exc.detail if isinstance(exc.detail, str) else "Request could not be completed."
            )
        return _problem(
            request,
            status=exc.status_code,
            title="Request failed",
            detail=safe_detail,
        )

    @application.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, _: Exception) -> JSONResponse:
        logger.error("api.unhandled_error", extra={"path": request.url.path})
        return _problem(
            request,
            status=500,
            title="Internal server error",
            detail="The request could not be completed.",
        )

    @application.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "ok", "version": _VERSION}

    @application.get("/health/live")
    async def health_live() -> dict[str, str]:
        return {"status": "alive", "env": settings.APP_ENV, "version": _VERSION}

    @application.get("/health/ready")
    async def health_ready(request: Request) -> dict[str, Any]:
        try:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except SQLAlchemyError:
            logger.warning("health.database_unavailable")
            raise HTTPException(status_code=503, detail="Database is unavailable") from None
        return {
            "status": "ready",
            "env": settings.APP_ENV,
            "version": _VERSION,
            "dependencies": {"database": "ready"},
        }

    return application


app = create_app()
