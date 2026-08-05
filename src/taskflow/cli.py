"""CLI do TaskFlow v1.2 — Comandos de administração, backfill e relatórios."""

from __future__ import annotations

import asyncio
import sys
from datetime import date, timedelta

import structlog

from taskflow.adapters.persistence.unit_of_work import SqlAlchemyUnitOfWork
from taskflow.application.use_cases.build_daily_snapshots import BuildDailySnapshotsUseCase
from taskflow.config.container import AsyncSessionLocal

log = structlog.get_logger()


async def run_backfill_snapshots(days: int = 30) -> None:
    """Executa o backfill de snapshots analíticos diários para os últimos N dias."""
    log.info("cli.backfill_snapshots.start", days=days)
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)

    current = start_date
    total_processed = 0

    while current <= end_date:
        async with AsyncSessionLocal() as session:
            uow = SqlAlchemyUnitOfWork(session)
            uc = BuildDailySnapshotsUseCase(session, uow)
            res = await uc.execute(current)
            log.info("cli.backfill_snapshots.day_done", day=current.isoformat(), result=res)
            total_processed += 1
        current += timedelta(days=1)

    log.info("cli.backfill_snapshots.completed", total_days=total_processed)


def main() -> None:
    """Entrypoint principal da CLI."""
    if len(sys.argv) > 1 and sys.argv[1] == "backfill-snapshots":
        days = 30
        if len(sys.argv) > 2 and sys.argv[2].isdigit():
            days = int(sys.argv[2])
        asyncio.run(run_backfill_snapshots(days=days))
    else:
        print("Uso: taskflow backfill-snapshots [DIAS]")


if __name__ == "__main__":
    main()
