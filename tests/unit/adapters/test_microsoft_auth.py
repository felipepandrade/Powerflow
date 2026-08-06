from __future__ import annotations

import json
from typing import Any

import pytest
from starlette.requests import Request

from taskflow.adapters.api.routers import auth_router
from taskflow.config.settings import Settings


class _FakeMsalApp:
    def __init__(self) -> None:
        self.auth_response: dict[str, str] | None = None

    def initiate_auth_code_flow(
        self,
        *,
        scopes: list[str],
        redirect_uri: str,
    ) -> dict[str, str]:
        assert "offline_access" not in scopes
        assert redirect_uri.endswith("/api/auth/callback")
        return {
            "state": "state-123",
            "auth_uri": "https://login.microsoftonline.com/authorize",
            "code_verifier": "verifier",
        }

    def acquire_token_by_auth_code_flow(
        self,
        flow: dict[str, Any],
        auth_response: dict[str, str],
    ) -> dict[str, str]:
        assert flow["state"] == "state-123"
        self.auth_response = auth_response
        return {"access_token": "must-never-be-returned"}

    def get_accounts(self) -> list[dict[str, str]]:
        return [{"home_account_id": "account"}]


def _request(query: bytes) -> Request:
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/api/auth/callback",
            "raw_path": b"/api/auth/callback",
            "query_string": query,
            "headers": [],
            "client": ("test", 123),
            "server": ("test", 80),
            "root_path": "",
        }
    )


@pytest.mark.asyncio
async def test_microsoft_login_persists_state_and_pkce_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(_env_file=None, APP_ENV="test", MS_CLIENT_ID="client")
    fake_app = _FakeMsalApp()
    saved: dict[str, str] = {}

    async def save(key: str, value: str) -> None:
        saved[key] = value

    async def load_cache() -> object:
        return object()

    monkeypatch.setattr(auth_router, "get_settings", lambda: settings)
    monkeypatch.setattr(auth_router, "_load_cache", load_cache)
    monkeypatch.setattr(auth_router, "_build_msal_app", lambda *_: fake_app)
    monkeypatch.setattr(auth_router, "save_credential", save)

    response = await auth_router.login()

    assert response.headers["location"].startswith("https://login.microsoftonline.com/")
    persisted = json.loads(saved["ms_graph_auth_flow:state-123"])
    assert persisted["code_verifier"] == "verifier"


@pytest.mark.asyncio
async def test_microsoft_callback_validates_saved_state_without_exposing_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(_env_file=None, APP_ENV="test", MS_CLIENT_ID="client")
    fake_app = _FakeMsalApp()
    deleted: list[str] = []

    async def get(key: str) -> str | None:
        assert key == "ms_graph_auth_flow:state-123"
        return json.dumps({"state": "state-123", "code_verifier": "verifier"})

    async def delete(key: str) -> None:
        deleted.append(key)

    async def load_cache() -> object:
        return object()

    async def persist_cache(_: object) -> None:
        return None

    monkeypatch.setattr(auth_router, "get_settings", lambda: settings)
    monkeypatch.setattr(auth_router, "get_credential", get)
    monkeypatch.setattr(auth_router, "delete_credential", delete)
    monkeypatch.setattr(auth_router, "_load_cache", load_cache)
    monkeypatch.setattr(auth_router, "_persist_cache", persist_cache)
    monkeypatch.setattr(auth_router, "_build_msal_app", lambda *_: fake_app)

    response = await auth_router.callback(
        _request(b"state=state-123&code=authorization-code"),
        state="state-123",
    )

    assert response.status_code == 307
    assert "must-never-be-returned" not in str(response.headers)
    assert deleted == ["ms_graph_auth_flow:state-123"]
    assert fake_app.auth_response == {
        "state": "state-123",
        "code": "authorization-code",
    }
