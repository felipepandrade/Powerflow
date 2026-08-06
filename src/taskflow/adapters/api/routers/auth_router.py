"""Microsoft Entra ID authorization-code flow with state, PKCE, and protected cache."""

from __future__ import annotations

import json
import logging
from typing import Any, cast

import msal
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from taskflow.adapters.persistence.credentials_store import (
    delete_credential,
    get_credential,
    save_credential,
)
from taskflow.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["Auth"])

_TOKEN_CACHE_KEY = "ms_graph_token_cache"
_FLOW_KEY_PREFIX = "ms_graph_auth_flow:"
_RESERVED_SCOPES = {"openid", "profile", "offline_access"}


def _requested_scopes(settings: Settings) -> list[str]:
    """MSAL adds OIDC reserved scopes itself; Graph scopes remain explicit."""
    return [scope for scope in settings.microsoft_scopes if scope.lower() not in _RESERVED_SCOPES]


def _build_msal_app(
    settings: Settings,
    cache: msal.SerializableTokenCache,
) -> msal.PublicClientApplication:
    authority = f"https://login.microsoftonline.com/{settings.MS_TENANT_ID}"
    return msal.PublicClientApplication(
        settings.MS_CLIENT_ID,
        authority=authority,
        token_cache=cache,
    )


async def _load_cache() -> msal.SerializableTokenCache:
    cache = msal.SerializableTokenCache()
    serialized = await get_credential(_TOKEN_CACHE_KEY)
    if serialized:
        cache.deserialize(serialized)
    return cache


async def _persist_cache(cache: msal.SerializableTokenCache) -> None:
    if cache.has_state_changed:
        await save_credential(_TOKEN_CACHE_KEY, cache.serialize())


@router.get("/login")
async def login() -> RedirectResponse:
    """Start a state-bound authorization-code flow; MSAL supplies PKCE."""
    settings = get_settings()
    if not settings.MS_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Microsoft authentication is not configured")

    cache = await _load_cache()
    app = _build_msal_app(settings, cache)
    raw_flow = app.initiate_auth_code_flow(
        scopes=_requested_scopes(settings),
        redirect_uri=settings.MS_REDIRECT_URI,
    )
    flow = cast(dict[str, Any], raw_flow)
    state = str(flow.get("state", ""))
    auth_uri = str(flow.get("auth_uri", ""))
    if not state or not auth_uri:
        logger.error("microsoft_auth.flow_initialization_failed")
        raise HTTPException(status_code=503, detail="Microsoft authentication is unavailable")

    await save_credential(f"{_FLOW_KEY_PREFIX}{state}", json.dumps(flow))
    return RedirectResponse(auth_uri)


@router.get("/callback")
async def callback(request: Request, state: str | None = None) -> RedirectResponse:
    """Complete the state/PKCE flow without returning or logging credentials."""
    if not state:
        raise HTTPException(status_code=400, detail="Invalid authentication state")

    settings = get_settings()
    flow_key = f"{_FLOW_KEY_PREFIX}{state}"
    serialized_flow = await get_credential(flow_key)
    if serialized_flow is None:
        raise HTTPException(status_code=400, detail="Invalid or expired authentication state")

    cache = await _load_cache()
    app = _build_msal_app(settings, cache)
    try:
        flow = cast(dict[str, Any], json.loads(serialized_flow))
        raw_result = app.acquire_token_by_auth_code_flow(flow, dict(request.query_params))
        result = cast(dict[str, Any], raw_result)
    except (ValueError, json.JSONDecodeError):
        logger.warning("microsoft_auth.callback_rejected")
        raise HTTPException(status_code=400, detail="Microsoft authentication failed") from None
    finally:
        await delete_credential(flow_key)

    if "error" in result:
        logger.warning("microsoft_auth.provider_rejected", extra={"error": result.get("error")})
        raise HTTPException(status_code=400, detail="Microsoft authentication failed")

    await _persist_cache(cache)
    return RedirectResponse(settings.FRONTEND_AUTH_SUCCESS_URL)


@router.get("/status")
async def auth_status() -> dict[str, Any]:
    """Expose connection metadata only; never tokens or provider exception details."""
    settings = get_settings()
    cache = await _load_cache()
    app = _build_msal_app(settings, cache)
    accounts = cast(list[dict[str, Any]], app.get_accounts())
    return {
        "connected": bool(accounts),
        "account_count": len(accounts),
        "scopes": settings.microsoft_scopes,
    }
