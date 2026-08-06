from taskflow.config.logging import redact_sensitive_data


def test_structured_logging_redacts_keys_and_secret_values() -> None:
    event = {
        "event": "provider failed for secret-value",
        "access_token": "token-value",
        "nested": {"api_key": "key-value", "safe": "secret-value"},
    }

    redacted = redact_sensitive_data(
        None,
        "error",
        event,
        secrets=("secret-value",),
    )

    assert redacted == {
        "event": "provider failed for [REDACTED]",
        "access_token": "[REDACTED]",
        "nested": {"api_key": "[REDACTED]", "safe": "[REDACTED]"},
    }
