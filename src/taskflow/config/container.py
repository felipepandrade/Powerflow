import os
from collections.abc import AsyncGenerator

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from taskflow.adapters.llm.factory import create_embedding_provider, create_llm_provider
from taskflow.adapters.persistence.signal_repository import SqlAlchemySignalRepository
from taskflow.adapters.persistence.task_repository import SqlAlchemyTaskRepository
from taskflow.adapters.persistence.unit_of_work import SqlAlchemyUnitOfWork
from taskflow.application.use_cases.correlate_signal import CorrelateSignalUseCase
from taskflow.application.use_cases.extract_signals import ExtractSignalsUseCase
from taskflow.application.use_cases.ingest_source_item import IngestSourceItemUseCase
from taskflow.application.use_cases.manage_task import ManageTaskUseCase
from taskflow.application.use_cases.scan_stale_items import ScanStaleItemsUseCase
from taskflow.application.use_cases.suggest_follow_up import SuggestFollowUpUseCase
from taskflow.application.use_cases.triage_proposal import TriageProposalUseCase
from taskflow.config.settings import get_settings
from taskflow.domain.ports.ports import EmbeddingProvider, LLMProvider, SignalRepository, TaskRepository, UnitOfWork


# Setup de Database
settings = get_settings()

if settings.DATABASE_URL.startswith("sqlite"):
    db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency que provê a sessão assíncrona com o banco."""
    async with AsyncSessionLocal() as session:
        yield session


def get_uow(session: AsyncSession = Depends(get_db_session)) -> UnitOfWork:
    """Retorna o Unit of Work instanciado com a sessão injetada."""
    return SqlAlchemyUnitOfWork(session)


def get_task_repository(session: AsyncSession = Depends(get_db_session)) -> TaskRepository:
    """Injeta repositório de tasks."""
    return SqlAlchemyTaskRepository(session)


def get_signal_repository(session: AsyncSession = Depends(get_db_session)) -> SignalRepository:
    """Injeta repositório de signals."""
    return SqlAlchemySignalRepository(session)


def get_llm_provider(
    request: Request,
    x_llm_provider: str | None = Header(None, description="Provedor de IA (gemini ou ollama)"),
    x_llm_api_key: str | None = Header(None, description="Chave de API do provedor"),
) -> LLMProvider:
    """
    Retorna o provedor de LLM com base no Header ou nas configurações padrão (Fallback).
    """
    app_settings = get_settings()
    provider = x_llm_provider or app_settings.LLM_PROVIDER
    api_key = x_llm_api_key or app_settings.GEMINI_API_KEY
    
    return create_llm_provider(
        provider_type=provider,
        api_key=api_key,
    )


def get_embedding_provider(
    request: Request,
    x_llm_provider: str | None = Header(None, description="Provedor de IA (gemini ou ollama)"),
    x_llm_api_key: str | None = Header(None, description="Chave de API do provedor"),
) -> EmbeddingProvider:
    """Injeta provedor de Embeddings."""
    app_settings = get_settings()
    provider = x_llm_provider or app_settings.EMBEDDING_PROVIDER
    api_key = x_llm_api_key or app_settings.GEMINI_API_KEY
    
    return create_embedding_provider(
        provider_type=provider,
        api_key=api_key,
    )


# ── Injeção de Use Cases ────────────────────────────────────────────────────────

def get_ingest_source_item_use_case(
    uow: UnitOfWork = Depends(get_uow),
    task_repo: TaskRepository = Depends(get_task_repository),
    signal_repo: SignalRepository = Depends(get_signal_repository),
) -> IngestSourceItemUseCase:
    from taskflow.adapters.queue.in_process_queue import InProcessQueue
    return IngestSourceItemUseCase(uow=uow, task_repo=task_repo, signal_repo=signal_repo, queue=InProcessQueue())


def get_correlate_signal_use_case(
    uow: UnitOfWork = Depends(get_uow),
    task_repo: TaskRepository = Depends(get_task_repository),
    signal_repo: SignalRepository = Depends(get_signal_repository),
    llm: LLMProvider = Depends(get_llm_provider),
    embedder: EmbeddingProvider = Depends(get_embedding_provider),
) -> CorrelateSignalUseCase:
    return CorrelateSignalUseCase(
        uow=uow, task_repo=task_repo, signal_repo=signal_repo, llm=llm, embedder=embedder
    )


def get_manage_task_use_case(
    uow: UnitOfWork = Depends(get_uow),
    task_repo: TaskRepository = Depends(get_task_repository),
) -> ManageTaskUseCase:
    return ManageTaskUseCase(uow=uow, task_repo=task_repo)


def get_triage_proposal_use_case(
    uow: UnitOfWork = Depends(get_uow),
    task_repo: TaskRepository = Depends(get_task_repository),
    signal_repo: SignalRepository = Depends(get_signal_repository),
) -> TriageProposalUseCase:
    return TriageProposalUseCase(uow=uow, task_repo=task_repo, signal_repo=signal_repo)


def get_scan_stale_items_use_case(
    uow: UnitOfWork = Depends(get_uow),
    task_repo: TaskRepository = Depends(get_task_repository),
    signal_repo: SignalRepository = Depends(get_signal_repository),
) -> ScanStaleItemsUseCase:
    return ScanStaleItemsUseCase(uow=uow, task_repo=task_repo, signal_repo=signal_repo)


def get_suggest_follow_up_use_case(
    task_repo: TaskRepository = Depends(get_task_repository),
    llm: LLMProvider = Depends(get_llm_provider),
) -> SuggestFollowUpUseCase:
    return SuggestFollowUpUseCase(task_repo=task_repo, llm=llm)


def get_active_tasks_use_case(
    task_repo: TaskRepository = Depends(get_task_repository),
) -> "GetActiveTasksUseCase":
    from taskflow.application.use_cases.get_active_tasks import GetActiveTasksUseCase
    return GetActiveTasksUseCase(repository=task_repo)


def get_pending_triage_use_case(
    signal_repo: SignalRepository = Depends(get_signal_repository),
) -> "GetPendingTriageUseCase":
    from taskflow.application.use_cases.get_pending_triage import GetPendingTriageUseCase
    return GetPendingTriageUseCase(repository=signal_repo)


def get_extract_signals_use_case(
    uow: UnitOfWork = Depends(get_uow),
    signal_repo: SignalRepository = Depends(get_signal_repository),
    llm: LLMProvider = Depends(get_llm_provider),
) -> ExtractSignalsUseCase:
    from taskflow.adapters.queue.in_process_queue import InProcessQueue
    return ExtractSignalsUseCase(signal_repo=signal_repo, llm=llm, queue=InProcessQueue(), uow=uow)


def create_background_llm_provider() -> LLMProvider:
    """Cria o provedor LLM usando as configurações do .env (para uso em workers background)."""
    s = get_settings()
    return create_llm_provider(
        provider_type=s.LLM_PROVIDER,
        api_key=s.GEMINI_API_KEY,
        ollama_model=s.OLLAMA_MODEL,
    )
