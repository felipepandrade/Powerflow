"""Use Case: ExtractSignals — Fase 7 (LLM).

Extrai sinais de compromisso e intenção a partir do texto do SourceItem
utilizando o provedor de LLM configurado, e os converte em objetos Signal.
"""

import uuid
from datetime import datetime

import structlog

from taskflow.domain.entities.source import Signal
from taskflow.domain.ports.ports import LLMProvider, Queue, SignalRepository, UnitOfWork
from taskflow.domain.value_objects.enums import SignalState, SignalType

log = structlog.get_logger()

class ExtractSignalsUseCase:
    """Extrai sinais a partir de um SourceItem utilizando um LLM."""

    def __init__(
        self,
        signal_repo: SignalRepository,
        llm: LLMProvider,
        queue: Queue,
        uow: UnitOfWork,
    ) -> None:
        self._signal_repo = signal_repo
        self._llm = llm
        self._queue = queue
        self._uow = uow

    async def execute(self, source_item_id: uuid.UUID) -> list[uuid.UUID]:
        """Executa a extração de sinais."""
        log.info("extract_signals.start", source_item_id=str(source_item_id))

        item = await self._signal_repo.get_source_item_by_id(source_item_id)
        if not item:
            log.warning("extract_signals.source_not_found", source_item_id=str(source_item_id))
            return []

        text_to_analyze = item.body_full or item.body_preview or item.title
        if not text_to_analyze:
            log.warning("extract_signals.no_content", source_item_id=str(source_item_id))
            return []

        # Extração via LLM
        context = {
            "author_name": item.author_name,
            "author_email": item.author_email,
            "subject": item.title,
            "date": item.occurred_at.isoformat() if item.occurred_at else None,
        }
        
        try:
            extracted_data = await self._llm.extract(text_to_analyze, context)
            
            # Formatar payload e extrair os sinais gerados
            # Como o LLM pode retornar múltiplos ou um, ajustamos
            payload = {}
            if "title" in extracted_data:
                payload = {
                    "task_title": extracted_data.get("title", item.title),
                    "task_description": extracted_data.get("description", text_to_analyze[:200]),
                    "due_date": extracted_data.get("due_date"),
                    "priority": extracted_data.get("priority", "medium"),
                }
            else:
                # Fallback se o LLM não trouxer o formato exato
                payload = {
                    "task_title": item.title,
                    "task_description": text_to_analyze[:200],
                    "raw_llm_output": extracted_data
                }

            signal = Signal(
                id=uuid.uuid4(),
                source_item_id=item.id,
                signal_type=SignalType.INTERACTION,  # Ou COMMITMENT, dependo da análise mais profunda
                state=SignalState.PENDING_CORRELATION,
                extraction_conf=0.9,
                payload=payload,
                created_at=datetime.utcnow()
            )

            async with self._uow:
                await self._signal_repo.save(signal)  # type: ignore[arg-type]
                await self._uow.commit()

            # Enfileirar a próxima etapa (Correlação)
            job_id = await self._queue.enqueue(
                "correlate_signal",
                {"signal_id": str(signal.id)},
            )
            log.info("extract_signals.enqueued_correlation", signal_id=str(signal.id), job_id=job_id)

            return [signal.id]

        except Exception as e:
            log.error("extract_signals.error", error=str(e), exc_info=True)
            return []
