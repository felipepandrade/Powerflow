"""InProcessQueue — Fila em memória que executa tasks de extração e correlação inline.

No MVP local não há Redis ou Celery. Esta fila aceita tasks e as executa
diretamente de forma assíncrona, usando o banco de dados real via AsyncSession.
"""
from __future__ import annotations

import asyncio
import uuid
from typing import Any

import structlog

from taskflow.domain.ports.ports import Queue

log = structlog.get_logger()


class InProcessQueue(Queue):
    """Fila in-process que dispara as tasks de extração/correlação inline."""

    async def enqueue(
        self,
        task_name: str,
        payload: dict[str, Any],
        delay_seconds: int = 0,
    ) -> str:
        job_id = str(uuid.uuid4())
        log.info("queue.enqueue", task=task_name, job_id=job_id)

        # Agenda a execução assíncrona sem bloquear o chamador
        asyncio.create_task(
            self._dispatch(task_name, payload, job_id),
            name=f"queue_{task_name}_{job_id[:8]}"
        )
        return job_id

    async def dequeue(self, task_name: str) -> dict[str, Any] | None:
        return None  # Não aplicável — execução é inline

    async def _dispatch(
        self,
        task_name: str,
        payload: dict[str, Any],
        job_id: str,
    ) -> None:
        """Executa o handler da task de forma assíncrona."""
        try:
            if task_name == "extract_signals":
                await self._run_extract_signals(payload)
            elif task_name == "correlate_signal":
                await self._run_correlate_signal(payload)
            else:
                log.warning("queue.unknown_task", task=task_name)
        except Exception as e:
            log.error("queue.dispatch_error", task=task_name, job_id=job_id, error=str(e), exc_info=True)

    async def _run_extract_signals(self, payload: dict[str, Any]) -> None:
        """Executa ExtractSignalsUseCase com uma sessão de banco própria."""
        from taskflow.adapters.persistence.signal_repository import SqlAlchemySignalRepository
        from taskflow.adapters.persistence.unit_of_work import SqlAlchemyUnitOfWork
        from taskflow.application.use_cases.extract_signals import ExtractSignalsUseCase
        from taskflow.config.container import AsyncSessionLocal, create_background_llm_provider

        source_item_id = uuid.UUID(payload["source_item_id"])

        async with AsyncSessionLocal() as session:
            signal_repo = SqlAlchemySignalRepository(session)
            uow = SqlAlchemyUnitOfWork(session)
            llm = create_background_llm_provider()

            uc = ExtractSignalsUseCase(
                signal_repo=signal_repo,
                llm=llm,
                queue=InProcessQueue(),
                uow=uow,
            )
            await uc.execute(source_item_id)
            log.info("queue.extract_signals.done", source_item_id=str(source_item_id))

    async def _run_correlate_signal(self, payload: dict[str, Any]) -> None:
        """Executa CorrelateSignalUseCase com uma sessão de banco própria."""
        from taskflow.adapters.llm.factory import create_embedding_provider
        from taskflow.adapters.persistence.signal_repository import SqlAlchemySignalRepository
        from taskflow.adapters.persistence.task_repository import SqlAlchemyTaskRepository
        from taskflow.adapters.persistence.unit_of_work import SqlAlchemyUnitOfWork
        from taskflow.application.use_cases.correlate_signal import CorrelateSignalUseCase
        from taskflow.config.container import AsyncSessionLocal, create_background_llm_provider
        from taskflow.config.settings import get_settings

        signal_id = uuid.UUID(payload["signal_id"])
        s = get_settings()

        async with AsyncSessionLocal() as session:
            signal_repo = SqlAlchemySignalRepository(session)
            task_repo = SqlAlchemyTaskRepository(session)
            uow = SqlAlchemyUnitOfWork(session)
            llm = create_background_llm_provider()
            embedder = create_embedding_provider(
                provider_type=s.EMBEDDING_PROVIDER,
                api_key=s.GEMINI_API_KEY,
            )

            uc = CorrelateSignalUseCase(
                uow=uow,
                task_repo=task_repo,
                signal_repo=signal_repo,
                llm=llm,
                embedder=embedder,
            )
            await uc.execute(signal_id)
            log.info("queue.correlate_signal.done", signal_id=str(signal_id))
