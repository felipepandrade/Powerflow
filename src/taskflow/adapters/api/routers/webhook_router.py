from datetime import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException

from taskflow.adapters.api.schemas.schemas import PowerAutomateWebhookRequest, IngestSourceResponse
from taskflow.application.dto.commands import IngestSourceItemCommand
from taskflow.application.use_cases.ingest_source_item import IngestSourceItemUseCase
from taskflow.config.container import get_ingest_source_item_use_case
from taskflow.domain.value_objects.enums import SourceKind

router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])


@router.post("/powerautomate", response_model=IngestSourceResponse, status_code=201)
async def power_automate_webhook(
    req: PowerAutomateWebhookRequest,
    uc: IngestSourceItemUseCase = Depends(get_ingest_source_item_use_case),
) -> IngestSourceResponse:
    """
    Recebe um webhook do Power Automate (ex: novo e-mail recebido).
    Converte o payload no comando interno e dispara a ingestão no Powerflow.
    """
    try:
        # Tenta fazer parse da data recebida, senão usa agora
        occurred_at = datetime.utcnow()
        if req.received_time:
            try:
                # Converter de string ISO
                occurred_at = datetime.fromisoformat(req.received_time.replace('Z', '+00:00'))
            except ValueError:
                pass

        cmd = IngestSourceItemCommand(
            kind=SourceKind.EMAIL,
            channel="power_automate_webhook",
            external_id=req.message_id or str(uuid.uuid4()),
            occurred_at=occurred_at,
            revision_hash=req.message_id or str(uuid.uuid4()),  # Para simplificar deduplicação no MVP
            title=req.subject,
            body_preview=req.body,
            author_email=req.sender_email,
            author_name=req.sender_name,
        )

        result = await uc.execute(cmd)

        status = "accepted"
        if result.was_filtered:
            status = "filtered"
        elif result.was_deduplicated:
            status = "deduplicated"

        return IngestSourceResponse(
            source_item_id=str(result.source_item_id),
            status=status,
            message=f"Webhook processed with status: {status}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
