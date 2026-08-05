import uuid

from fastapi import APIRouter, Depends, HTTPException

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
