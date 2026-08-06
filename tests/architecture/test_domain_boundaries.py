from __future__ import annotations

import ast
from pathlib import Path

DOMAIN_ROOT = Path("src/taskflow/domain")
FORBIDDEN_PREFIXES = (
    "taskflow.adapters",
    "taskflow.application",
    "taskflow.config",
    "fastapi",
    "sqlalchemy",
    "httpx",
    "google",
    "msal",
)


def test_domain_has_no_io_or_outer_layer_imports() -> None:
    violations: list[str] = []

    for path in DOMAIN_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module)
            for module in modules:
                if module.startswith(FORBIDDEN_PREFIXES):
                    violations.append(f"{path}:{node.lineno} imports {module}")

    assert violations == []
