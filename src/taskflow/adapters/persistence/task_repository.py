from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date, datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from taskflow.adapters.persistence.models import (
    SourceItemORM,
    TaskEvidenceORM,
    TaskORM,
    TaskStatusHistoryORM,
    TaskUpdateORM,
)
from taskflow.domain.entities.task import Task, TaskEvidence, TaskStatusHistory, TaskUpdate
from taskflow.domain.ports.ports import TaskRepository
from taskflow.domain.value_objects.enums import (
    ActorType,
    EvidenceRole,
    Priority,
    TaskStatus,
    TaskType,
)


class SqlAlchemyTaskRepository(TaskRepository):
    """Durable aggregate repository for tasks and their audit children."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, orm: TaskORM) -> Task:
        return Task(
            id=orm.id,
            title=orm.title,
            description=orm.description,
            status=TaskStatus(orm.status),
            priority=Priority(orm.priority),
            task_type=TaskType(orm.task_type) if orm.task_type else None,
            project_id=orm.project_id,
            parent_task_id=orm.parent_task_id,
            waiting_on_id=orm.waiting_on_id,
            due_date=date.fromisoformat(orm.due_date) if orm.due_date else None,
            due_date_source=orm.due_date_source or "manual",
            estimated_effort_minutes=orm.estimated_effort_minutes,
            snooze_until=orm.snooze_until,
            auto_created=orm.auto_created,
            llm_confidence=orm.llm_confidence,
            last_activity_at=orm.last_activity_at,
            last_interaction_at=orm.last_interaction_at,
            completed_at=orm.completed_at,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    async def _hydrate(self, task: Task) -> Task:
        evidence_result = await self.session.execute(
            select(TaskEvidenceORM)
            .where(TaskEvidenceORM.task_id == task.id)
            .order_by(TaskEvidenceORM.created_at, TaskEvidenceORM.id)
        )
        task.evidence = [
            TaskEvidence(
                id=row.id,
                task_id=row.task_id,
                source_item_id=row.source_item_id,
                signal_id=row.signal_id,
                quote=row.quote,
                role=EvidenceRole(row.role),
                created_at=row.created_at,
            )
            for row in evidence_result.scalars().all()
        ]

        history_result = await self.session.execute(
            select(TaskStatusHistoryORM)
            .where(TaskStatusHistoryORM.task_id == task.id)
            .order_by(TaskStatusHistoryORM.created_at, TaskStatusHistoryORM.id)
        )
        task.status_history = [
            TaskStatusHistory(
                id=row.id,
                task_id=row.task_id,
                from_status=TaskStatus(row.from_status) if row.from_status else None,
                to_status=TaskStatus(row.to_status),
                actor=ActorType(row.actor),
                reason=row.reason,
                signal_id=row.signal_id,
                is_undone=row.is_undone,
                undone_at=row.undone_at,
                snapshot=row.snapshot,
                created_at=row.created_at,
            )
            for row in history_result.scalars().all()
        ]

        updates_result = await self.session.execute(
            select(TaskUpdateORM)
            .where(TaskUpdateORM.task_id == task.id)
            .order_by(TaskUpdateORM.created_at, TaskUpdateORM.id)
        )
        task.updates = [
            TaskUpdate(
                id=row.id,
                task_id=row.task_id,
                content=row.content,
                source=row.source,
                source_item_id=row.source_item_id,
                signal_id=row.signal_id,
                created_at=row.created_at,
            )
            for row in updates_result.scalars().all()
        ]
        return task

    async def _hydrate_rows(self, rows: Sequence[TaskORM]) -> list[Task]:
        return [await self._hydrate(self._to_domain(row)) for row in rows]

    async def get_by_id(self, task_id: uuid.UUID) -> Task | None:
        result = await self.session.execute(select(TaskORM).where(TaskORM.id == task_id))
        orm = result.scalar_one_or_none()
        return None if orm is None else await self._hydrate(self._to_domain(orm))

    async def save(self, task: Task) -> None:
        await self.session.merge(
            TaskORM(
                id=task.id,
                title=task.title,
                description=task.description,
                status=task.status.value,
                priority=task.priority.value,
                task_type=task.task_type.value if task.task_type else None,
                project_id=task.project_id,
                parent_task_id=task.parent_task_id,
                waiting_on_id=task.waiting_on_id,
                due_date=task.due_date.isoformat() if task.due_date else None,
                due_date_source=task.due_date_source,
                estimated_effort_minutes=task.estimated_effort_minutes,
                snooze_until=task.snooze_until,
                auto_created=task.auto_created,
                llm_confidence=task.llm_confidence,
                last_activity_at=task.last_activity_at,
                last_interaction_at=task.last_interaction_at,
                completed_at=task.completed_at,
                created_at=task.created_at,
                updated_at=task.updated_at,
            )
        )
        await self.session.flush()

        for evidence in task.evidence:
            await self.session.merge(
                TaskEvidenceORM(
                    id=evidence.id,
                    task_id=task.id,
                    source_item_id=evidence.source_item_id,
                    signal_id=evidence.signal_id,
                    quote=evidence.quote,
                    role=evidence.role.value,
                    created_at=evidence.created_at,
                )
            )
        for history in task.status_history:
            await self.session.merge(
                TaskStatusHistoryORM(
                    id=history.id,
                    task_id=task.id,
                    from_status=history.from_status.value if history.from_status else None,
                    to_status=history.to_status.value,
                    actor=history.actor.value,
                    reason=history.reason,
                    signal_id=history.signal_id,
                    is_undone=history.is_undone,
                    undone_at=history.undone_at,
                    snapshot=history.snapshot,
                    created_at=history.created_at,
                )
            )
        for update in task.updates:
            await self.session.merge(
                TaskUpdateORM(
                    id=update.id,
                    task_id=task.id,
                    content=update.content,
                    source=update.source,
                    source_item_id=update.source_item_id,
                    signal_id=update.signal_id,
                    created_at=update.created_at,
                )
            )
        await self.session.flush()

    async def find_active(
        self,
        status_filter: list[str] | None = None,
        limit: int = 100,
    ) -> Sequence[Task]:
        active = status_filter or [
            TaskStatus.INBOX.value,
            TaskStatus.OPEN.value,
            TaskStatus.IN_PROGRESS.value,
            TaskStatus.WAITING_ON_OTHERS.value,
            TaskStatus.BLOCKED.value,
        ]
        result = await self.session.execute(
            select(TaskORM)
            .where(TaskORM.status.in_(active))
            .order_by(TaskORM.updated_at.desc(), TaskORM.id)
            .limit(limit)
        )
        return await self._hydrate_rows(result.scalars().all())

    async def search_full_text(self, query: str, limit: int = 20) -> Sequence[Task]:
        like_query = f"%{query}%"
        statement = (
            select(TaskORM)
            .outerjoin(TaskEvidenceORM, TaskEvidenceORM.task_id == TaskORM.id)
            .where(
                or_(
                    TaskORM.title.like(like_query),
                    TaskORM.description.like(like_query),
                    TaskEvidenceORM.quote.like(like_query),
                )
            )
            .distinct()
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return await self._hydrate_rows(result.scalars().all())

    async def find_by_embedding(
        self, embedding: list[float], top_k: int = 8
    ) -> Sequence[Task]:
        return ()

    async def find_by_source_context(
        self,
        conversation_id: str | None,
        external_id: str | None,
        limit: int = 8,
    ) -> Sequence[Task]:
        predicates = []
        if conversation_id:
            predicates.append(SourceItemORM.conversation_id == conversation_id)
        if external_id:
            predicates.append(SourceItemORM.external_id == external_id)
        if not predicates:
            return ()
        result = await self.session.execute(
            select(TaskORM)
            .join(TaskEvidenceORM, TaskEvidenceORM.task_id == TaskORM.id)
            .join(SourceItemORM, SourceItemORM.id == TaskEvidenceORM.source_item_id)
            .where(or_(*predicates))
            .distinct()
            .limit(limit)
        )
        return await self._hydrate_rows(result.scalars().all())

    async def find_by_project(self, project_id: uuid.UUID) -> Sequence[Task]:
        result = await self.session.execute(
            select(TaskORM).where(TaskORM.project_id == project_id)
        )
        return await self._hydrate_rows(result.scalars().all())

    async def find_by_stakeholder(self, stakeholder_id: uuid.UUID) -> Sequence[Task]:
        result = await self.session.execute(
            select(TaskORM).where(
                or_(
                    TaskORM.requester_id == stakeholder_id,
                    TaskORM.waiting_on_id == stakeholder_id,
                )
            )
        )
        return await self._hydrate_rows(result.scalars().all())

    async def find_stale(self, cutoff: datetime) -> Sequence[Task]:
        result = await self.session.execute(
            select(TaskORM).where(
                TaskORM.last_activity_at < cutoff,
                TaskORM.status.not_in(
                    [TaskStatus.DONE.value, TaskStatus.CANCELLED.value]
                ),
            )
        )
        return await self._hydrate_rows(result.scalars().all())
