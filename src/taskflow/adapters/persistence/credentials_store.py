"""Encrypted persistence for application credentials."""

from __future__ import annotations

import base64
import binascii
import hashlib
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from taskflow.adapters.persistence.models import CredentialORM
from taskflow.config.settings import Settings, get_settings


class CredentialCipher:
    """Versioned AES-GCM envelope encryption with per-record associated data."""

    _PREFIX = "enc:v1:"

    def __init__(self, encryption_key: str) -> None:
        try:
            decoded = base64.urlsafe_b64decode(encryption_key.encode("ascii"))
        except (binascii.Error, ValueError, UnicodeEncodeError) as exc:
            raise ValueError("ENCRYPTION_KEY must be URL-safe base64") from exc
        if len(decoded) not in {16, 24, 32}:
            decoded = hashlib.sha256(decoded).digest()
        self._cipher = AESGCM(decoded)

    def encrypt(self, credential_key: str, plaintext: str) -> str:
        nonce = os.urandom(12)
        ciphertext = self._cipher.encrypt(
            nonce,
            plaintext.encode("utf-8"),
            credential_key.encode("utf-8"),
        )
        payload = base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")
        return f"{self._PREFIX}{payload}"

    def decrypt(self, credential_key: str, envelope: str) -> str:
        if not envelope.startswith(self._PREFIX):
            raise ValueError("Credential is not stored in a protected envelope")
        payload = envelope.removeprefix(self._PREFIX)
        try:
            raw = base64.urlsafe_b64decode(payload.encode("ascii"))
            plaintext = self._cipher.decrypt(
                raw[:12],
                raw[12:],
                credential_key.encode("utf-8"),
            )
            return plaintext.decode("utf-8")
        except (binascii.Error, InvalidTag, UnicodeError, ValueError) as exc:
            raise ValueError("Credential envelope is invalid") from exc


class EncryptedCredentialStore:
    """Persist credentials encrypted at rest using an injected session factory."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        settings: Settings,
    ) -> None:
        self._session_factory = session_factory
        self._cipher = CredentialCipher(settings.ENCRYPTION_KEY)

    async def save(self, key: str, value: str) -> None:
        encrypted = self._cipher.encrypt(key, value)
        async with self._session_factory() as session:
            result = await session.execute(select(CredentialORM).where(CredentialORM.key == key))
            credential = result.scalar_one_or_none()
            if credential is None:
                session.add(CredentialORM(key=key, value=encrypted))
            else:
                credential.value = encrypted
            await session.commit()

    async def get(self, key: str) -> str | None:
        async with self._session_factory() as session:
            result = await session.execute(select(CredentialORM).where(CredentialORM.key == key))
            credential = result.scalar_one_or_none()
            if credential is None:
                return None
            return self._cipher.decrypt(key, credential.value)

    async def delete(self, key: str) -> None:
        async with self._session_factory() as session:
            credential = await session.get(CredentialORM, key)
            if credential is not None:
                await session.delete(credential)
                await session.commit()



def _default_store() -> EncryptedCredentialStore:
    from taskflow.config.container import AsyncSessionLocal

    return EncryptedCredentialStore(AsyncSessionLocal, get_settings())


async def save_credential(key: str, value: str) -> None:
    """Save a protected credential through the production composition root."""
    await _default_store().save(key, value)


async def get_credential(key: str) -> str | None:
    """Read and decrypt a credential without exposing its persisted envelope."""
    return await _default_store().get(key)


async def delete_credential(key: str) -> None:
    """Delete an encrypted credential envelope."""
    await _default_store().delete(key)
