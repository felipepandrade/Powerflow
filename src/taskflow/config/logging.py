import logging
import sys
from functools import partial
from typing import Any, cast

import structlog

from taskflow.config.settings import get_settings

_SENSITIVE_KEY_PARTS = ("token", "secret", "password", "api_key", "authorization")


def _redact_value(value: object, secrets: tuple[str, ...]) -> object:
    if isinstance(value, dict):
        return {
            str(key): (
                "[REDACTED]"
                if any(part in str(key).lower() for part in _SENSITIVE_KEY_PARTS)
                else _redact_value(item, secrets)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_value(item, secrets) for item in value]
    if isinstance(value, str):
        redacted = value
        for secret in secrets:
            redacted = redacted.replace(secret, "[REDACTED]")
        return redacted
    return value


def redact_sensitive_data(
    _: Any,
    __: str,
    event_dict: structlog.types.EventDict,
    *,
    secrets: tuple[str, ...],
) -> structlog.types.EventDict:
    return cast(structlog.types.EventDict, _redact_value(event_dict, secrets))

def configure_logging() -> None:
    """Configura o sistema de logging estruturado com structlog."""
    settings = get_settings()
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    secrets = tuple(
        secret
        for secret in (
            settings.ENCRYPTION_KEY,
            settings.MS_CLIENT_SECRET,
            settings.GEMINI_API_KEY,
        )
        if len(secret) >= 8
    )
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        partial(redact_sensitive_data, secrets=secrets),
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.APP_ENV == "cloud":
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors + [renderer],
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
