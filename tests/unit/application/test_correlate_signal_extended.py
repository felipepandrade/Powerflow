"""Testes adicionais para CorrelateSignalUseCase — cobrindo branches de P1.

Complementa tests/unit/application/test_correlate_signal.py.
Cobre: fonte redatada (privacy block), guardrails, _validate_assessments,
_apply_decision ATTACH_CONTEXT / UPDATE / TRANSITION, discard path,
_extract_decision_kind para todos os RelationType, _build_proposal.
"""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import datetime

import pytest

from taskflow.application.dto.commands import CorrelateSignalCommand
from taskflow.application.use_cases.correlate_signal import CorrelateSignalUseCase
from taskflow.domain.entities.source import Signal, SourceItem
from taskflow.domain.entities.task import Task
from taskflow.domain.policies.candidate_fusion import CandidateFusion
from taskflow.domain.policies.correlation_policy import CorrelationPolicy
from taskflow.domain.value_objects.enums import (
    DecisionKind,
    Priority,
    RelationType,
    SignalState,
    SignalType,
    SourceKind,
    TaskStatus,
)
from tests.fakes import (
    FakeEmbeddingProvider,
    FakeLLMProvider,
    FakeSignalRepository,
    FakeTaskRepository,
    FakeUnitOfWork,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_uc(
    llm: FakeLLMProvider | None = None,
    allow_auto_done: bool = True,
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
        policy=CorrelationPolicy(allow_auto_done=allow_auto_done),
    )
    return uc, sig_repo, task_repo, llm


def make_signal(payload: dict, evidence_quote: str = "Evidência real") -> Signal:
    return Signal(
        id=uuid.uuid4(),
        source_item_id=uuid.uuid4(),
        signal_type=SignalType.COMMITMENT,
        extraction_conf=0.95,
        state=SignalState.PENDING_CORRELATION,
        payload=payload,
        evidence_quote=evidence_quote,
    )


def make_source_item(
    signal: Signal,
    is_redacted: bool = False,
    body_preview: str = "Evidência real do email",
) -> SourceItem:
    return SourceItem(
        id=signal.source_item_id,
        kind=SourceKind.EMAIL,
        external_id="ext-001",
        channel="email",
        revision_hash="abc123",
        occurred_at=datetime.utcnow(),
        body_preview=body_preview,
        is_redacted=is_redacted,
    )


def make_task(status: TaskStatus = TaskStatus.INBOX) -> Task:
    return Task(id=uuid.uuid4(), title="Tarefa Alvo", status=status, priority=Priority.MEDIUM)


# ── Privacy block ─────────────────────────────────────────────────────────────

class TestPrivacyBlock:
    @pytest.mark.asyncio
    async def test_redacted_source_skips_llm_and_routes_to_triage(self) -> None:
        llm = FakeLLMProvider()
        uc, sig_repo, _, _ = make_uc(llm=llm)

        sig = make_signal({"title": "Reunião confidencial"})
        source = make_source_item(sig, is_redacted=True)
        await sig_repo.save(sig)
        await sig_repo.save(source)

        res = await uc.execute(CorrelateSignalCommand(signal_id=sig.id))

        # LLM não deve ser chamado
        correlate_calls = [c for c in llm.calls if c["method"] == "correlate"]
        assert len(correlate_calls) == 0

        # Decisão deve ir para triage (guardrail de privacidade)
        assert res.action == "triage"

    @pytest.mark.asyncio
    async def test_non_redacted_source_does_not_block(self) -> None:
        llm = FakeLLMProvider(
            correlate_response={"assessments": [{"relation": "unrelated", "confidence": 0.92}]}
        )
        uc, sig_repo, _, _ = make_uc(llm=llm)

        sig = make_signal({"title": "Reunião normal"})
        source = make_source_item(sig, is_redacted=False)
        await sig_repo.save(sig)
        await sig_repo.save(source)

        res = await uc.execute(CorrelateSignalCommand(signal_id=sig.id))
        assert res.action == "apply"


# ── Signal não encontrado / não pendente ──────────────────────────────────────

class TestSignalValidation:
    @pytest.mark.asyncio
    async def test_signal_not_found_raises(self) -> None:
        uc, _, _, _ = make_uc()
        with pytest.raises(ValueError, match="not found"):
            await uc.execute(CorrelateSignalCommand(signal_id=uuid.uuid4()))

    @pytest.mark.asyncio
    async def test_signal_not_pending_raises(self) -> None:
        uc, sig_repo, _, _ = make_uc()
        sig = make_signal({"title": "X"})
        sig.state = SignalState.RESOLVED
        await sig_repo.save(sig)

        with pytest.raises(ValueError, match="not pending"):
            await uc.execute(CorrelateSignalCommand(signal_id=sig.id))

    @pytest.mark.asyncio
    async def test_force_triage_on_resolved_signal_works(self) -> None:
        uc, sig_repo, _, _ = make_uc()
        sig = make_signal({"title": "X"})
        sig.state = SignalState.RESOLVED
        await sig_repo.save(sig)

        # force_triage deve contornar a checagem de estado
        res = await uc.execute(CorrelateSignalCommand(signal_id=sig.id, force_triage=True))
        assert res.action == "triage"


# ── _validate_assessments (método estático) ───────────────────────────────────

class TestValidateAssessments:
    def test_not_a_list_returns_schema_guardrail(self) -> None:
        valid, rejected = CorrelateSignalUseCase._validate_assessments(None, set())
        assert valid == []
        assert any(r["guardrail"] == "assessment_schema" for r in rejected)

    def test_non_dict_item_is_rejected(self) -> None:
        valid, rejected = CorrelateSignalUseCase._validate_assessments(["not_a_dict"], set())
        assert valid == []
        assert rejected[0]["reason"] == "not_an_object"

    def test_invalid_relation_is_rejected(self) -> None:
        raw = [{"relation": "completely_invalid", "confidence": 0.9}]
        valid, rejected = CorrelateSignalUseCase._validate_assessments(raw, set())
        assert valid == []
        assert "invalid_relation_or_confidence" in rejected[0]["reason"]

    def test_non_numeric_confidence_is_rejected(self) -> None:
        raw = [{"relation": "same_task", "confidence": "high"}]
        valid, rejected = CorrelateSignalUseCase._validate_assessments(raw, set())
        assert valid == []
        assert "invalid_relation_or_confidence" in rejected[0]["reason"]

    def test_confidence_out_of_range_is_rejected(self) -> None:
        raw = [{"relation": "same_task", "confidence": 1.5}]
        valid, rejected = CorrelateSignalUseCase._validate_assessments(raw, set())
        assert valid == []
        assert rejected[0]["reason"] == "confidence_out_of_range"

    def test_task_id_not_in_candidates_is_rejected(self) -> None:
        raw = [{"relation": "same_task", "confidence": 0.9, "task_id": str(uuid.uuid4())}]
        valid, rejected = CorrelateSignalUseCase._validate_assessments(raw, set())
        assert valid == []
        assert "assessment_task_not_retrieved" in rejected[0]["reason"]

    def test_valid_assessment_without_task_id_is_accepted(self) -> None:
        raw = [{"relation": "unrelated", "confidence": 0.92}]
        valid, rejected = CorrelateSignalUseCase._validate_assessments(raw, set())
        assert len(valid) == 1
        assert rejected == []

    def test_valid_assessment_with_matching_task_id_is_accepted(self) -> None:
        tid = uuid.uuid4()
        raw = [{"relation": "same_task", "confidence": 0.88, "task_id": str(tid)}]
        valid, rejected = CorrelateSignalUseCase._validate_assessments(raw, {tid})
        assert len(valid) == 1
        assert rejected == []

    def test_mixed_assessments_separates_valid_from_rejected(self) -> None:
        tid = uuid.uuid4()
        raw = [
            {"relation": "same_task", "confidence": 0.85, "task_id": str(tid)},   # válido
            {"relation": "bad_relation", "confidence": 0.9},                       # rejeitado
            {"relation": "unrelated", "confidence": 1.5},                          # rejeitado (fora de range)
        ]
        valid, rejected = CorrelateSignalUseCase._validate_assessments(raw, {tid})
        assert len(valid) == 1
        assert len(rejected) == 2


# ── Discard path ──────────────────────────────────────────────────────────────

class TestDiscardPath:
    @pytest.mark.asyncio
    async def test_noise_signal_is_discarded(self) -> None:
        """Sinal com confiança muito baixa (< CORR_DISCARD_MAX=0.55) deve ser descartado.

        Para o LLM ser chamado, precisa haver ao menos 1 candidato recuperado.
        Usamos full_text_search: título do sinal = título da tarefa → R5_lexical match.
        NÃO usamos task_id explícito para evitar o atalho determinístico R3.
        """
        llm = FakeLLMProvider(
            correlate_response={"assessments": [{"relation": "unrelated", "confidence": 0.30}]}
        )
        uc, sig_repo, task_repo, _ = make_uc(llm=llm)

        task = Task(
            id=uuid.uuid4(),
            title="Candidato para spam",
            status=TaskStatus.INBOX,
            priority=Priority.MEDIUM,
        )
        await task_repo.save(task)

        # Sinal com título = título do task → full_text_search retorna candidato
        sig = make_signal({"title": "Candidato para spam"})
        await sig_repo.save(sig)

        res = await uc.execute(CorrelateSignalCommand(signal_id=sig.id))
        # LLM foi chamado, confidence=0.30 < 0.55 → discard
        assert res.action == "discard"
        assert res.applied_task_id is None


# ── ATTACH_CONTEXT auto-apply ─────────────────────────────────────────────────

class TestAttachContext:
    @pytest.mark.asyncio
    async def test_related_context_attaches_evidence_to_task(self) -> None:
        task = make_task(status=TaskStatus.IN_PROGRESS)
        llm = FakeLLMProvider(
            correlate_response={
                "assessments": [
                    {
                        "relation": RelationType.RELATED_CONTEXT.value,
                        "confidence": 0.75,
                        "task_id": str(task.id),
                    }
                ]
            }
        )
        uc, sig_repo, task_repo, _ = make_uc(llm=llm)
        await task_repo.save(task)

        sig = make_signal({"title": "Contexto adicional"})
        source = make_source_item(sig)
        await sig_repo.save(sig)
        await sig_repo.save(source)

        res = await uc.execute(CorrelateSignalCommand(signal_id=sig.id))

        assert res.decision_kind == DecisionKind.ATTACH_CONTEXT
        assert res.action == "apply"
        assert res.applied_task_id == task.id


# ── _extract_decision_kind para todos os RelationType ────────────────────────

class TestExtractDecisionKind:
    def _make_uc_instance(self) -> CorrelateSignalUseCase:
        return CorrelateSignalUseCase(
            task_repo=FakeTaskRepository(),
            signal_repo=FakeSignalRepository(),
            llm=FakeLLMProvider(),
            embedder=FakeEmbeddingProvider(),
            uow=FakeUnitOfWork(),
        )

    def _assessment(self, relation: RelationType, confidence: float = 0.9) -> list[dict]:
        return [{"relation": relation.value, "confidence": confidence}]

    def test_same_task_maps_to_update_existing(self) -> None:
        uc = self._make_uc_instance()
        result = uc._extract_decision_kind(self._assessment(RelationType.SAME_TASK))
        assert result == DecisionKind.UPDATE_EXISTING

    def test_status_update_maps_to_transition_existing(self) -> None:
        uc = self._make_uc_instance()
        result = uc._extract_decision_kind(self._assessment(RelationType.STATUS_UPDATE))
        assert result == DecisionKind.TRANSITION_EXISTING

    def test_due_date_change_maps_to_update_existing(self) -> None:
        uc = self._make_uc_instance()
        result = uc._extract_decision_kind(self._assessment(RelationType.DUE_DATE_CHANGE))
        assert result == DecisionKind.UPDATE_EXISTING

    def test_scope_change_maps_to_split(self) -> None:
        uc = self._make_uc_instance()
        result = uc._extract_decision_kind(self._assessment(RelationType.SCOPE_CHANGE))
        assert result == DecisionKind.SPLIT

    def test_subtask_of_maps_to_split(self) -> None:
        uc = self._make_uc_instance()
        result = uc._extract_decision_kind(self._assessment(RelationType.SUBTASK_OF))
        assert result == DecisionKind.SPLIT

    def test_blocks_maps_to_transition_existing(self) -> None:
        uc = self._make_uc_instance()
        result = uc._extract_decision_kind(self._assessment(RelationType.BLOCKS))
        assert result == DecisionKind.TRANSITION_EXISTING

    def test_duplicate_maps_to_merge(self) -> None:
        uc = self._make_uc_instance()
        result = uc._extract_decision_kind(self._assessment(RelationType.DUPLICATE_OF))
        assert result == DecisionKind.MERGE_DUPLICATE

    def test_related_context_maps_to_attach_context(self) -> None:
        uc = self._make_uc_instance()
        result = uc._extract_decision_kind(self._assessment(RelationType.RELATED_CONTEXT))
        assert result == DecisionKind.ATTACH_CONTEXT

    def test_unrelated_maps_to_new_task(self) -> None:
        uc = self._make_uc_instance()
        result = uc._extract_decision_kind(self._assessment(RelationType.UNRELATED))
        assert result == DecisionKind.NEW_TASK

    def test_empty_assessments_defaults_to_new_task(self) -> None:
        uc = self._make_uc_instance()
        result = uc._extract_decision_kind([])
        assert result == DecisionKind.NEW_TASK


# ── Guardrails: literal evidence e candidate identity ────────────────────────

class TestGuardrails:
    @pytest.mark.asyncio
    async def test_evidence_quote_not_in_source_triggers_guardrail_triage(self) -> None:
        """Quote não encontrada no conteúdo da fonte → force triage."""
        task = make_task()
        llm = FakeLLMProvider(
            correlate_response={"assessments": [{"relation": "unrelated", "confidence": 0.95}]}
        )
        uc, sig_repo, task_repo, _ = make_uc(llm=llm)
        await task_repo.save(task)

        # evidence_quote que NÃO está no body_preview
        sig = make_signal({"title": "X"}, evidence_quote="Frase ausente no email")
        source = make_source_item(sig, body_preview="Conteúdo completamente diferente")
        await sig_repo.save(sig)
        await sig_repo.save(source)

        res = await uc.execute(CorrelateSignalCommand(signal_id=sig.id))
        # Guardrail de evidência literal → triage
        assert res.action == "triage"

    @pytest.mark.asyncio
    async def test_blocked_by_safety_flag_forces_triage(self) -> None:
        """Sinal com blocked_by_safety=True deve ir para triage."""
        llm = FakeLLMProvider(
            correlate_response={"assessments": [{"relation": "unrelated", "confidence": 0.95}]}
        )
        uc, sig_repo, _, _ = make_uc(llm=llm)

        sig = make_signal({"title": "X", "blocked_by_safety": True})
        await sig_repo.save(sig)

        res = await uc.execute(CorrelateSignalCommand(signal_id=sig.id))
        assert res.action == "triage"


# ── _build_proposal ───────────────────────────────────────────────────────────

class TestBuildProposal:
    @pytest.mark.asyncio
    async def test_triage_proposal_has_correct_kind_for_new_task(self) -> None:
        llm = FakeLLMProvider(
            correlate_response={"assessments": [{"relation": "unrelated", "confidence": 0.80}]}
        )
        uc, sig_repo, _, _ = make_uc(llm=llm)
        sig = make_signal({"title": "Nova tarefa via triage"})
        await sig_repo.save(sig)

        res = await uc.execute(CorrelateSignalCommand(signal_id=sig.id, force_triage=True))
        assert res.proposal_id is not None

    @pytest.mark.asyncio
    async def test_correlate_run_is_audited_in_signal_repo(self) -> None:
        """Deve salvar CorrelationRun no repositório de sinais."""
        llm = FakeLLMProvider(
            correlate_response={"assessments": [{"relation": "unrelated", "confidence": 0.92}]}
        )
        uc, sig_repo, _, _ = make_uc(llm=llm)
        sig = make_signal({"title": "Auditoria"})
        await sig_repo.save(sig)

        from taskflow.domain.entities.source import CorrelationRun
        await uc.execute(CorrelateSignalCommand(signal_id=sig.id))

        runs = [item for item in sig_repo._items if isinstance(item, CorrelationRun)]
        assert len(runs) == 1
        assert runs[0].signal_id == sig.id
