from __future__ import annotations

import base64

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from taskflow.adapters.persistence.credentials_store import (
    CredentialCipher,
    EncryptedCredentialStore,
)
from taskflow.adapters.persistence.models import Base, CredentialORM
from taskflow.config.settings import Settings


def _settings() -> Settings:
    key = base64.urlsafe_b64encode(b"k" * 32).decode("ascii")
    return Settings(_env_file=None, APP_ENV="test", ENCRYPTION_KEY=key)


def test_credential_cipher_binds_ciphertext_to_record_key() -> None:
    cipher = CredentialCipher(_settings().ENCRYPTION_KEY)
    envelope = cipher.encrypt("graph", "super-secret")

    assert "super-secret" not in envelope
    assert cipher.decrypt("graph", envelope) == "super-secret"
    with pytest.raises(ValueError):
        cipher.decrypt("different-key", envelope)


@pytest.mark.asyncio
async def test_credential_store_never_persists_plaintext() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    store = EncryptedCredentialStore(factory, _settings())
    await store.save("ms_graph_token_cache", "token-material")

    async with factory() as session:
        result = await session.execute(
            select(CredentialORM).where(CredentialORM.key == "ms_graph_token_cache")
        )
        persisted = result.scalar_one()
        assert persisted.value.startswith("enc:v1:")
        assert "token-material" not in persisted.value

    assert await store.get("ms_graph_token_cache") == "token-material"
    await store.delete("ms_graph_token_cache")
    assert await store.get("ms_graph_token_cache") is None
    await engine.dispose()
