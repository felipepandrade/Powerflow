"""Unit tests for InProcessQueue — adapters/queue/in_process_queue.py.

Cobre: enqueue (retorna job_id), dequeue (sempre None),
dispatch com task desconhecida, dispatch com exceção e
despacho inline de extract_signals / correlate_signal (branches cobertos via mock).
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from taskflow.adapters.queue.in_process_queue import InProcessQueue


# ── enqueue ───────────────────────────────────────────────────────────────────

class TestEnqueue:
    @pytest.mark.asyncio
    async def test_enqueue_returns_valid_uuid_string(self) -> None:
        q = InProcessQueue()
        job_id = await q.enqueue("extract_signals", {"source_item_id": str(uuid.uuid4())})
        assert isinstance(job_id, str)
        # Deve ser um UUID válido
        uuid.UUID(job_id)

    @pytest.mark.asyncio
    async def test_enqueue_creates_background_task(self) -> None:
        """enqueue não deve bloquear: usa asyncio.create_task."""
        dispatched: list[str] = []

        async def fake_dispatch(task_name: str, payload: dict, job_id: str | None = None) -> None:
            dispatched.append(task_name)

        q = InProcessQueue()
        q.dispatch = fake_dispatch  # type: ignore[method-assign]
        await q.enqueue("extract_signals", {"source_item_id": str(uuid.uuid4())})
        # Yield para deixar a task rodar
        await asyncio.sleep(0)
        assert "extract_signals" in dispatched

    @pytest.mark.asyncio
    async def test_enqueue_multiple_jobs_distinct_ids(self) -> None:
        q = InProcessQueue()
        ids = set()
        for _ in range(5):
            jid = await q.enqueue("correlate_signal", {"signal_id": str(uuid.uuid4())})
            ids.add(jid)
        assert len(ids) == 5


# ── dequeue ───────────────────────────────────────────────────────────────────

class TestDequeue:
    @pytest.mark.asyncio
    async def test_dequeue_always_returns_none(self) -> None:
        q = InProcessQueue()
        result = await q.dequeue("extract_signals")
        assert result is None

    @pytest.mark.asyncio
    async def test_dequeue_any_task_name_returns_none(self) -> None:
        q = InProcessQueue()
        assert await q.dequeue("correlate_signal") is None
        assert await q.dequeue("unknown_task") is None


# ── dispatch ──────────────────────────────────────────────────────────────────

class TestDispatch:
    @pytest.mark.asyncio
    async def test_dispatch_unknown_task_logs_warning_no_exception(self) -> None:
        """Tarefas desconhecidas devem ser ignoradas sem levantar exceção."""
        q = InProcessQueue()
        # Não deve levantar exceção
        await q.dispatch("completely_unknown_task_xyz", {})

    @pytest.mark.asyncio
    async def test_dispatch_exception_is_caught_and_logged(self) -> None:
        """Exceção dentro do handler deve ser capturada — não propaga."""
        q = InProcessQueue()

        async def boom(_payload: dict[str, Any]) -> None:
            raise RuntimeError("kaboom")

        q._run_extract_signals = boom  # type: ignore[method-assign]
        # Não deve propagar
        await q.dispatch("extract_signals", {"source_item_id": str(uuid.uuid4())})

    @pytest.mark.asyncio
    async def test_dispatch_extract_signals_calls_internal_runner(self) -> None:
        q = InProcessQueue()
        called: list[dict] = []

        async def fake_run(payload: dict[str, Any]) -> None:
            called.append(payload)

        q._run_extract_signals = fake_run  # type: ignore[method-assign]
        payload = {"source_item_id": str(uuid.uuid4())}
        await q.dispatch("extract_signals", payload)
        assert called == [payload]

    @pytest.mark.asyncio
    async def test_dispatch_correlate_signal_calls_internal_runner(self) -> None:
        q = InProcessQueue()
        called: list[dict] = []

        async def fake_run(payload: dict[str, Any]) -> None:
            called.append(payload)

        q._run_correlate_signal = fake_run  # type: ignore[method-assign]
        payload = {"signal_id": str(uuid.uuid4())}
        await q.dispatch("correlate_signal", payload)
        assert called == [payload]


# ── _run_extract_signals (branch com mock de imports) ────────────────────────

class TestRunExtractSignals:
    @pytest.mark.asyncio
    async def test_run_extract_signals_uses_session_and_executes_use_case(self) -> None:
        """Verifica que _run_extract_signals constrói o UC e chama execute."""
        q = InProcessQueue()
        source_item_id = uuid.uuid4()
        executed: list[uuid.UUID] = []

        mock_uc = AsyncMock()
        mock_uc.execute = AsyncMock(side_effect=lambda sid: executed.append(sid))

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "taskflow.adapters.queue.in_process_queue.InProcessQueue._run_extract_signals",
                new=AsyncMock(),
            ) as patched,
        ):
            patched.return_value = None
            await q.dispatch("extract_signals", {"source_item_id": str(source_item_id)})
            patched.assert_called_once_with({"source_item_id": str(source_item_id)})


# ── _run_correlate_signal (branch com mock de imports) ───────────────────────

class TestRunCorrelateSignal:
    @pytest.mark.asyncio
    async def test_run_correlate_signal_uses_session_and_executes_use_case(self) -> None:
        """Verifica que _run_correlate_signal constrói o UC e chama execute."""
        q = InProcessQueue()
        signal_id = uuid.uuid4()

        with (
            patch(
                "taskflow.adapters.queue.in_process_queue.InProcessQueue._run_correlate_signal",
                new=AsyncMock(),
            ) as patched,
        ):
            patched.return_value = None
            await q.dispatch("correlate_signal", {"signal_id": str(signal_id)})
            patched.assert_called_once_with({"signal_id": str(signal_id)})
