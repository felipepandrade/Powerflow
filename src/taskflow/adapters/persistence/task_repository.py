from datetime import date
import uuid
from collections.abc import Sequence

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from taskflow.adapters.persistence.models import TaskORM
from taskflow.domain.entities.task import Task
from taskflow.domain.ports.ports import TaskRepository
from taskflow.domain.value_objects.enums import Priority, TaskStatus


class SqlAlchemyTaskRepository(TaskRepository):
    """Implementação do repositório de tarefas com SQLAlchemy e SQLite."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, orm: TaskORM) -> Task:
        return Task(
            id=orm.id,
            title=orm.title,
            description=orm.description,
            status=TaskStatus(orm.status),
            priority=Priority(orm.priority),
            task_type=None,  # ignorado MVP
            project_id=orm.project_id,
            due_date=date.fromisoformat(orm.due_date) if orm.due_date else None,
            completed_at=orm.completed_at,
            created_at=orm.created_at,
        )

    async def get_by_id(self, task_id: uuid.UUID) -> Task | None:
        result = await self.session.execute(select(TaskORM).where(TaskORM.id == task_id))
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        return self._to_domain(orm)

    async def save(self, task: Task) -> None:
        # Simplificado para MVP: usar merge
        orm = TaskORM(
            id=task.id,
            title=task.title,
            description=task.description,
            status=task.status.value,
            priority=task.priority.value,
            project_id=task.project_id,
            due_date=task.due_date.isoformat() if task.due_date else None,
            created_at=task.created_at,
        )
        await self.session.merge(orm)
        # Flush para enviar as mudanças ao UoW mas não comitar
        await self.session.flush()

    async def find_active(
        self,
        status_filter: list[str] | None = None,
        limit: int = 100,
    ) -> Sequence[Task]:
        stmt = select(TaskORM)
        if status_filter:
            stmt = stmt.where(TaskORM.status.in_(status_filter))
        stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return [self._to_domain(r) for r in result.scalars().all()]

    async def search_full_text(self, query: str, limit: int = 20) -> Sequence[Task]:
        # Busca básica com LIKE no SQLite
        like_q = f"%{query}%"
        stmt = select(TaskORM).where(
            or_(TaskORM.title.like(like_q), TaskORM.description.like(like_q))
        ).limit(limit)
        result = await self.session.execute(stmt)
        return [self._to_domain(r) for r in result.scalars().all()]

    async def find_by_embedding(self, embedding: list[float], top_k: int = 8) -> Sequence[Task]:
        # Para MVP com SQLite padrão, a busca por embedding não é possível nativamente.
        # SQLite não tem suporte vetorial out-of-the-box (requer sqlite-vss).
        # Vamos retornar uma lista vazia ou fazer um mock, já que o MVP foca no fluxo e LLMs textuais.
        # Em PostgreSQL (Neon) usaríamos pgvector.
        return []
