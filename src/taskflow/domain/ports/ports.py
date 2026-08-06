"""Portas (interfaces) do domínio TaskFlow — Dependency Inversion.

Todas as dependências externas são invertidas aqui. O domínio depende
apenas dessas abstrações — nunca das implementações concretas.
"""

from __future__ import annotations

import abc
import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from taskflow.domain.entities.source import CalendarEvent, CorrelationRun, Signal, SourceItem
from taskflow.domain.entities.task import Task, TaskProposal


class LLMProvider(abc.ABC):
    """Porta para provedores de LLM — RF-C.5, RF-H.1."""

    @abc.abstractmethod
    async def classify(self, text: str, context: dict[str, Any]) -> dict[str, Any]:
        """Classificação leve — Estágio 2 da extração.

        Responde: 'contém compromisso acionável?' — thinking=0.
        """

    @abc.abstractmethod
    async def extract(self, text: str, context: dict[str, Any]) -> dict[str, Any]:
        """Extração estruturada de sinais — Estágio 3, LLM reasoner."""

    @abc.abstractmethod
    async def correlate(self, signal: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
        """Raciocínio relacional — Estágio G2.

        Recebe o sinal e fichas compactas dos candidatos.
        Retorna assessments + decision_hint.
        """

    @abc.abstractmethod
    async def draft_follow_up(self, task: dict[str, Any], context: dict[str, Any], tone: str) -> str:
        """Gera rascunho de nudge — RF-E.2."""


class EmbeddingProvider(abc.ABC):
    """Porta para geração de embeddings — recuperador R6."""

    @abc.abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Gera embeddings vetoriais para os textos."""


class SourceProvider(abc.ABC):
    """Porta para adaptadores de fonte de dados (Graph API)."""

    @abc.abstractmethod
    async def fetch_delta(self, resource_id: str, delta_link: str | None) -> tuple[list[dict[str, Any]], str]:
        """Busca itens incrementais via delta query.

        Retorna (items, new_delta_link).
        """


class TaskRepository(abc.ABC):
    """Porta para persistência de tarefas."""

    @abc.abstractmethod
    async def get_by_id(self, task_id: uuid.UUID) -> Task | None:
        """Busca tarefa por ID."""

    @abc.abstractmethod
    async def save(self, task: Task) -> None:
        """Persiste ou atualiza uma tarefa."""

    @abc.abstractmethod
    async def find_active(
        self,
        status_filter: list[str] | None = None,
        limit: int = 100,
    ) -> Sequence[Task]:
        """Retorna tarefas ativas com filtros opcionais."""

    @abc.abstractmethod
    async def search_full_text(self, query: str, limit: int = 20) -> Sequence[Task]:
        """Busca full-text em título, descrição e evidências — RF-D.7."""

    @abc.abstractmethod
    async def find_by_embedding(self, embedding: list[float], top_k: int = 8) -> Sequence[Task]:
        """Busca semântica por similaridade vetorial — recuperador R6."""

    async def find_by_source_context(
        self, conversation_id: str | None, external_id: str | None, limit: int = 8,
    ) -> Sequence[Task]:
        """Return tasks linked to the same source conversation or event."""
        return ()


class SignalRepository(abc.ABC):
    """Porta para persistência de sinais e dados de correlação."""

    @abc.abstractmethod
    async def save(self, item: Signal | SourceItem | TaskProposal) -> None:
        """Persiste ou atualiza um sinal."""
    async def save_calendar_event(self, event: CalendarEvent) -> None:
        """Persist capacity-safe calendar metadata."""
        raise NotImplementedError

    async def get_signal_by_id(self, signal_id: uuid.UUID) -> Signal | None:
        """Fetch a signal regardless of its current state."""
        raise NotImplementedError


    @abc.abstractmethod
    async def get_source_item_by_id(self, item_id: uuid.UUID) -> SourceItem | None:
        """Busca o SourceItem pelo ID."""
    async def get_source_item_by_dedup_key(
        self, kind: str, external_id: str, revision_hash: str,
    ) -> SourceItem | None:
        """Fetch the canonical item protected by the transactional unique key."""
        raise NotImplementedError


    @abc.abstractmethod
    async def get_pending(self, limit: int = 50) -> Sequence[Signal]:
        """Retorna sinais aguardando correlação."""
    async def get_proposal_by_id(self, proposal_id: uuid.UUID) -> TaskProposal | None:
        """Fetch one triage proposal by identity."""
        raise NotImplementedError

    async def get_pending_proposals(self, limit: int = 50) -> Sequence[TaskProposal]:
        """Return pending triage proposals only."""
        raise NotImplementedError


    @abc.abstractmethod
    async def save_correlation_run(self, run: CorrelationRun) -> None:
        """Persiste auditoria de correlação — NF-5."""

    @abc.abstractmethod
    async def get_orphan_signals(self, since: datetime, limit: int = 100) -> Sequence[Signal]:
        """Retorna sinais não resolvidos para reprocessamento tardio — RF-G.10."""


class AreaRepository(abc.ABC):
    """Porta para persistência de áreas organizacionais."""

    @abc.abstractmethod
    async def get_by_id(self, area_id: uuid.UUID) -> Any | None:
        """Busca área por ID."""

    @abc.abstractmethod
    async def save(self, area: Any) -> None:
        """Persiste ou atualiza uma área."""

    @abc.abstractmethod
    async def list_all(self) -> Sequence[Any]:
        """Lista todas as áreas."""


class StakeholderRepository(abc.ABC):
    """Porta para persistência de stakeholders."""

    @abc.abstractmethod
    async def get_by_id(self, stakeholder_id: uuid.UUID) -> Any | None:
        """Busca stakeholder por ID."""

    @abc.abstractmethod
    async def get_by_email(self, email: str) -> Any | None:
        """Busca stakeholder por e-mail."""

    @abc.abstractmethod
    async def save(self, stakeholder: Any) -> None:
        """Persiste ou atualiza um stakeholder."""

    @abc.abstractmethod
    async def list_all(self) -> Sequence[Any]:
        """Lista todos os stakeholders."""


class ProjectRepository(abc.ABC):
    """Porta para persistência de projetos."""

    @abc.abstractmethod
    async def get_by_id(self, project_id: uuid.UUID) -> Any | None:
        """Busca projeto por ID."""

    @abc.abstractmethod
    async def save(self, project: Any) -> None:
        """Persiste ou atualiza um projeto."""

    @abc.abstractmethod
    async def list_all(self) -> Sequence[Any]:
        """Lista todos os projetos."""


class MilestoneRepository(abc.ABC):
    """Porta para persistência de marcos."""

    @abc.abstractmethod
    async def get_by_id(self, milestone_id: uuid.UUID) -> Any | None:
        """Busca marco por ID."""

    @abc.abstractmethod
    async def save(self, milestone: Any) -> None:
        """Persiste ou atualiza um marco."""

    @abc.abstractmethod
    async def find_by_project(self, project_id: uuid.UUID) -> Sequence[Any]:
        """Retorna os marcos de um projeto."""


class CalendarRepository(abc.ABC):
    """Porta para persistência de eventos de calendário."""

    @abc.abstractmethod
    async def save(self, event: Any) -> None:
        """Persiste ou atualiza um evento de calendário."""

    @abc.abstractmethod
    async def find_in_range(self, start: datetime, end: datetime) -> Sequence[Any]:
        """Retorna eventos no intervalo especificado."""


class UnitOfWork(abc.ABC):
    """Porta para gerenciamento de transações."""

    @abc.abstractmethod
    async def __aenter__(self) -> UnitOfWork:
        """Inicia transação."""

    @abc.abstractmethod
    async def __aexit__(self, *args: object) -> None:
        """Commit ou rollback."""

    @abc.abstractmethod
    async def commit(self) -> None:
        """Confirma transação."""

    @abc.abstractmethod
    async def rollback(self) -> None:
        """Reverte transação."""


class Queue(abc.ABC):
    """Porta para fila de mensagens — InProcessQueue ou ARQ/Redis."""

    @abc.abstractmethod
    async def enqueue(self, task_name: str, payload: dict[str, Any], delay_seconds: int = 0) -> str:
        """Enfileira tarefa com payload."""

    @abc.abstractmethod
    async def dequeue(self, task_name: str) -> dict[str, Any] | None:
        """Retira próxima tarefa da fila."""


class Notifier(abc.ABC):
    """Porta para envio de notificações — email, Teams."""

    @abc.abstractmethod
    async def send_email(self, to: str, subject: str, body: str) -> None:
        """Envia e-mail — requer confirmação explícita do usuário (RF-E.3)."""

    @abc.abstractmethod
    async def send_teams_message(self, chat_id: str, body: str) -> None:
        """Envia mensagem no Teams."""


class Clock(abc.ABC):
    """Porta para obtenção de hora corrente — facilita testes determinísticos."""

    @abc.abstractmethod
    def now(self) -> datetime:
        """Retorna o instante atual."""


class SystemClock(Clock):
    """Implementação padrão que usa o relógio do sistema."""

    def now(self) -> datetime:
        """Retorna datetime.utcnow()."""
        return datetime.utcnow()
