"""Testes para o fluxo OAuth PKCE do ChatGPT/OpenAI e provider de assinatura."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any
import pytest
import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from taskflow.adapters.api.routers.oauth_openai import PKCE_SESSIONS
from taskflow.adapters.llm.chatgpt_subscription import (
    ChatGPTSubscriptionLLMProvider,
    generate_pkce_pair,
)
from taskflow.adapters.persistence.models import Base, SyncStateORM
from taskflow.config.container import get_db_session
from taskflow.main import app


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        async def _override():
            yield s

        app.dependency_overrides[get_db_session] = _override
        yield s
        app.dependency_overrides.pop(get_db_session, None)


class TestPKCEHelper:
    def test_generate_pkce_pair_returns_valid_tokens(self) -> None:
        verifier, challenge = generate_pkce_pair()
        assert isinstance(verifier, str) and len(verifier) > 40
        assert isinstance(challenge, str) and len(challenge) > 20
        assert verifier != challenge


class TestOpenAIOAuthEndpoints:
    def test_login_endpoint_returns_auth_url_and_state(self) -> None:
        client = TestClient(app)
        response = client.get("/api/auth/openai-subscription/login")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "auth0.openai.com/authorize" in data["auth_url"]
        assert "client_id=p267s40a" in data["auth_url"]
        assert data["state"] in PKCE_SESSIONS

    @pytest.mark.asyncio
    async def test_callback_saves_tokens_to_db(self, async_client: httpx.AsyncClient, db_session: AsyncSession) -> None:
        state_key = "test_state_123"
        PKCE_SESSIONS[state_key] = "test_verifier"

        response = await async_client.get(
            "/api/auth/openai-subscription/callback",
            params={"code": "test_auth_code_xyz", "state": state_key},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        # Verificar se foi salvo no DB
        stmt = select(SyncStateORM).where(
            SyncStateORM.channel == "openai_subscription",
            SyncStateORM.resource_id == "chatgpt_user",
        )
        res = await db_session.execute(stmt)
        record = res.scalar_one_or_none()
        assert record is not None
        assert record.state == "healthy"
        assert "chatgpt_sub_at_" in record.delta_link

    @pytest.mark.asyncio
    async def test_status_endpoint_returns_connection_state(
        self, async_client: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        # Inicialmente limpo ou desconectado
        response = await async_client.get("/api/auth/openai-subscription/status")
        assert response.status_code == 200
        assert "is_connected" in response.json()


class TestChatGPTSubscriptionLLMProvider:
    @pytest.mark.asyncio
    async def test_extract_without_token_raises_value_error(self) -> None:
        provider = ChatGPTSubscriptionLLMProvider()
        with pytest.raises(ValueError, match="Nenhum token de acesso do ChatGPT configurado"):
            await provider.extract("Algum texto")

    @pytest.mark.asyncio
    async def test_classify_returns_confidence(self) -> None:
        provider = ChatGPTSubscriptionLLMProvider(access_token="fake_token")
        result = await provider.classify("Reunião amanhã 15h", {})
        assert result["has_actionable_commitment"] is True
        assert result["confidence"] == 0.9
