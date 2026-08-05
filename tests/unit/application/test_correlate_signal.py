"""Testes de integração para CorrelateSignalUseCase — UC-2."""

import uuid
from datetime import datetime

import pytest

from taskflow.application.dto.commands import CorrelateSignalCommand
from taskflow.application.use_cases.correlate_signal import CorrelateSignalUseCase
from taskflow.domain.entities.source import Signal
from taskflow.domain.entities.task import Task
from taskflow.domain.policies.candidate_fusion import CandidateFusion
from taskflow.domain.policies.correlation_policy import CorrelationPolicy
from taskflow.domain.value_objects.enums import (
    DecisionKind,
    Priority,
    SignalState,
    SignalType,
    TaskStatus,
)
from tests.fakes import (
    FakeEmbeddingProvider,
    FakeLLMProvider,
    FakeSignalRepository,
    FakeTaskRepository,
    FakeUnitOfWork,
)


def make_uc(
    llm: FakeLLMProvider | None = None,
) -> tuple[CorrelateSignalUseCase, FakeSignalRepository, FakeTaskRepository, FakeLLMProvider]:
    task_repo = FakeTaskRepository()
    sig_repo = FakeSignalRepository()
    uow = FakeUnitOfWork()
    llm = llm or FakeLLMProvider()
    embedder = FakeEmbeddingProvider()
    uc = CorrelateSignalUseCase(
        task_repo=task_repo,
        signal_repo=sig_repo,
        llm=llm,
        embedder=embedder,
        uow=uow,
        fusion=CandidateFusion(),
        policy=CorrelationPolicy(),
    )
    return uc, sig_repo, task_repo, llm


def make_signal(payload: dict) -> Signal:
    return Signal(
        id=uuid.uuid4(),
        source_item_id=uuid.uuid4(),
        signal_type=SignalType.COMMITMENT,
        extraction_conf=0.95,
        state=SignalState.PENDING_CORRELATION,
        payload=payload,
    )


class TestCorrelateSignal:
    """Testes da UC-2 (Correlação)."""

    @pytest.mark.asyncio
    async def test_correlate_new_task_auto_applied(self) -> None:
        """Testa o caminho onde o LLM (G2) diz UNRELATED com alta confiança, e a política G3 cria a tarefa."""
        # LLM vai retornar UNRELATED (novo)
        llm = FakeLLMProvider(
            correlate_response={
                "assessments": [
                    {"relation": "unrelated", "confidence": 0.95}
                ]
            }
        )
        uc, sig_repo, task_repo, _ = make_uc(llm=llm)

        sig = make_signal({"title": "Nova feature ABC", "description": "Detalhes"})
        await sig_repo.save(sig)

        res = await uc.execute(CorrelateSignalCommand(signal_id=sig.id))

        assert res.decision_kind == DecisionKind.NEW_TASK
        assert res.action == "apply"
        assert res.applied_task_id is not None
        assert res.proposal_id is None

        # Verifica se a tarefa foi criada
        task = await task_repo.get_by_id(res.applied_task_id)
        assert task.title == "Nova feature ABC"
        assert task.description == "Detalhes"

    @pytest.mark.asyncio
    async def test_correlate_deterministic_shortcut(self) -> None:
        """Testa o atalho determinístico (R3 -> RF-G.3) ignorando LLM."""
        llm = FakeLLMProvider()
        uc, sig_repo, task_repo, _ = make_uc(llm=llm)

        # Tarefa existente
        target_task = Task(
            id=uuid.uuid4(),
            title="Tarefa Alvo",
            status=TaskStatus.INBOX,
            priority=Priority.MEDIUM,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            last_activity_at=datetime.utcnow(),
        )
        await task_repo.save(target_task)

        # Sinal cita explicitamente o ID (R3)
        sig = make_signal({
            "title": "Atualizando a tarefa alvo",
            "task_id": str(target_task.id),
            "progress_note": "Achei um problema.",
        })
        await sig_repo.save(sig)

        res = await uc.execute(CorrelateSignalCommand(signal_id=sig.id))

        # Deve usar atalho -> same_task (UPDATE_EXISTING) -> update é automático em inbox se conf > min?
        # Mas sem LLM a confidence é 1.0 (do atalho).
        assert res.decision_kind == DecisionKind.UPDATE_EXISTING
        assert res.action == "apply"
        assert res.applied_task_id == target_task.id
        
        # O LLM não deve ter sido chamado para correlate
        correlate_calls = [c for c in llm.calls if c["method"] == "correlate"]
        assert len(correlate_calls) == 0

    @pytest.mark.asyncio
    async def test_force_triage_overrides_auto_apply(self) -> None:
        """Testa que force_triage impede a aplicação automática."""
        llm = FakeLLMProvider(
            correlate_response={
                "assessments": [
                    {"relation": "unrelated", "confidence": 0.95}
                ]
            }
        )
        uc, sig_repo, _task_repo, _ = make_uc(llm=llm)
        sig = make_signal({"title": "X"})
        await sig_repo.save(sig)

        res = await uc.execute(CorrelateSignalCommand(signal_id=sig.id, force_triage=True))

        assert res.decision_kind == DecisionKind.NEW_TASK
        assert res.action == "triage"
        assert res.applied_task_id is None
        assert res.proposal_id is not None
