"""Observable scheduler for the trustworthy analytics read model."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from taskflow.adapters.persistence.unit_of_work import SqlAlchemyUnitOfWork
from taskflow.application.use_cases.build_daily_snapshots import BuildDailySnapshotsUseCase
from taskflow.application.use_cases.compute_metrics import ComputeMetricsUseCase
from taskflow.config.container import AsyncSessionLocal
from taskflow.config.logging import configure_logging
from taskflow.config.settings import Settings, get_settings
from taskflow.domain.policies.capacity_policy import CapacityPolicy

log = structlog.get_logger()
SNAPSHOT_DUE_LOCAL = time(23, 50)


@dataclass(frozen=True)
class SchedulerCycleResult:
    snapshot_date: date
    snapshot_counts: dict[str, int]
    metric_count: int


def _parse_local_time(value: str) -> time:
    try:
        return time.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("work-hour settings must use HH:MM") from exc


def _capacity_policy(settings: Settings) -> CapacityPolicy:
    configured_days = frozenset(
        int(item.strip()) - 1
        for item in settings.WORK_DAYS.split(",")
        if item.strip()
    )
    return CapacityPolicy(
        work_start=_parse_local_time(settings.WORK_HOURS_START),
        work_end=_parse_local_time(settings.WORK_HOURS_END),
        work_days=configured_days,
        buffer_minutes=settings.CAPACITY_BUFFER_MINUTES,
        timezone_name=settings.APP_TIMEZONE,
    )


def most_recent_due_date(now: datetime) -> date:
    """Return the latest partition that should already have been published."""
    if now.timetz().replace(tzinfo=None) >= SNAPSHOT_DUE_LOCAL:
        return now.date()
    return now.date() - timedelta(days=1)


async def build_due_partition(
    now: datetime | None = None,
    session: AsyncSession | None = None,
) -> SchedulerCycleResult:
    """Build the due snapshot and only then materialize metrics from that partition."""
    settings = get_settings()
    current = now or datetime.now(ZoneInfo(settings.APP_TIMEZONE))
    target = most_recent_due_date(current)

    if session is not None:
        uow = SqlAlchemyUnitOfWork(session)
        counts = await BuildDailySnapshotsUseCase(
            session,
            uow,
            capacity_policy=_capacity_policy(settings),
        ).execute(target)
        metrics = await ComputeMetricsUseCase(session, uow).execute(target, target)
        return SchedulerCycleResult(target, counts, len(metrics))

    async with AsyncSessionLocal() as owned_session:
        return await build_due_partition(current, owned_session)


async def run_scheduler() -> None:
    """Run idempotent cycles with bounded backoff and structured observability."""
    configure_logging()
    settings = get_settings()
    interval = max(10, settings.SCHEDULER_INTERVAL_SECONDS)
    consecutive_failures = 0
    log.info("scheduler.started", interval_seconds=interval)
    try:
        while settings.ENABLE_SCHEDULER:
            try:
                result = await build_due_partition()
                consecutive_failures = 0
                log.info(
                    "scheduler.cycle.completed",
                    snapshot_date=result.snapshot_date.isoformat(),
                    snapshot_counts=result.snapshot_counts,
                    metric_count=result.metric_count,
                )
                await asyncio.sleep(interval)
            except Exception as exc:  # noqa: BLE001 - scheduler boundary must retry
                consecutive_failures += 1
                retry_seconds = min(300, interval * (2 ** min(consecutive_failures, 3)))
                log.error(
                    "scheduler.cycle.failed",
                    error_type=type(exc).__name__,
                    consecutive_failures=consecutive_failures,
                    retry_seconds=retry_seconds,
                )
                await asyncio.sleep(retry_seconds)
    except asyncio.CancelledError:
        log.info("scheduler.stopped")
        raise


if __name__ == "__main__":
    asyncio.run(run_scheduler())