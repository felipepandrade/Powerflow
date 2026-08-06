"""Deterministic, guarded and audited signal correlation."""

from __future__ import annotations

import time
import uuid
from dataclasses import replace
from datetime import date, datetime
from typing import Any

import structlog

from taskflow.application.dto.commands import CorrelateSignalCommand, CorrelationRunResult
from taskflow.domain.entities.source import CorrelationRun, Signal, SourceItem
from taskflow.domain.entities.task import (
    Task,
    TaskEvidence,
    TaskProposal,
    TaskStatusHistory,
    TaskUpdate,
)
from taskflow.domain.policies.candidate_fusion import CandidateFusion, FusionResult
from taskflow.domain.policies.correlation_policy import CorrelationDecision, CorrelationPolicy
from taskflow.domain.policies.task_state_machine import TaskStateMachine
from taskflow.domain.ports.ports import (
    EmbeddingProvider,
    LLMProvider,
    SignalRepository,
    TaskRepository,
    UnitOfWork,
)
from taskflow.domain.value_objects.enums import (
    ActorType,
    DecisionKind,
    EvidenceRole,
    Priority,
    ProposalKind,
    RelationType,
    SignalState,
    TaskStatus,
)

log = structlog.get_logger()
MAX_CANDIDATES = 8


class CorrelateSignalUseCase:
    """LLM assessments are hypotheses; CorrelationPolicy owns the final decision."""

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
        self._state_machine = TaskStateMachine()

    async def execute(self, cmd: CorrelateSignalCommand) -> CorrelationRunResult:
        started = time.monotonic()
        signal = await self._signal_repo.get_signal_by_id(cmd.signal_id)
        if signal is None:
            raise ValueError(f"Signal {cmd.signal_id} not found")
        if signal.state != SignalState.PENDING_CORRELATION and not cmd.force_triage:
            raise ValueError(f"Signal {cmd.signal_id} is not pending")

        source = await self._signal_repo.get_source_item_by_id(signal.source_item_id)
        guardrail_blocks: list[dict[str, Any]] = []
        privacy_blocked = source is not None and source.is_redacted
        if privacy_blocked:
            guardrail_blocks.append({"guardrail": "privacy", "reason": "redacted_source"})

        candidates, retrievers = await self._retrieve_candidates(signal, source)
        candidate_ids = {result.task_id for result in candidates}
        has_shortcut, shortcut_id = self._fusion.has_strong_deterministic_match(retrievers)
        assessments: list[dict[str, Any]] = []
        llm_response: dict[str, Any] | None = None
        skipped_llm = privacy_blocked

        if not privacy_blocked and has_shortcut and shortcut_id in candidate_ids:
            skipped_llm = True
            assessments = [{
                "relation": RelationType.SAME_TASK.value,
                "confidence": 1.0,
                "task_id": str(shortcut_id),
            }]
        elif not privacy_blocked and candidates:
            llm_response = await self._llm.correlate(
                signal={"schema_version": "correlation/v1", **signal.payload},
                candidates=await self._build_candidate_cards(candidates),
            )
            assessments, rejected = self._validate_assessments(
                llm_response.get("assessments"), candidate_ids
            )
            guardrail_blocks.extend(rejected)

        decision_kind = self._extract_decision_kind(assessments)
        confidence = self._extract_confidence(signal, assessments)
        primary_task_id = self._extract_primary_task_id(assessments)
        changes = self._extract_proposed_changes(signal, assessments, decision_kind)
        target = (
            await self._task_repo.get_by_id(uuid.UUID(primary_task_id))
            if primary_task_id is not None
            else None
        )
        if target is not None and changes is not None and changes.get("due_date"):
            changes["current_due_date"] = (
                target.due_date.isoformat() if target.due_date else None
            )

        decision = self._policy.decide(
            decision_kind=decision_kind,
            confidence=confidence,
            primary_task_id=primary_task_id,
            proposed_changes=changes,
            has_deterministic_match=has_shortcut,
            signal_from_responsible=signal.payload.get("owner_type") == "me",
            ambiguity_reason=None,
            assessments=assessments,
        )

        if source is not None and (
            not signal.evidence_quote
            or signal.evidence_quote not in source.get_content_for_llm()
        ):
            guardrail_blocks.append({
                "guardrail": "literal_evidence",
                "reason": "quote_missing_or_not_literal",
            })
        if primary_task_id is not None and uuid.UUID(primary_task_id) not in candidate_ids:
            guardrail_blocks.append({
                "guardrail": "candidate_identity",
                "reason": "primary_task_not_retrieved",
            })
        if (
            target is not None
            and changes is not None
            and changes.get("to_status") is not None
        ):
            try:
                next_status = TaskStatus(str(changes["to_status"]))
            except ValueError:
                guardrail_blocks.append({
                    "guardrail": "transition",
                    "reason": "unknown_target_status",
                })
            else:
                if not self._state_machine.is_valid(target.status, next_status):
                    guardrail_blocks.append({
                        "guardrail": "transition",
                        "reason": "invalid_state_transition",
                    })

        force_triage = (
            cmd.force_triage
            or bool(signal.payload.get("blocked_by_safety"))
            or bool(guardrail_blocks)
        )
        if force_triage and decision.action != "triage":
            decision = replace(
                decision,
                action="triage",
                policy_rule_id=f"{decision.policy_rule_id}/guardrail",
                ambiguity_reason=decision.ambiguity_reason or "guardrail_blocked",
            )

        run = CorrelationRun(
            signal_id=signal.id,
            candidates=[
                {
                    "task_id": str(result.task_id),
                    "fused_score": result.fused_score,
                    "final_score": result.final_score,
                    "retrievers": [source.retriever for source in result.sources],
                }
                for result in candidates
            ],
            llm_assessments=llm_response,
            final_decision=decision.decision_kind.value,
            final_confidence=decision.confidence,
            applied=False,
            routed_to_triage=decision.routed_to_triage,
            policy_rule_id=decision.policy_rule_id,
            guardrail_blocks=guardrail_blocks,
            skipped_llm=skipped_llm,
        )

        applied_task_id: uuid.UUID | None = None
        proposal_id: uuid.UUID | None = None
        async with self._uow:
            if decision.is_auto_applied and not force_triage:
                applied_task_id = await self._apply_decision(signal, source, decision)
                run.applied = applied_task_id is not None
            elif decision.routed_to_triage or force_triage:
                proposal = self._build_proposal(signal, decision, candidates)
                await self._signal_repo.save(proposal)
                proposal_id = proposal.id

            if run.applied:
                signal.state = SignalState.RESOLVED
                signal.resolved_task_id = applied_task_id
                signal.resolved_at = datetime.utcnow()
            elif decision.action == "discard" and not force_triage:
                signal.state = SignalState.DISCARDED
                signal.resolved_at = datetime.utcnow()

            run.latency_ms = int((time.monotonic() - started) * 1000)
            await self._signal_repo.save(signal)
            await self._signal_repo.save_correlation_run(run)
            await self._uow.commit()

        return CorrelationRunResult(
            signal_id=signal.id,
            correlation_run_id=run.id,
            decision_kind=decision.decision_kind,
            policy_rule_id=decision.policy_rule_id,
            action="triage" if force_triage else decision.action,
            confidence=decision.confidence,
            applied_task_id=applied_task_id,
            proposal_id=proposal_id,
            latency_ms=run.latency_ms or 0,
        )

    async def _retrieve_candidates(
        self, signal: Signal, source: SourceItem | None
    ) -> tuple[list[FusionResult], dict[str, list[tuple[uuid.UUID, float]]]]:
        retrievers: dict[str, list[tuple[uuid.UUID, float]]] = {}
        if source is not None:
            source_matches = await self._task_repo.find_by_source_context(
                source.conversation_id, source.external_id, MAX_CANDIDATES
            )
            if source_matches:
                key = "R1_thread" if source.conversation_id else "R2_event"
                retrievers[key] = [(task.id, 1.0) for task in source_matches]

        explicit = signal.payload.get("task_id")
        if isinstance(explicit, str):
            try:
                explicit_id = uuid.UUID(explicit)
            except ValueError:
                explicit_id = None
            if explicit_id is not None and await self._task_repo.get_by_id(explicit_id):
                retrievers["R3_identifier"] = [(explicit_id, 1.0)]

        query = signal.payload.get("title") or signal.payload.get("task_title")
        if isinstance(query, str) and query.strip():
            matches = await self._task_repo.search_full_text(query, MAX_CANDIDATES)
            if matches:
                retrievers["R5_lexical"] = [(task.id, 0.8) for task in matches]

        signal_text = " ".join(
            value
            for key in ("title", "task_title", "description", "task_description", "commitment")
            if isinstance((value := signal.payload.get(key)), str)
        )
        if signal_text:
            try:
                vectors = await self._embedder.embed([signal_text])
                semantic = (
                    await self._task_repo.find_by_embedding(vectors[0], MAX_CANDIDATES)
                    if vectors
                    else ()
                )
                if semantic:
                    retrievers["R6_semantic"] = [(task.id, 0.7) for task in semantic]
            except Exception:
                log.exception("correlate.embedding_failed", signal_id=str(signal.id))

        return self._fusion.fuse(retrievers)[:MAX_CANDIDATES], retrievers

    async def _build_candidate_cards(
        self, candidates: list[FusionResult]
    ) -> list[dict[str, Any]]:
        cards: list[dict[str, Any]] = []
        for candidate in candidates:
            task = await self._task_repo.get_by_id(candidate.task_id)
            if task is None:
                continue
            cards.append({
                "task_id": str(task.id),
                "title": task.title,
                "status": task.status.value,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "fused_score": round(candidate.fused_score, 6),
                "retrievers": [score.retriever for score in candidate.sources],
            })
        return cards

    @staticmethod
    def _validate_assessments(
        raw: object, candidate_ids: set[uuid.UUID]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        valid: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        if not isinstance(raw, list):
            return valid, [{"guardrail": "assessment_schema", "reason": "not_a_list"}]
        for assessment in raw:
            if not isinstance(assessment, dict):
                rejected.append({"guardrail": "assessment_schema", "reason": "not_an_object"})
                continue
            try:
                RelationType(str(assessment.get("relation")))
                confidence_raw = assessment.get("confidence")
                if not isinstance(confidence_raw, (int, float)):
                    raise TypeError
                confidence = float(confidence_raw)
            except (TypeError, ValueError):
                rejected.append({"guardrail": "assessment_schema", "reason": "invalid_relation_or_confidence"})
                continue
            if not 0.0 <= confidence <= 1.0:
                rejected.append({"guardrail": "assessment_schema", "reason": "confidence_out_of_range"})
                continue
            task_id = assessment.get("task_id")
            if task_id is not None:
                try:
                    parsed = uuid.UUID(str(task_id))
                except ValueError:
                    parsed = None
                if parsed not in candidate_ids:
                    rejected.append({"guardrail": "candidate_identity", "reason": "assessment_task_not_retrieved"})
                    continue
            valid.append({str(key): value for key, value in assessment.items()})
        return valid, rejected

    @staticmethod
    def _top(assessments: list[dict[str, Any]]) -> dict[str, Any] | None:
        return max(assessments, key=lambda row: float(row["confidence"])) if assessments else None

    def _extract_decision_kind(
        self, assessments: list[dict[str, Any]]
    ) -> DecisionKind:
        top = self._top(assessments)
        if top is None:
            return DecisionKind.NEW_TASK
        mapping = {
            RelationType.SAME_TASK: DecisionKind.UPDATE_EXISTING,
            RelationType.STATUS_UPDATE: DecisionKind.TRANSITION_EXISTING,
            RelationType.DUE_DATE_CHANGE: DecisionKind.UPDATE_EXISTING,
            RelationType.SCOPE_CHANGE: DecisionKind.SPLIT,
            RelationType.SUBTASK_OF: DecisionKind.SPLIT,
            RelationType.BLOCKS: DecisionKind.TRANSITION_EXISTING,
            RelationType.DUPLICATE_OF: DecisionKind.MERGE_DUPLICATE,
            RelationType.RELATED_CONTEXT: DecisionKind.ATTACH_CONTEXT,
            RelationType.UNRELATED: DecisionKind.NEW_TASK,
        }
        return mapping[RelationType(str(top["relation"]))]

    def _extract_confidence(
        self, signal: Signal, assessments: list[dict[str, Any]]
    ) -> float:
        top = self._top(assessments)
        return float(top["confidence"]) if top is not None else float(signal.extraction_conf or 0.0)

    def _extract_primary_task_id(
        self, assessments: list[dict[str, Any]]
    ) -> str | None:
        top = self._top(assessments)
        task_id = top.get("task_id") if top else None
        return str(task_id) if task_id is not None else None

    def _extract_proposed_changes(
        self,
        signal: Signal,
        assessments: list[dict[str, Any]],
        kind: DecisionKind,
    ) -> dict[str, Any] | None:
        if kind == DecisionKind.NEW_TASK:
            return {
                "title": signal.payload.get("title")
                or signal.payload.get("task_title")
                or "Untitled task",
                "description": signal.payload.get("description")
                or signal.payload.get("task_description"),
                "due_date": signal.payload.get("due_date"),
                "priority": signal.payload.get("priority", Priority.MEDIUM.value),
            }
        changes: dict[str, Any] = {}
        top = self._top(assessments)
        if top and top.get("proposed_status"):
            changes["to_status"] = top["proposed_status"]
        for key in ("due_date", "progress_note", "waiting_on_id", "description"):
            if signal.payload.get(key) is not None:
                changes[key] = signal.payload[key]
        return changes or None

    async def _apply_decision(
        self,
        signal: Signal,
        source: SourceItem | None,
        decision: CorrelationDecision,
    ) -> uuid.UUID | None:
        if decision.decision_kind == DecisionKind.NEW_TASK:
            payload = decision.proposed_changes or signal.payload
            try:
                priority = Priority(str(payload.get("priority", Priority.MEDIUM.value)))
            except ValueError:
                priority = Priority.MEDIUM
            due_raw = payload.get("due_date")
            task = Task(
                title=str(payload.get("title") or "Untitled task"),
                description=(
                    str(payload["description"])
                    if payload.get("description") is not None
                    else None
                ),
                priority=priority,
                due_date=date.fromisoformat(str(due_raw)) if due_raw else None,
                auto_created=True,
                llm_confidence=decision.confidence,
            )
            task.status_history.append(TaskStatusHistory(
                task_id=task.id,
                from_status=None,
                to_status=task.status,
                actor=ActorType.LLM,
                reason="automatic task creation",
                signal_id=signal.id,
                snapshot={"created": True},
            ))
            self._append_evidence(task, signal, source, EvidenceRole.ORIGIN)
            await self._task_repo.save(task)
            return task.id

        if decision.primary_task_id is None:
            return None
        existing_task = await self._task_repo.get_by_id(uuid.UUID(decision.primary_task_id))
        if existing_task is None:
            return None
        task = existing_task

        if decision.decision_kind == DecisionKind.ATTACH_CONTEXT:
            self._append_evidence(task, signal, source, EvidenceRole.CONTEXT)
            await self._task_repo.save(task)
            return task.id

        snapshot = task.snapshot_dict()
        changes = decision.proposed_changes or {}
        if changes.get("to_status") is not None:
            next_status = TaskStatus(str(changes["to_status"]))
            self._state_machine.validate(task.status, next_status)
            task.status = next_status
            task.completed_at = datetime.utcnow() if next_status == TaskStatus.DONE else None
        if changes.get("due_date") is not None:
            task.due_date = date.fromisoformat(str(changes["due_date"]))
            task.due_date_source = "explicit"
        if changes.get("waiting_on_id") is not None:
            task.waiting_on_id = uuid.UUID(str(changes["waiting_on_id"]))
        if changes.get("description") is not None:
            task.description = str(changes["description"])
        if changes.get("progress_note"):
            task.updates.append(TaskUpdate(
                task_id=task.id,
                content=str(changes["progress_note"]),
                source="extracted",
                source_item_id=signal.source_item_id,
                signal_id=signal.id,
            ))

        task.status_history.append(TaskStatusHistory(
            task_id=task.id,
            from_status=TaskStatus(str(snapshot["status"])),
            to_status=task.status,
            actor=ActorType.LLM,
            reason=f"automatic {decision.decision_kind.value}",
            signal_id=signal.id,
            snapshot=snapshot,
        ))
        self._append_evidence(task, signal, source, EvidenceRole.UPDATE)
        task.last_activity_at = datetime.utcnow()
        task.updated_at = datetime.utcnow()
        await self._task_repo.save(task)
        return task.id

    @staticmethod
    def _append_evidence(
        task: Task,
        signal: Signal,
        source: SourceItem | None,
        role: EvidenceRole,
    ) -> None:
        if source is None or not signal.evidence_quote:
            return
        task.evidence.append(TaskEvidence(
            task_id=task.id,
            source_item_id=source.id,
            signal_id=signal.id,
            quote=signal.evidence_quote,
            role=role,
        ))

    @staticmethod
    def _build_proposal(
        signal: Signal,
        decision: CorrelationDecision,
        candidates: list[FusionResult],
    ) -> TaskProposal:
        kind_map = {
            DecisionKind.NEW_TASK: ProposalKind.NEW_TASK,
            DecisionKind.UPDATE_EXISTING: ProposalKind.UPDATE,
            DecisionKind.TRANSITION_EXISTING: ProposalKind.TRANSITION,
            DecisionKind.SPLIT: ProposalKind.SPLIT,
            DecisionKind.MERGE_DUPLICATE: ProposalKind.MERGE,
            DecisionKind.ATTACH_CONTEXT: ProposalKind.DISAMBIGUATE,
            DecisionKind.NOISE: ProposalKind.DISAMBIGUATE,
        }
        payload = dict(decision.proposed_changes or {})
        if decision.primary_task_id is not None:
            payload.setdefault("task_id", decision.primary_task_id)
        return TaskProposal(
            signal_id=signal.id,
            proposal_kind=kind_map[decision.decision_kind],
            payload=payload,
            candidate_tasks=[
                {"task_id": str(candidate.task_id), "score": candidate.final_score}
                for candidate in candidates
            ],
            confidence=decision.confidence,
        )
