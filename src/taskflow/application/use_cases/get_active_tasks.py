import logging
from typing import Sequence
from taskflow.domain.ports.ports import TaskRepository

logger = logging.getLogger(__name__)


class GetActiveTasksUseCase:
    """Busca tarefas ativas para listagem no Dashboard e aba Tarefas.
    
    A filtragem por status específicos é feita no frontend conforme a escolha técnica do MVP,
    embora o repositório suporte filtragem opcional.
    """

    def __init__(self, repository: TaskRepository) -> None:
        self.repository = repository

    async def execute(self) -> Sequence[dict]:
        """Recupera tarefas não-concluídas/canceladas."""
        logger.info("Recuperando tarefas ativas")
        tasks = await self.repository.find_active()
        # Retorna representações ditadas das tarefas (DTOs simplificados ou próprias entidades serializáveis)
        return tasks
