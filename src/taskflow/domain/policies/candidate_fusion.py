"""CandidateFusion — Fusão por Reciprocal Rank Fusion (RRF) — RF-G.2.

Implementação determinística do algoritmo RRF que combina os resultados
dos 6 recuperadores (R1..R6) em um ranking único.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

# Pesos por recuperador — RF-G.1
RETRIEVER_WEIGHTS: dict[str, float] = {
    "R1_thread": 1.00,
    "R2_event": 0.95,
    "R3_identifier": 0.90,
    "R6_semantic": 0.75,
    "R5_lexical": 0.65,
    "R4_participants": 0.55,
}

RRF_K: int = 60


@dataclass(frozen=True)
class CandidateScore:
    """Score de um candidato de tarefa para correlação."""

    task_id: uuid.UUID
    retriever: str
    rank: int
    raw_score: float
    fused_score: float = 0.0


@dataclass
class FusionResult:
    """Resultado da fusão de candidatos."""

    task_id: uuid.UUID
    fused_score: float
    sources: list[CandidateScore] = field(default_factory=list)
    temporal_boost: float = 0.0
    status_boost: float = 0.0

    @property
    def final_score(self) -> float:
        """Score final incluindo boosts."""
        return self.fused_score + self.temporal_boost + self.status_boost


class CandidateFusion:
    """Fusão de recuperadores por Reciprocal Rank Fusion.

    RF-G.2: score(task) = Σᵢ pesoᵢ / (RRF_K + rankᵢ)

    Implementação 100% determinística e testável sem I/O.
    """

    def __init__(self, rrf_k: int = RRF_K) -> None:
        self.rrf_k = rrf_k

    def fuse(
        self,
        retriever_results: dict[str, list[tuple[uuid.UUID, float]]],
        active_statuses: set[str] | None = None,
    ) -> list[FusionResult]:
        """Funde os resultados dos recuperadores em ranking único.

        Args:
            retriever_results: {retriever_name: [(task_id, raw_score), ...]}
                               ordenados do mais relevante para o menos.
            active_statuses: Conjunto de status de tarefas ativas
                             (para boost de status).

        Returns:
            Lista de FusionResult ordenada por final_score desc.
        """
        if active_statuses is None:
            active_statuses = {"open", "in_progress", "waiting_on_others", "blocked"}

        # Mapeia task_id → {retriever → CandidateScore}
        task_scores: dict[uuid.UUID, list[CandidateScore]] = {}

        for retriever, results in retriever_results.items():
            weight = RETRIEVER_WEIGHTS.get(retriever, 0.5)
            for rank, (task_id, raw_score) in enumerate(results, start=1):
                rrf_score = weight / (self.rrf_k + rank)
                candidate = CandidateScore(
                    task_id=task_id,
                    retriever=retriever,
                    rank=rank,
                    raw_score=raw_score,
                    fused_score=rrf_score,
                )
                if task_id not in task_scores:
                    task_scores[task_id] = []
                task_scores[task_id].append(candidate)

        # Agrega scores por task_id
        results_list: list[FusionResult] = []
        for task_id, candidates in task_scores.items():
            total_fused = sum(c.fused_score for c in candidates)
            results_list.append(
                FusionResult(
                    task_id=task_id,
                    fused_score=total_fused,
                    sources=candidates,
                )
            )

        # Ordena por score final desc, depois task_id para estabilidade
        results_list.sort(key=lambda r: (-r.final_score, str(r.task_id)))
        return results_list

    def has_strong_deterministic_match(
        self,
        retriever_results: dict[str, list[tuple[uuid.UUID, float]]],
    ) -> tuple[bool, uuid.UUID | None]:
        """Verifica atalho determinístico — RF-G.3.

        Se R1 (thread) OU R2 (event) retornar exatamente UMA tarefa ativa
        e nenhum outro candidato passar do limiar mínimo, retorna
        (True, task_id) — o estágio G2 deve ser pulado.

        Returns:
            (has_shortcut, task_id_or_None)
        """
        for retriever in ("R1_thread", "R2_event", "R3_identifier"):
            results = retriever_results.get(retriever, [])
            if len(results) == 1:
                task_id, _ = results[0]
                # Verifica que outros recuperadores não têm candidatos adicionais
                other_task_ids: set[uuid.UUID] = set()
                for other_retriever, other_results in retriever_results.items():
                    if other_retriever == retriever:
                        continue
                    other_task_ids.update(tid for tid, _ in other_results)

                if not other_task_ids or other_task_ids == {task_id}:
                    return True, task_id

        return False, None
