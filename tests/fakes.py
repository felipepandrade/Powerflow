"""Implementações in-memory das portas de domínio para testes.

NUNCA usadas em produção. Apenas em tests/.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from taskflow.domain.ports.ports import (
    Clock,
    EmbeddingProvider,
    LLMProvider,
    Queue,
    SignalRepository,
    TaskRepository,
    UnitOfWork,
)


class FakeTaskRepository(TaskRepository):
    """Repositório de tarefas em memória."""

    def __init__(self) -> None:
        self._tasks: dict[uuid.UUID, Any] = {}

    async def get_by_id(self, task_id: uuid.UUID) -> Any | None:
        return self._tasks.get(task_id)

    async def save(self, task: Any) -> None:
        self._tasks[task.id] = task

    async def find_active(
        self,
        status_filter: list[str] | None = None,
        limit: int = 100,
    ) -> Sequence[Any]:
        results = list(self._tasks.values())
        if status_filter:
            results = [t for t in results if t.status.value in status_filter]
        return results[:limit]

    async def search_full_text(self, query: str, limit: int = 20) -> Sequence[Any]:
        q = query.lower()
        return [t for t in self._tasks.values() if q in t.title.lower()][:limit]

    async def find_by_embedding(
        self, embedding: list[float], top_k: int = 8
    ) -> Sequence[Any]:
        # Retorna todos (sem similaridade real em testes)
        return list(self._tasks.values())[:top_k]


class FakeSignalRepository(SignalRepository):
    """Repositório de sinais e artefatos auxiliares em memória."""

    def __init__(self) -> None:
        self._items: list[Any] = []

    async def save(self, signal: Any) -> None:
        # Atualiza se já existe
        for i, item in enumerate(self._items):
            if item.id == signal.id:
                self._items[i] = signal
                return
        self._items.append(signal)

    async def get_pending(self, limit: int = 50) -> Sequence[Any]:
        from taskflow.domain.value_objects.enums import ProposalStatus, SignalState
        return [
            s for s in self._items
            if (hasattr(s, "state") and s.state == SignalState.PENDING_CORRELATION)
            or (hasattr(s, "status") and s.status == ProposalStatus.PENDING)
        ][:limit]

    async def get_source_item_by_id(self, item_id: uuid.UUID) -> Any | None:
        for item in self._items:
            if item.id == item_id:
                return item
        return None

    async def save_correlation_run(self, run: Any) -> None:
        self._items.append(run)

    async def get_orphan_signals(
        self, since: datetime, limit: int = 100
    ) -> Sequence[Any]:
        from taskflow.domain.value_objects.enums import SignalState
        return [
            s for s in self._items
            if hasattr(s, "state")
            and s.state == SignalState.PENDING_CORRELATION
            and hasattr(s, "created_at")
            and s.created_at <= since
        ][:limit]


class FakeUnitOfWork(UnitOfWork):
    """Unit of Work em memória — sem transações reais."""

    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> FakeUnitOfWork:
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class FakeQueue(Queue):
    """Fila em memória para testes."""

    def __init__(self) -> None:
        self._jobs: list[dict[str, Any]] = []

    async def enqueue(
        self,
        task_name: str,
        payload: dict[str, Any],
        delay_seconds: int = 0,
    ) -> str:
        job_id = str(uuid.uuid4())
        self._jobs.append({"id": job_id, "task": task_name, "payload": payload})
        return job_id

    async def dequeue(self, task_name: str) -> dict[str, Any] | None:
        for i, job in enumerate(self._jobs):
            if job["task"] == task_name:
                return self._jobs.pop(i)
        return None

    @property
    def queued(self) -> list[dict[str, Any]]:
        return list(self._jobs)


class FakeLLMProvider(LLMProvider):
    """Provedor de LLM determinístico para testes."""

    def __init__(
        self,
        classify_response: dict[str, Any] | None = None,
        extract_response: dict[str, Any] | None = None,
        correlate_response: dict[str, Any] | None = None,
        follow_up_body: str = "Por favor, poderia atualizar o status?",
    ) -> None:
        self._classify = classify_response or {"has_commitment": False}
        self._extract = extract_response or {"signals": []}
        self._correlate = correlate_response or {"assessments": []}
        self._follow_up_body = follow_up_body
        self.calls: list[dict[str, Any]] = []

    async def classify(self, text: str, context: dict[str, Any]) -> dict[str, Any]:
        self.calls.append({"method": "classify", "text": text})
        return self._classify

    async def extract(self, text: str, context: dict[str, Any]) -> dict[str, Any]:
        self.calls.append({"method": "extract", "text": text})
        return self._extract

    async def correlate(
        self, signal: dict[str, Any], candidates: list[dict[str, Any]]
    ) -> dict[str, Any]:
        self.calls.append({"method": "correlate", "signal": signal})
        return self._correlate

    async def draft_follow_up(
        self, task: dict[str, Any], context: dict[str, Any], tone: str
    ) -> str:
        self.calls.append({"method": "draft_follow_up", "task": task})
        return self._follow_up_body


class FakeEmbeddingProvider(EmbeddingProvider):
    """Provedor de embeddings determinístico para testes."""

    def __init__(self, dimension: int = 384) -> None:
        self._dim = dimension
        self.calls: int = 0

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls += len(texts)
        # Retorna vetor constante para testes determinísticos
        return [[0.1] * self._dim for _ in texts]


class FakeClock(Clock):
    """Relógio controlado para testes determinísticos."""

    def __init__(self, fixed_time: datetime | None = None) -> None:
        self._time = fixed_time or datetime(2026, 8, 4, 10, 0, 0)

    def now(self) -> datetime:
        return self._time

    def advance(self, **kwargs: Any) -> None:
        """Avança o relógio — aceita argumentos como timedelta."""
        from datetime import timedelta
        self._time += timedelta(**kwargs)
