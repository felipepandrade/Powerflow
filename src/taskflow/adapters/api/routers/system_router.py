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
