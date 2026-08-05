"""Testes de integração para SuggestFollowUpUseCase — UC-6."""

import uuid
from datetime import datetime

import pytest

from taskflow.application.dto.commands import SuggestFollowUpCommand
from taskflow.application.use_cases.suggest_follow_up import SuggestFollowUpUseCase
from taskflow.domain.entities.task import Task
from taskflow.domain.value_objects.enums import FollowUpChannel, Priority, TaskStatus
from tests.fakes import FakeLLMProvider, FakeTaskRepository


def make_uc(llm_body: str = "Corpo do email gerado") -> tuple[SuggestFollowUpUseCase, FakeTaskRepository, FakeLLMProvider]:
    task_repo = FakeTaskRepository()
    llm = FakeLLMProvider(follow_up_body=llm_body)
    uc = SuggestFollowUpUseCase(task_repo=task_repo, llm=llm)
    return uc, task_repo, llm


class TestSuggestFollowUp:
    """Testes da UC-6 (Follow-up via LLM)."""

    @pytest.mark.asyncio
    async def test_draft_follow_up_calls_llm(self) -> None:
        """Verifica se o caso de uso chama o LLM corretamente."""
        uc, repo, llm = make_uc(llm_body="Olá, qual o status?")
        
        task = Task(
            id=uuid.uuid4(),
            title="Aprovação pendente",
            status=TaskStatus.WAITING_ON_OTHERS,
            priority=Priority.HIGH,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            last_activity_at=datetime.utcnow(),
        )
        await repo.save(task)

        cmd = SuggestFollowUpCommand(
            task_id=task.id,
            channel=FollowUpChannel.EMAIL,
            tone="professional",
        )
        
        draft = await uc.execute(cmd)
        
        assert draft.body == "Olá, qual o status?"
        assert draft.channel == FollowUpChannel.EMAIL
        assert draft.tone == "professional"
        assert draft.subject == "Acompanhamento: Aprovação pendente"
        
        # Verifica se o contexto foi passado pro LLM
        assert len(llm.calls) == 1
        call = llm.calls[0]
        assert call["method"] == "draft_follow_up"
        assert call["task"]["title"] == "Aprovação pendente"

    @pytest.mark.asyncio
    async def test_non_existent_task_raises(self) -> None:
        uc, _, _ = make_uc()
        cmd = SuggestFollowUpCommand(
            task_id=uuid.uuid4(),
            channel=FollowUpChannel.EMAIL,
        )
        with pytest.raises(ValueError):
            await uc.execute(cmd)
