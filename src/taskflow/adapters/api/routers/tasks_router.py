from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taskflow.adapters.api.schemas.schemas import (
    FollowUpResponse,
    ManageTaskRequest,
    ManageTaskResponse,
    TaskListResponse,
    TaskSchema,
)
from taskflow.adapters.persistence.models import (
    SourceItemORM,
    TaskEvidenceORM,
    TaskORM,
    TaskStatusHistoryORM,
    TaskUpdateORM,
)
from taskflow.adapters.persistence.signal_repository import SqlAlchemySignalRepository
from taskflow.adapters.persistence.task_repository import SqlAlchemyTaskRepository
from taskflow.adapters.persistence.unit_of_work import SqlAlchemyUnitOfWork
from taskflow.application.dto.commands import (
    SuggestFollowUpCommand,
    TransitionTaskCommand,
    UndoAutoActionCommand,
    UpdateTaskCommand,
)
from taskflow.application.use_cases.get_active_tasks import GetActiveTasksUseCase
from taskflow.application.use_cases.manage_task import ManageTaskUseCase
from taskflow.application.use_cases.suggest_follow_up import SuggestFollowUpUseCase
from taskflow.config.container import (
    get_active_tasks_use_case,
    get_db_session,
    get_manage_task_use_case,
    get_suggest_follow_up_use_case,
)
from taskflow.domain.value_objects.enums import FollowUpChannel

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    uc: GetActiveTasksUseCase = Depends(get_active_tasks_use_case),
) -> TaskListResponse:
    tasks = await uc.execute()
    data = [TaskSchema.model_validate(task) for task in tasks]
    return TaskListResponse(data=data, count=len(data))


@router.patch("/{task_id}", response_model=ManageTaskResponse)
async def manage_task(
    task_id: uuid.UUID,
    request: ManageTaskRequest,
    uc: ManageTaskUseCase = Depends(get_manage_task_use_case),
) -> ManageTaskResponse:
    try:
        if any(
            value is not None
            for value in (
                request.title,
                request.description,
                request.priority,
                request.due_date,
                request.waiting_on_id,
            )
        ):
            await uc.update(
                UpdateTaskCommand(
                    task_id=task_id,
                    title=request.title,
                    description=request.description,
                    priority=request.priority,
                    due_date=request.due_date,
                    waiting_on_id=request.waiting_on_id,
                )
            )
        if request.status is not None:
            await uc.transition(
                TransitionTaskCommand(task_id=task_id, to_status=request.status)
            )
        return ManageTaskResponse(success=True, message="Task updated.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{task_id}/follow-up", response_model=FollowUpResponse)
async def suggest_follow_up(
    task_id: uuid.UUID,
    uc: SuggestFollowUpUseCase = Depends(get_suggest_follow_up_use_case),
) -> FollowUpResponse:
    draft = await uc.execute(
        SuggestFollowUpCommand(
            task_id=task_id,
            channel=FollowUpChannel.EMAIL,
            tone="professional",
        )
    )
    return FollowUpResponse(draft_text=draft.body, task_id=str(task_id))


@router.get("/stale")
async def get_stale_tasks(
    session: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    from taskflow.application.use_cases.evaluate_staleness import EvaluateStalenessUseCase

    use_case = EvaluateStalenessUseCase(session, SqlAlchemyUnitOfWork(session))
    result = await use_case.execute()
    return list(result)


@router.get("/{task_id}/timeline")
async def get_task_timeline(
    task_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    task = await session.get(TaskORM, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    history_result = await session.execute(
        select(TaskStatusHistoryORM)
        .where(TaskStatusHistoryORM.task_id == task_id)
        .order_by(TaskStatusHistoryORM.created_at, TaskStatusHistoryORM.id)
    )
    updates_result = await session.execute(
        select(TaskUpdateORM)
        .where(TaskUpdateORM.task_id == task_id)
        .order_by(TaskUpdateORM.created_at, TaskUpdateORM.id)
    )
    evidence_result = await session.execute(
        select(TaskEvidenceORM, SourceItemORM)
        .join(SourceItemORM, SourceItemORM.id == TaskEvidenceORM.source_item_id)
        .where(TaskEvidenceORM.task_id == task_id, SourceItemORM.is_redacted.is_(False))
        .order_by(TaskEvidenceORM.created_at, TaskEvidenceORM.id)
    )

    timeline: list[dict[str, Any]] = [
        {
            "id": str(row.id),
            "type": "status_change",
            "from_status": row.from_status,
            "to_status": row.to_status,
            "actor": row.actor,
            "reason": row.reason,
            "signal_id": str(row.signal_id) if row.signal_id else None,
            "is_undone": row.is_undone,
            "timestamp": row.created_at.isoformat(),
        }
        for row in history_result.scalars().all()
    ]
    timeline.extend(
        {
            "id": str(row.id),
            "type": "update_note",
            "content": row.content,
            "source": row.source,
            "signal_id": str(row.signal_id) if row.signal_id else None,
            "timestamp": row.created_at.isoformat(),
        }
        for row in updates_result.scalars().all()
    )
    timeline.extend(
        {
            "id": str(row.id),
            "type": "evidence",
            "quote": row.quote,
            "role": row.role,
            "source_item_id": str(row.source_item_id),
            "signal_id": str(row.signal_id) if row.signal_id else None,
            "source_kind": source.kind,
            "source_subject": source.title,
            "source_occurred_at": source.occurred_at.isoformat(),
            "deep_link": source.web_link,
            "timestamp": row.created_at.isoformat(),
        }
        for row, source in evidence_result.all()
    )
    timeline.sort(key=lambda item: str(item["timestamp"]))
    return {
        "task_id": str(task.id),
        "title": task.title,
        "status": task.status,
        "created_at": task.created_at.isoformat(),
        "timeline": timeline,
    }


@router.post("/{task_id}/undo/{history_id}", response_model=TaskSchema)
async def undo_task_transition(
    task_id: uuid.UUID,
    history_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> TaskSchema:
    use_case = ManageTaskUseCase(
        task_repo=SqlAlchemyTaskRepository(session),
        signal_repo=SqlAlchemySignalRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
    )
    try:
        task = await use_case.undo_auto_action(
            UndoAutoActionCommand(task_id=task_id, history_id=history_id)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TaskSchema.model_validate(task)
