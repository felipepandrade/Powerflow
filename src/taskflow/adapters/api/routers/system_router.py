from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from taskflow.adapters.persistence.models import DailyCalendarSnapshotORM
from taskflow.application.dto.commands import ScanStaleItemsCommand
from taskflow.application.use_cases.scan_stale_items import ScanStaleItemsUseCase
from taskflow.config.container import get_db_session, get_scan_stale_items_use_case
from taskflow.config.settings import get_settings

router = APIRouter(prefix="/api/system", tags=["System"])


class ScanResponse(BaseModel):
    scanned_tasks_count: int
    message: str


@router.post("/scan-stale", response_model=ScanResponse)
async def scan_stale_items(
    uc: ScanStaleItemsUseCase = Depends(get_scan_stale_items_use_case),
) -> ScanResponse:
    """Run the deterministic stale-task scan."""
    result = await uc.execute(ScanStaleItemsCommand())
    return ScanResponse(
        scanned_tasks_count=result.total_scanned,
        message="Scan completed successfully.",
    )


class CapacityResponse(BaseModel):
    """Capacity facts read from the published daily snapshot."""

    snapshot_date: str
    state: Literal["known", "unknown"]
    meeting_minutes: int | None
    meeting_count: int | None
    available_minutes: int | None
    utilization_pct: float | None
    provenance: str


@router.get("/capacity", response_model=CapacityResponse)
async def get_daily_capacity(
    session: AsyncSession = Depends(get_db_session),
) -> CapacityResponse:
    """Return today's normalized snapshot; never invent missing capacity values."""
    settings = get_settings()
    target = datetime.now(ZoneInfo(settings.APP_TIMEZONE)).date()
    snapshot = await session.get(DailyCalendarSnapshotORM, target)
    if snapshot is None:
        return CapacityResponse(
            snapshot_date=target.isoformat(),
            state="unknown",
            meeting_minutes=None,
            meeting_count=None,
            available_minutes=None,
            utilization_pct=None,
            provenance="daily_calendar_snapshots",
        )
    return CapacityResponse(
        snapshot_date=target.isoformat(),
        state="known",
        meeting_minutes=snapshot.total_meeting_minutes,
        meeting_count=snapshot.meeting_count,
        available_minutes=snapshot.available_minutes,
        utilization_pct=snapshot.utilization_pct,
        provenance="daily_calendar_snapshots",
    )