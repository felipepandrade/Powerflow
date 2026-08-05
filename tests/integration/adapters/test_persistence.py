from typing import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker

from taskflow.adapters.persistence.models import Base
from taskflow.adapters.persistence.task_repository import SqlAlchemyTaskRepository
from taskflow.adapters.persistence.unit_of_work import SqlAlchemyUnitOfWork
from taskflow.domain.entities.task import Task
from taskflow.domain.value_objects.enums import Priority, TaskStatus


@pytest.fixture
async def async_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestingSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    async with TestingSessionLocal() as session:
        yield session


@pytest.mark.asyncio
async def test_uow_and_repository_can_save_and_retrieve_task(async_session: AsyncSession) -> None:
    task = Task(
        title="Estudar SQLAlchemy 2.0",
        description="Fazer testes com aiosqlite",
        status=TaskStatus.INBOX,
        priority=Priority.HIGH,
    )

    uow = SqlAlchemyUnitOfWork(async_session)
    repo = SqlAlchemyTaskRepository(async_session)

    # 1. Salvar tarefa usando UoW
    async with uow:
        await repo.save(task)
        await uow.commit()

    # 2. Recuperar tarefa
    async with uow:
        saved_task = await repo.get_by_id(task.id)
        assert saved_task is not None
        assert saved_task.id == task.id
        assert saved_task.title == "Estudar SQLAlchemy 2.0"
        assert saved_task.priority == Priority.HIGH
        
        # 3. Busca Full-Text
        results = await repo.search_full_text("aiosqlite")
        assert len(results) == 1
        assert results[0].id == task.id
