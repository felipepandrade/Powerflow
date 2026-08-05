import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from taskflow.adapters.api.schemas.schemas import (
    FollowUpResponse,
    ManageTaskRequest,
    ManageTaskResponse,
    TaskListResponse,
    TaskSchema,
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
from taskflow.domain.value_objects.enums import TaskStatus

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    uc: GetActiveTasksUseCase = Depends(get_active_tasks_use_case),
) -> TaskListResponse:
    """Retorna a lista de tarefas ativas."""
    try:
        tasks = await uc.execute()
        # Convert raw domain models/dicts to Pydantic schema dicts safely
        schema_data = []
        for t in tasks:
            # tasks is expected to be a sequence of objects with these attributes
            schema_data.append(TaskSchema.model_validate(t))
        return TaskListResponse(data=schema_data, count=len(schema_data))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{task_id}", response_model=ManageTaskResponse)
async def manage_task(
    task_id: uuid.UUID,
    req: ManageTaskRequest,
    uc: ManageTaskUseCase = Depends(get_manage_task_use_case),
) -> ManageTaskResponse:
    """Atualiza metadados ou status de uma tarefa."""
    try:
        new_status = TaskStatus(req.status) if req.status else None
        
        await uc.execute(
            task_id=task_id,
            action="update",
            new_status=new_status,
            title=req.title,
            description=req.description,
        )
        return ManageTaskResponse(
            success=True,
            message="Task updated successfully.",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{task_id}/follow-up", response_model=FollowUpResponse)
async def suggest_follow_up(
    task_id: uuid.UUID,
    uc: SuggestFollowUpUseCase = Depends(get_suggest_follow_up_use_case),
) -> FollowUpResponse:
    """Gera um texto de follow-up para uma tarefa usando LLM."""
    try:
        draft = await uc.execute(task_id=task_id, tone="cordial")
        return FollowUpResponse(
            draft_text=draft,
            task_id=str(task_id),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stale")
async def get_stale_tasks(
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    """Retorna o diagnóstico de tarefas envelhecidas e sugestões de cobrança."""
    from taskflow.adapters.persistence.unit_of_work import SqlAlchemyUnitOfWork
    from taskflow.application.use_cases.evaluate_staleness import EvaluateStalenessUseCase

    uow = SqlAlchemyUnitOfWork(session)
    uc = EvaluateStalenessUseCase(session, uow)
    return await uc.execute()


@router.get("/{task_id}/timeline")
async def get_task_timeline(
    task_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Retorna a linha do tempo completa da tarefa com auditoria."""
    from sqlalchemy import select
    from taskflow.adapters.persistence.models import TaskORM, TaskStatusHistoryORM, TaskUpdateORM

    task = await session.get(TaskORM, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")

    stmt_h = select(TaskStatusHistoryORM).where(TaskStatusHistoryORM.task_id == task_id).order_by(TaskStatusHistoryORM.created_at.asc())
    res_h = await session.execute(stmt_h)
    history = res_h.scalars().all()

    stmt_u = select(TaskUpdateORM).where(TaskUpdateORM.task_id == task_id).order_by(TaskUpdateORM.created_at.asc())
    res_u = await session.execute(stmt_u)
    updates = res_u.scalars().all()

    timeline_items = []
    for h in history:
        timeline_items.append({
            "id": str(h.id),
            "type": "status_change",
            "from_status": h.from_status,
            "to_status": h.to_status,
            "actor": h.actor,
            "timestamp": h.created_at.isoformat(),
        })

    for u in updates:
        timeline_items.append({
            "id": str(u.id),
            "type": "update_note",
            "content": u.content,
            "author": u.author,
            "timestamp": u.created_at.isoformat(),
        })

    timeline_items.sort(key=lambda x: x["timestamp"])

    return {
        "task_id": str(task.id),
        "title": task.title,
        "status": task.status,
        "created_at": task.created_at.isoformat(),
        "timeline": timeline_items,
    }


@router.post("/{task_id}/undo/{history_id}")
async def undo_task_transition(
    task_id: uuid.UUID,
    history_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Reverte uma transição de estado de tarefa com base no histórico auditável (RF-G.8 Undo)."""
    from taskflow.adapters.persistence.models import TaskORM, TaskStatusHistoryORM

    task = await session.get(TaskORM, task_id)
    history = await session.get(TaskStatusHistoryORM, history_id)

    if not task or not history or history.task_id != task_id:
        raise HTTPException(status_code=404, detail="Histórico de transição não encontrado para esta tarefa.")

    # Reverter o status da tarefa para o estado original
    task.status = history.from_status
    await session.commit()

    return {
        "status": "success",
        "message": f"Transição revertida com sucesso. Status restaurado para '{history.from_status}'.",
        "task_id": str(task_id),
        "current_status": task.status,
    }
