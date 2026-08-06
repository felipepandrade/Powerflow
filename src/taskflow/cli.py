"""Operational CLI for snapshots and deterministic metric materialization."""
from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import typer
from sqlalchemy import select

from taskflow.adapters.persistence.models import DailyCalendarSnapshotORM
from taskflow.adapters.persistence.unit_of_work import SqlAlchemyUnitOfWork
from taskflow.application.use_cases.build_daily_snapshots import BuildDailySnapshotsUseCase
from taskflow.application.use_cases.compute_metrics import ComputeMetricsUseCase
from taskflow.config.container import AsyncSessionLocal
from taskflow.config.settings import get_settings

app = typer.Typer(
    name="taskflow",
    help="Powerflow operational commands for reproducible analytics.",
    no_args_is_help=True,
)


def _parse_date(value: str, option_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise typer.BadParameter("expected ISO date YYYY-MM-DD", param_hint=option_name) from exc


def _local_today() -> date:
    settings = get_settings()
    return datetime.now(ZoneInfo(settings.APP_TIMEZONE)).date()


async def _build_range(start: date, end: date) -> int:
    if end < start:
        raise typer.BadParameter("--to must be on or after --from")
    processed = 0
    current = start
    while current <= end:
        async with AsyncSessionLocal() as session:
            result = await BuildDailySnapshotsUseCase(
                session,
                SqlAlchemyUnitOfWork(session),
            ).execute(current)
        typer.echo(f"{current.isoformat()}: {result}")
        processed += 1
        current += timedelta(days=1)
    return processed


@app.command("backfill-snapshots")
def backfill_snapshots(
    start_raw: str | None = typer.Option(None, "--from", help="First date, YYYY-MM-DD."),
    end_raw: str | None = typer.Option(None, "--to", help="Last date, YYYY-MM-DD."),
    days: int = typer.Option(30, min=1, help="Fallback window when --from is omitted."),
) -> None:
    """Rebuild a deterministic daily range from historical facts."""
    end = _parse_date(end_raw, "--to") if end_raw else _local_today()
    start = _parse_date(start_raw, "--from") if start_raw else end - timedelta(days=days - 1)
    processed = asyncio.run(_build_range(start, end))
    typer.echo(f"processed_partitions={processed}")


@app.command("build-snapshot")
def build_snapshot(
    date_raw: str | None = typer.Option(None, "--date", help="Partition date, YYYY-MM-DD."),
) -> None:
    """Build one idempotent snapshot partition."""
    target = _parse_date(date_raw, "--date") if date_raw else _local_today()
    asyncio.run(_build_range(target, target))


async def _recompute(
    start: date,
    end: date,
    project_id: uuid.UUID | None,
) -> int:
    async with AsyncSessionLocal() as session:
        metrics = await ComputeMetricsUseCase(
            session,
            SqlAlchemyUnitOfWork(session),
        ).execute(start, end, project_id=project_id)
    return len(metrics)


@app.command("recompute-metrics")
def recompute_metrics(
    start_raw: str = typer.Option(..., "--from", help="First covered date, YYYY-MM-DD."),
    end_raw: str = typer.Option(..., "--to", help="Last covered date, YYYY-MM-DD."),
    project_raw: str | None = typer.Option(None, "--project-id"),
) -> None:
    """Materialize deterministic metrics only when snapshot coverage is complete."""
    start = _parse_date(start_raw, "--from")
    end = _parse_date(end_raw, "--to")
    if end < start:
        raise typer.BadParameter("--to must be on or after --from")
    try:
        project_id = uuid.UUID(project_raw) if project_raw else None
    except ValueError as exc:
        raise typer.BadParameter("expected UUID", param_hint="--project-id") from exc
    count = asyncio.run(_recompute(start, end, project_id))
    typer.echo(f"materialized_metrics={count}")


async def _snapshot_status() -> tuple[date | None, date | None, int, list[date]]:
    async with AsyncSessionLocal() as session:
        dates = list((await session.execute(
            select(DailyCalendarSnapshotORM.snapshot_date)
            .order_by(DailyCalendarSnapshotORM.snapshot_date)
        )).scalars().all())
    if not dates:
        return None, None, 0, []
    available = set(dates)
    gaps: list[date] = []
    current = dates[0]
    while current <= dates[-1]:
        if current not in available:
            gaps.append(current)
        current += timedelta(days=1)
    return dates[0], dates[-1], len(dates), gaps


@app.command("snapshots-status")
def snapshots_status() -> None:
    """Report analytical coverage and missing daily partitions."""
    first, last, count, gaps = asyncio.run(_snapshot_status())
    typer.echo(
        f"first={first.isoformat() if first else 'none'} "
        f"last={last.isoformat() if last else 'none'} partitions={count}"
    )
    typer.echo("gaps=" + (",".join(item.isoformat() for item in gaps) if gaps else "none"))


def main() -> None:
    """Console-script entrypoint."""
    app()


if __name__ == "__main__":
    main()