"""Use Case: CorrelateSignal — UC-2.

Pipeline de correlação em 3 estágios:
  G1: Recuperação de candidatos (6 recuperadores)
  G2: Raciocínio relacional (LLM, pode ser pulado)
  G3: Decisão determinística via CorrelationPolicy
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime

import structlog

from taskflow.application.dto.commands import CorrelateSignalCommand, CorrelationRunResult
from taskflow.domain.entities.source import CorrelationRun, Signal
from taskflow.domain.policies.candidate_fusion import CandidateFusion
from taskflow.domain.policies.correlation_policy import CorrelationPolicy
from taskflow.domain.ports.ports import (
    EmbeddingProvider,
    LLMProvider,
    SignalRepository,
    TaskRepository,
    UnitOfWork,
)
from taskflow.domain.value_objects.enums import (
    DecisionKind,
    RelationType,
    SignalState,
)

log = structlog.get_logger()

# Limiares de candidatos — configuráveis via Settings
MAX_CANDIDATES = 8
MIN_CANDIDATES_FOR_LLM = 1


class CorrelateSignalUseCase:
    """UC-2 — Correlação de sinal pendente com tarefas existentes.

    Implementa a pipeline de 3 estágios do RF-G definida no PRD.
    """

    def __init__(
        self,
        task_repo: TaskRepository,
        signal_repo: SignalRepository,
        llm: LLMProvider,
        embedder: EmbeddingProvider,
        uow: UnitOfWork,
        fusion: CandidateFusion | None = None,
        policy: CorrelationPolicy | None = None,
        auto_done_enabled: bool = True,
    ) -> None:
        self._task_repo = task_repo
        self._signal_repo = signal_repo
        self._llm = llm
        self._embedder = embedder
        self._uow = uow
        self._fusion = fusion or CandidateFusion()
        self._policy = policy or CorrelationPolicy(allow_auto_done=auto_done_enabled)

    async def execute(self, cmd: CorrelateSignalCommand) -> CorrelationRunResult:
        """Executa a correlação de um sinal."""
        t0 = time.monotonic()
        run_id = uuid.uuid4()

        log.info("correlate.start", signal_id=str(cmd.signal_id))

        # Busca o sinal
        signal = await self._get_signal(cmd.signal_id)
        if signal is None:
            raise ValueError(f"Sinal {cmd.signal_id} não encontrado.")

        # ─── G1: Recuperação de candidatos ─────────────────────────────────
        candidates, retriever_results = await self._retrieve_candidates(signal)

        # Verifica atalho determinístico RF-G.3
        has_shortcut, shortcut_task_id = self._fusion.has_strong_deterministic_match(
            retriever_results
        )
        skipped_llm = False
        assessments: list[dict] = []
        llm_assessments: dict | None = None

        if not cmd.force_triage and has_shortcut and shortcut_task_id is not None:
            # Atalho: ativa a decisão sem chamar o LLM
            log.info("correlate.shortcut", task_id=str(shortcut_task_id))
            skipped_llm = True
            assessments = [{"relation": RelationType.SAME_TASK.value, "confidence": 1.0, "task_id": str(shortcut_task_id)}]

        elif candidates:
            # ─── G2: Raciocínio relacional via LLM ─────────────────────────
            candidate_cards = self._build_candidate_cards(candidates)
            llm_response = await self._llm.correlate(
                signal=signal.payload,
                candidates=candidate_cards,
            )
            assessments = llm_response.get("assessments", [])
            llm_assessments = llm_response

        # ─── G3: Decisão determinística — CorrelationPolicy ─────────────────
        decision = self._policy.decide(
            decision_kind=self._extract_decision_kind(signal, assessments),
            confidence=self._extract_confidence(signal, assessments),
            primary_task_id=self._extract_primary_task_id(assessments),
            proposed_changes=self._extract_proposed_changes(signal, assessments),
            has_deterministic_match=has_shortcut,
            signal_from_responsible=self._is_from_responsible(signal),
            ambiguity_reason=None,
            assessments=assessments,
        )

        if cmd.force_triage and decision.action == "apply":
            decision.action = "triage"
            decision.policy_rule_id += "_forced"

        latency_ms = int((time.monotonic() - t0) * 1000)

        # Persiste auditoria de correlação (NF-5)
        run = CorrelationRun(
            id=run_id,
            signal_id=cmd.signal_id,
            candidates=[{"task_id": str(r.task_id), "fused_score": r.fused_score} for r in candidates],
            llm_assessments=llm_assessments,
            final_decision=decision.decision_kind.value,
            final_confidence=decision.confidence,
            applied=decision.is_auto_applied,
            routed_to_triage=decision.routed_to_triage,
            policy_rule_id=decision.policy_rule_id,
            skipped_llm=skipped_llm,
            latency_ms=latency_ms,
        )

        applied_task_id: uuid.UUID | None = None
        proposal_id: uuid.UUID | None = None

        async with self._uow:
            await self._signal_repo.save_correlation_run(run)

            if decision.is_auto_applied and not cmd.force_triage:
                applied_task_id = await self._apply_decision(signal, decision)
            elif decision.routed_to_triage:
                proposal_id = await self._create_proposal(signal, decision)

            # Atualiza estado do sinal
            resolved_state = (
                SignalState.RESOLVED if decision.is_auto_applied
                else SignalState.RESOLVED if decision.action == "discard"
                else SignalState.PENDING_CORRELATION
            )
            signal.state = resolved_state
            signal.decision_kind = decision.decision_kind
            signal.decision_conf = decision.confidence
            signal.resolved_at = datetime.utcnow() if decision.action != "triage" else None
            if applied_task_id:
                signal.resolved_task_id = applied_task_id

            await self._signal_repo.save(signal)
            await self._uow.commit()

        log.info(
            "correlate.done",
            signal_id=str(cmd.signal_id),
            action=decision.action,
            rule=decision.policy_rule_id,
            latency_ms=latency_ms,
        )

        return CorrelationRunResult(
            signal_id=cmd.signal_id,
            correlation_run_id=run_id,
            decision_kind=decision.decision_kind,
            policy_rule_id=decision.policy_rule_id,
            action=decision.action,
            confidence=decision.confidence,
            applied_task_id=applied_task_id,
            proposal_id=proposal_id,
            latency_ms=latency_ms,
        )

    async def _get_signal(self, signal_id: uuid.UUID) -> Signal | None:
        """Busca o sinal pelo ID (adaptor: via signal_repo)."""
        pending = await self._signal_repo.get_pending(limit=1000)
        for s in pending:
            if s.id == signal_id:  # type: ignore[union-attr]
                return s  # type: ignore[return-value]
        return None

    async def _retrieve_candidates(
        self,
        signal: Signal,
    ) -> tuple[list, dict[str, list[tuple[uuid.UUID, float]]]]:
        """G1: Recupera candidatos usando os 6 recuperadores RF-G.1.

        Recuperadores:
        - R1_thread: Por conversation_id
        - R2_event: Por event-id vinculado
        - R3_identifier: Por identificadores no payload (task_id explícito)
        - R4_participants: Por participantes comuns
        - R5_lexical: Full-text por título/palavras-chave
        - R6_semantic: Embedding similarity
        """
        retriever_results: dict[str, list[tuple[uuid.UUID, float]]] = {}

        # R3: Identificador explícito no payload
        explicit_task_id = signal.payload.get("task_id")
        if explicit_task_id:
            try:
                task_id = uuid.UUID(explicit_task_id)
                retriever_results["R3_identifier"] = [(task_id, 1.0)]
            except ValueError:
                pass

        # R5: Busca full-text por título/palavras-chave
        query_text = signal.payload.get("title") or signal.payload.get("subject") or ""
        if query_text:
            ft_results = await self._task_repo.search_full_text(query_text, limit=MAX_CANDIDATES)
            if ft_results:
                retriever_results["R5_lexical"] = [
                    (t.id, 0.8) for t in ft_results  # type: ignore[union-attr]
                ]

        # R6: Busca semântica (embedding) — RF-G.1
        signal_text = self._build_signal_text(signal)
        if signal_text:
            try:
                embeddings = await self._embedder.embed([signal_text])
                if embeddings:
                    semantic_results = await self._task_repo.find_by_embedding(
                        embeddings[0], top_k=MAX_CANDIDATES
                    )
                    if semantic_results:
                        retriever_results["R6_semantic"] = [
                            (t.id, 0.7) for t in semantic_results  # type: ignore[union-attr]
                        ]
            except Exception:  # noqa: BLE001
                log.warning("correlate.embedding_failed", signal_id=str(signal.id))

        # Funde os resultados com RRF
        fused = self._fusion.fuse(retriever_results)
        return fused[:MAX_CANDIDATES], retriever_results

    def _build_signal_text(self, signal: Signal) -> str:
        """Extrai texto relevante do payload do sinal para embedding."""
        parts = []
        for key in ("title", "description", "subject", "commitment"):
            val = signal.payload.get(key)
            if val and isinstance(val, str):
                parts.append(val)
        return " ".join(parts)

    def _build_candidate_cards(self, candidates: list) -> list[dict]:
        """Constrói fichas compactas dos candidatos para o LLM RF-G.2."""
        return [
            {
                "task_id": str(c.task_id),
                "fused_score": round(c.fused_score, 4),
                "sources": [s.retriever for s in c.sources],
            }
            for c in candidates
        ]

    def _extract_decision_kind(self, signal: Signal, assessments: list[dict]) -> DecisionKind:
        """Extrai o tipo de decisão do sinal + assessments do LLM."""
        if not assessments:
            return DecisionKind.NEW_TASK

        top = max(assessments, key=lambda a: a.get("confidence", 0.0))
        relation = top.get("relation", "")

        mapping = {
            RelationType.SAME_TASK.value: DecisionKind.UPDATE_EXISTING,
            RelationType.STATUS_UPDATE.value: DecisionKind.TRANSITION_EXISTING,
            RelationType.DUE_DATE_CHANGE.value: DecisionKind.UPDATE_EXISTING,
            RelationType.SCOPE_CHANGE.value: DecisionKind.SPLIT,
            RelationType.SUBTASK_OF.value: DecisionKind.SPLIT,
            RelationType.BLOCKS.value: DecisionKind.TRANSITION_EXISTING,
            RelationType.DUPLICATE_OF.value: DecisionKind.MERGE_DUPLICATE,
            RelationType.RELATED_CONTEXT.value: DecisionKind.ATTACH_CONTEXT,
            RelationType.UNRELATED.value: DecisionKind.NEW_TASK,
        }
        return mapping.get(relation, DecisionKind.NEW_TASK)

    def _extract_confidence(self, signal: Signal, assessments: list[dict]) -> float:
        """Extrai a confiança da decisão."""
        if not assessments:
            return signal.extraction_conf or 0.5
        top = max(assessments, key=lambda a: a.get("confidence", 0.0))
        return float(top.get("confidence", 0.5))

    def _extract_primary_task_id(self, assessments: list[dict]) -> str | None:
        """Extrai o task_id primário dos assessments."""
        if not assessments:
            return None
        top = max(assessments, key=lambda a: a.get("confidence", 0.0))
        return top.get("task_id")

    def _extract_proposed_changes(
        self,
        signal: Signal,
        assessments: list[dict],
    ) -> dict | None:
        """Extrai as mudanças propostas do sinal + assessments."""
        changes: dict = {}

        # Status proposto pelo LLM
        if assessments:
            top = max(assessments, key=lambda a: a.get("confidence", 0.0))
            proposed_status = top.get("proposed_status")
            if proposed_status:
                changes["to_status"] = proposed_status

        # Prazo proposto no payload
        new_due = signal.payload.get("due_date")
        if new_due:
            changes["due_date"] = new_due

        # Nota de progresso
        progress = signal.payload.get("progress_note")
        if progress:
            changes["progress_note"] = progress

        return changes if changes else None

    def _is_from_responsible(self, signal: Signal) -> bool:
        """Verifica se o sinal vem do responsável pela entrega.

        Critério: signal.payload.owner_type == 'me' ou remetente == responsável.
        """
        owner = signal.payload.get("owner_type", "")
        return owner == "me"

    async def _apply_decision(self, signal: Signal, decision) -> uuid.UUID | None:  # type: ignore[no-untyped-def]
        """Aplica a decisão automaticamente (com registro para undo)."""
        from taskflow.domain.value_objects.enums import ActorType
        from taskflow.domain.value_objects.enums import TaskStatus as TS

        if decision.decision_kind == DecisionKind.NEW_TASK:
            return await self._create_task_from_signal(signal, decision)

        if decision.decision_kind in (DecisionKind.UPDATE_EXISTING, DecisionKind.TRANSITION_EXISTING):
            task_id_str = decision.primary_task_id
            if not task_id_str:
                return None
            task = await self._task_repo.get_by_id(uuid.UUID(task_id_str))
            if not task:
                return None

            changes = decision.proposed_changes or {}
            if "to_status" in changes:
                try:
                    new_status = TS(changes["to_status"])
                    from taskflow.domain.entities.task import TaskStatusHistory
                    history = TaskStatusHistory(
                        task_id=task.id,  # type: ignore[union-attr]
                        from_status=task.status,  # type: ignore[union-attr]
                        to_status=new_status,
                        actor=ActorType.SYSTEM,
                        signal_id=signal.id,
                        snapshot=task.snapshot_dict(),  # type: ignore[union-attr]
                    )
                    task.status = new_status  # type: ignore[union-attr]
                    task.status_history.append(history)  # type: ignore[union-attr]
                except ValueError:
                    pass

            task.last_activity_at = datetime.utcnow()  # type: ignore[union-attr]
            await self._task_repo.save(task)
            return task.id  # type: ignore[union-attr]

        if decision.decision_kind == DecisionKind.ATTACH_CONTEXT:
            task_id_str = decision.primary_task_id
            if task_id_str:
                return uuid.UUID(task_id_str)

        return None

    async def _create_task_from_signal(self, signal: Signal, decision) -> uuid.UUID:  # type: ignore[no-untyped-def]
        """Cria uma nova tarefa a partir do sinal."""
        from taskflow.domain.entities.task import Task
        payload = decision.proposed_changes or signal.payload
        task = Task(
            id=uuid.uuid4(),
            title=payload.get("title", "Tarefa sem título"),
            description=payload.get("description"),
            auto_created=True,
            llm_confidence=decision.confidence,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        await self._task_repo.save(task)
        return task.id

    async def _create_proposal(self, signal: Signal, decision) -> uuid.UUID:  # type: ignore[no-untyped-def]
        """Cria uma proposta de triagem para o usuário revisar."""
        from taskflow.domain.entities.task import TaskProposal
        from taskflow.domain.value_objects.enums import ProposalKind

        kind_map = {
            DecisionKind.NEW_TASK: ProposalKind.NEW_TASK,
            DecisionKind.UPDATE_EXISTING: ProposalKind.UPDATE,
            DecisionKind.TRANSITION_EXISTING: ProposalKind.TRANSITION,
            DecisionKind.SPLIT: ProposalKind.SPLIT,
            DecisionKind.MERGE_DUPLICATE: ProposalKind.MERGE,
        }
        proposal = TaskProposal(
            id=uuid.uuid4(),
            signal_id=signal.id,
            proposal_kind=kind_map.get(decision.decision_kind, ProposalKind.NEW_TASK),
            payload=decision.proposed_changes or {},
            confidence=decision.confidence,
        )
        # Persiste via signal_repo (adaptação — não temos ProposalRepository ainda)
        await self._signal_repo.save(proposal)  # type: ignore[arg-type]
        return proposal.id
