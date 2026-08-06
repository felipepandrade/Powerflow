import base64

import pytest
from pydantic import ValidationError

from taskflow.config.settings import Settings


def test_public_environment_rejects_development_encryption_key() -> None:
    with pytest.raises(ValidationError, match="ENCRYPTION_KEY"):
        Settings(
            _env_file=None,
            APP_ENV="cloud",
            ENCRYPTION_KEY="c29tZV9zZWNyZXRfa2V5XzMyX2J5dGVzX2xvbmdfMTIzNDU2Nzg=",
        )


def test_public_environment_accepts_explicit_secure_configuration() -> None:
    key = base64.urlsafe_b64encode(b"p" * 32).decode("ascii")
    settings = Settings(
        _env_file=None,
        APP_ENV="cloud",
        ENCRYPTION_KEY=key,
        CORS_ALLOWED_ORIGINS="https://powerflow.example",
    )

    assert settings.cors_allowed_origins == ["https://powerflow.example"]
    assert "offline_access" in settings.microsoft_scopes
