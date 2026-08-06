"""ASGI compatibility entrypoint for the shared Powerflow composition root."""

from taskflow.main import app, create_app

__all__ = ["app", "create_app"]
