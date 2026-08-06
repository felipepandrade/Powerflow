from __future__ import annotations

import hashlib
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from taskflow.adapters.api.schemas.schemas import (
    CorrelateSignalResponse,
    IngestSourceRequest,
    IngestSourceResponse,
    TriageItemSchema,
    TriageListResponse,
    TriageProposalRequest,
    TriageProposalResponse,
)
from taskflow.application.dto.commands import (
    AcceptProposalCommand,
    CorrelateSignalCommand,
    IngestSourceItemCommand,
    RejectProposalCommand,
)
from taskflow.application.use_cases.correlate_signal import CorrelateSignalUseCase
from taskflow.application.use_cases.get_pending_triage import GetPendingTriageUseCase
from taskflow.application.use_cases.ingest_source_item import IngestSourceItemUseCase
from taskflow.application.use_cases.triage_proposal import TriageProposalUseCase
from taskflow.config.container import (
    get_correlate_signal_use_case,
    get_ingest_source_item_use_case,
    get_pending_triage_use_case,
    get_triage_proposal_use_case,
)

router = APIRouter(prefix="/api/signals", tags=["Signals"])


@router.post("", response_model=IngestSourceResponse, status_code=201)
async def ingest_source(
    request: IngestSourceRequest,
    use_case: IngestSourceItemUseCase = Depends(get_ingest_source_item_use_case),
) -> IngestSourceResponse:
    content_hash = hashlib.sha256(request.content.encode("utf-8")).hexdigest()
    result = await use_case.execute(
        IngestSourceItemCommand(
            kind=request.kind,
            channel=request.channel,
            external_id=request.external_id or f"api:{content_hash}",
            occurred_at=request.occurred_at or datetime.utcnow(),
            revision_hash=request.revision_hash or content_hash,
            title=request.title,
            body_full=request.content,
            body_preview=request.content[:500],
            author_email=request.author_email,
            author_name=request.author_name,
        )
    )
    status = (
        "deduplicated"
        if result.was_deduplicated
        else "filtered"
        if result.was_filtered
        else "accepted"
    )
    return IngestSourceResponse(
        source_item_id=str(result.source_item_id),
        status=status,
        message=f"Ingestion completed with status: {status}",
    )


@router.post("/{signal_id}/correlate", response_model=CorrelateSignalResponse)
async def correlate_signal(
    signal_id: uuid.UUID,
    use_case: CorrelateSignalUseCase = Depends(get_correlate_signal_use_case),
) -> CorrelateSignalResponse:
    try:
        result = await use_case.execute(CorrelateSignalCommand(signal_id=signal_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return CorrelateSignalResponse(
        signal_id=str(result.signal_id),
        action_taken=result.action,
        message=f"Correlation finished with action: {result.action}",
        correlation_run_id=result.correlation_run_id,
        decision_kind=result.decision_kind.value,
        policy_rule_id=result.policy_rule_id,
        confidence=result.confidence,
        applied_task_id=result.applied_task_id,
        proposal_id=result.proposal_id,
    )


@router.get("/triage", response_model=TriageListResponse)
async def list_pending_triage(
    use_case: GetPendingTriageUseCase = Depends(get_pending_triage_use_case),
) -> TriageListResponse:
    proposals = await use_case.execute()
    data = [TriageItemSchema.model_validate(proposal) for proposal in proposals]
    return TriageListResponse(data=data, count=len(data))


@router.post("/{proposal_id}/triage", response_model=TriageProposalResponse)
async def triage_proposal(
    proposal_id: uuid.UUID,
    request: TriageProposalRequest,
    use_case: TriageProposalUseCase = Depends(get_triage_proposal_use_case),
) -> TriageProposalResponse:
    try:
        if request.action == "apply":
            edits = dict(request.modifications or {})
            if request.task_id:
                edits.setdefault("task_id", request.task_id)
            await use_case.accept(
                AcceptProposalCommand(proposal_id=proposal_id, user_edits=edits or None)
            )
        elif request.action == "discard":
            await use_case.reject(
                RejectProposalCommand(
                    proposal_id=proposal_id,
                    reason="Rejected by user",
                )
            )
        else:
            raise HTTPException(status_code=422, detail="action must be apply or discard")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TriageProposalResponse(
        success=True,
        message=f"Triage decision '{request.action}' applied.",
    )
