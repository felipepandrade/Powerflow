import re
from pathlib import Path

# 1. unit_of_work.py
p_uow = Path("src/taskflow/adapters/persistence/unit_of_work.py")
content = p_uow.read_text("utf-8")
content = content.replace(
    "async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:",
    "async def __aexit__(self, *args: object) -> None:"
)
p_uow.write_text(content, "utf-8")

# 2. task_repository.py
p_task = Path("src/taskflow/adapters/persistence/task_repository.py")
content = p_task.read_text("utf-8")
content = content.replace("from datetime import date", "")
content = "from datetime import date\n" + content
content = content.replace(
    "project_id=orm.project_id,\n            due_date=orm.due_date,\n            completed_at=orm.completed_at,",
    "project_id=orm.project_id,\n            due_date=date.fromisoformat(orm.due_date) if orm.due_date else None,\n            completed_at=orm.completed_at,"
)
content = content.replace(
    "priority=task.priority.value,\n            project_id=task.project_id,\n            created_at=task.created_at,",
    "priority=task.priority.value,\n            project_id=task.project_id,\n            due_date=task.due_date.isoformat() if task.due_date else None,\n            created_at=task.created_at,"
)
p_task.write_text(content, "utf-8")

# 3. signal_repository.py
p_sig = Path("src/taskflow/adapters/persistence/signal_repository.py")
content = p_sig.read_text("utf-8")
content = content.replace("SignalState.ORPHAN.value", "SignalState.PENDING_CORRELATION.value")
p_sig.write_text(content, "utf-8")

# 4. test_persistence.py
p_test = Path("tests/integration/adapters/test_persistence.py")
content = p_test.read_text("utf-8")
content = content.replace("from sqlalchemy.orm import sessionmaker", "from sqlalchemy.ext.asyncio import async_sessionmaker")
content = content.replace("from typing import AsyncGenerator\n", "")
content = "from typing import AsyncGenerator\n" + content
content = content.replace(
    "async def async_session() -> AsyncSession:",
    "async def async_session() -> AsyncGenerator[AsyncSession, None]:"
)
content = content.replace(
    "TestingSessionLocal = sessionmaker(\n        engine, expire_on_commit=False, class_=AsyncSession\n    )",
    "TestingSessionLocal = async_sessionmaker(engine, expire_on_commit=False)"
)
p_test.write_text(content, "utf-8")

# 5. ollama_provider.py
p_ollama = Path("src/taskflow/adapters/llm/ollama_provider.py")
content = p_ollama.read_text("utf-8")
content = content.replace("from typing import Any", "from typing import Any, cast")
content = content.replace("return json.loads(data.get(\"response\", \"{}\"))", "return cast(dict[str, Any], json.loads(data.get(\"response\", \"{}\")))")
content = content.replace("return data.get(\"response\", \"\")", "return str(data.get(\"response\", \"\"))")
p_ollama.write_text(content, "utf-8")

# 6. gemini_provider.py
p_gemini = Path("src/taskflow/adapters/llm/gemini_provider.py")
content = p_gemini.read_text("utf-8")
content = content.replace("from typing import Any", "from typing import Any, cast")
content = content.replace("return json.loads(response.text)", "return cast(dict[str, Any], json.loads(response.text or \"{}\"))")
content = content.replace("return [emb.values for emb in response.embeddings]", "return [emb.values for emb in response.embeddings] if response.embeddings else []")
p_gemini.write_text(content, "utf-8")

# 7. test_llm.py
p_tllm = Path("tests/integration/adapters/test_llm.py")
content = p_tllm.read_text("utf-8")
content = content.replace("def raise_for_status(self): pass", "def raise_for_status(self) -> None: pass")
content = content.replace("def json(self): return", "def json(self) -> dict: return")
p_tllm.write_text(content, "utf-8")

print("Fixed typings.")
