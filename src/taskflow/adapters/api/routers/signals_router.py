import uuid

from fastapi import APIRouter, Depends, HTTPException

from taskflow.adapters.api.schemas.schemas import (
    CorrelateSignalResponse,
    IngestSourceRequest,
    IngestSourceResponse,
    TriageProposalRequest,
    TriageProposalResponse,
    TriageListResponse,
    TriageItemSchema,
)
from taskflow.application.use_cases.correlate_signal import CorrelateSignalUseCase
from taskflow.application.dto.commands import IngestSourceItemCommand
from taskflow.application.use_cases.ingest_source_item import IngestSourceItemUseCase
from taskflow.application.use_cases.triage_proposal import TriageProposalUseCase
from taskflow.application.use_cases.get_pending_triage import GetPendingTriageUseCase
from taskflow.config.container import (
    get_correlate_signal_use_case,
    get_ingest_source_item_use_case,
    get_triage_proposal_use_case,
    get_pending_triage_use_case,
)
from taskflow.domain.value_objects.enums import ProcessingStatus, SourceKind
import datetime

router = APIRouter(prefix="/api/signals", tags=["Signals"])


@router.post("", response_model=IngestSourceResponse, status_code=201)
async def ingest_source(
    req: IngestSourceRequest,
    uc: IngestSourceItemUseCase = Depends(get_ingest_source_item_use_case),
) -> IngestSourceResponse:
    """Ingere um novo item de origem (email, anotação, etc.) e dispara a extração de sinais."""
    cmd = IngestSourceItemCommand(
        kind=SourceKind.EMAIL,
        channel=req.channel,
        external_id=str(uuid.uuid4()),
        occurred_at=datetime.datetime.utcnow(),
        revision_hash=str(uuid.uuid4()),
        body_full=req.content,
        body_preview=req.content[:500] if req.content else None,
        author_email=req.author_email,
        author_name=req.author_name,
    )
    result = await uc.execute(cmd)
    
    status = "accepted"
    if result.was_filtered:
        status = "filtered"
        
    return IngestSourceResponse(
        source_item_id=str(result.source_item_id),
        status=status,
        message=f"Ingestion completed with status: {status}",
    )


@router.post("/{signal_id}/correlate", response_model=CorrelateSignalResponse)
async def correlate_signal(
    signal_id: uuid.UUID,
    uc: CorrelateSignalUseCase = Depends(get_correlate_signal_use_case),
) -> CorrelateSignalResponse:
    """Dispara a correlação de um sinal específico contra a base de tarefas candidatas."""
    try:
        run = await uc.execute(signal_id)
        if not run:
            raise HTTPException(status_code=404, detail="Signal not found or not pending")
            
        return CorrelateSignalResponse(
            signal_id=str(run.signal_id),
            action_taken=run.routed_to_triage and "triage" or "applied",
            message=f"Correlation finished with action: {run.routed_to_triage and 'triage' or 'applied'}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/triage", response_model=TriageListResponse)
async def list_pending_triage(
    uc: GetPendingTriageUseCase = Depends(get_pending_triage_use_case),
) -> TriageListResponse:
    """Retorna itens na fila de triagem aguardando decisão manual."""
    try:
        signals = await uc.execute()
        schema_data = [TriageItemSchema.model_validate(s) for s in signals]
        return TriageListResponse(data=schema_data, count=len(schema_data))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{signal_id}/triage", response_model=TriageProposalResponse)
async def triage_proposal(
    signal_id: uuid.UUID,
    req: TriageProposalRequest,
    uc: TriageProposalUseCase = Depends(get_triage_proposal_use_case),
) -> TriageProposalResponse:
    """Aplica a decisão manual de triagem feita pelo usuário."""
    try:
        from taskflow.application.dto.commands import AcceptProposalCommand, RejectProposalCommand
        if req.action == "apply":
            cmd = AcceptProposalCommand(
                proposal_id=signal_id,
                user_edits=req.modifications
            )
            await uc.accept(cmd)
        else:
            cmd = RejectProposalCommand(
                proposal_id=signal_id,
                reason="Rejeitado manualmente"
            )
            await uc.reject(cmd)
            
        return TriageProposalResponse(
            success=True,
            message=f"Triage decision '{req.action}' applied successfully.",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
