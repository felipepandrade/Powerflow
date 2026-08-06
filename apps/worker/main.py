"""Durable database-backed worker for extraction and correlation jobs."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

import structlog
from sqlalchemy import select

from taskflow.adapters.persistence.models import SignalORM, SourceItemORM
from taskflow.adapters.queue.in_process_queue import InProcessQueue
from taskflow.config.container import AsyncSessionLocal
from taskflow.config.logging import configure_logging
from taskflow.domain.value_objects.enums import ProcessingStatus, SignalState

log = structlog.get_logger()


@dataclass(frozen=True)
class WorkerCycleResult:
    extracted: int
    correlated: int


async def consume_pending(limit: int = 25) -> WorkerCycleResult:
    """Consume persisted work so API and worker processes need not share memory."""
    async with AsyncSessionLocal() as session:
        source_ids = tuple((await session.execute(
            select(SourceItemORM.id)
            .where(
                SourceItemORM.processing_status == ProcessingStatus.PENDING.value,
                SourceItemORM.blocked_by_safety.is_(False),
            )
            .order_by(SourceItemORM.created_at)
            .limit(limit)
        )).scalars().all())

    queue = InProcessQueue()
    extracted = 0
    for source_id in source_ids:
        await queue.dispatch("extract_signals", {"source_item_id": str(source_id)})
        extracted += 1

    async with AsyncSessionLocal() as session:
        signal_ids = tuple((await session.execute(
            select(SignalORM.id)
            .where(SignalORM.state == SignalState.PENDING_CORRELATION.value)
            .order_by(SignalORM.created_at)
            .limit(limit)
        )).scalars().all())

    correlated = 0
    for signal_id in signal_ids:
        await queue.dispatch(
            "correlate_signal",
            {"signal_id": str(signal_id), "force_triage": False},
        )
        correlated += 1

    return WorkerCycleResult(extracted=extracted, correlated=correlated)


async def run_worker(poll_seconds: float = 2.0) -> None:
    """Poll durable pending states with bounded retry backoff and observable failures."""
    configure_logging()
    log.info("worker.started", poll_seconds=poll_seconds)
    consecutive_failures = 0
    try:
        while True:
            try:
                result = await consume_pending()
                consecutive_failures = 0
                if result.extracted or result.correlated:
                    log.info(
                        "worker.cycle.completed",
                        extracted=result.extracted,
                        correlated=result.correlated,
                    )
                await asyncio.sleep(poll_seconds)
            except Exception as exc:  # noqa: BLE001 - worker boundary must retry
                consecutive_failures += 1
                retry_seconds = min(30.0, poll_seconds * (2 ** min(consecutive_failures, 4)))
                log.error(
                    "worker.cycle.failed",
                    error_type=type(exc).__name__,
                    consecutive_failures=consecutive_failures,
                    retry_seconds=retry_seconds,
                )
                await asyncio.sleep(retry_seconds)
    except asyncio.CancelledError:
        log.info("worker.stopped")
        raise


if __name__ == "__main__":
    asyncio.run(run_worker())