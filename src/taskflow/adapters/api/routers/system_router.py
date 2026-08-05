from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from taskflow.application.use_cases.scan_stale_items import ScanStaleItemsUseCase
from taskflow.config.container import get_scan_stale_items_use_case

router = APIRouter(prefix="/api/system", tags=["System"])


class ScanResponse(BaseModel):
    scanned_tasks_count: int
    message: str


@router.post("/scan-stale", response_model=ScanResponse)
async def scan_stale_items(
    uc: ScanStaleItemsUseCase = Depends(get_scan_stale_items_use_case),
) -> ScanResponse:
    """Aciona a varredura de tarefas inativas ou obsoletas manualmente."""
    try:
        results = await uc.execute()
        return ScanResponse(
            scanned_tasks_count=len(results),
            message="Scan completed successfully.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/capacity")
async def get_daily_capacity() -> dict:
    """Diagnóstico de capacidade diária (Horas de Reunião vs Focus Time)."""
    return {
        "work_hours_total": 8.0,
        "meeting_hours": 3.5,
        "focus_time_available": 4.5,
        "energy_score_pct": 85,
        "context_switches_count": 4,
    }
