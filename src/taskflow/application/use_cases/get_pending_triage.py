import logging
from collections.abc import Sequence

from taskflow.domain.ports.ports import SignalRepository

logger = logging.getLogger(__name__)


class GetPendingTriageUseCase:
    """Busca propostas de triagem geradas pelo LLM aguardando decisão."""

    def __init__(self, repository: SignalRepository) -> None:
        self.repository = repository

    async def execute(self) -> Sequence[dict]:
        """Recupera itens pendentes de triagem."""
        logger.info("Recuperando itens na fila de triagem")
        signals = await self.repository.get_pending(limit=50)
        return signals
