"""Testes unitários para CandidateFusion (RRF) — RF-G.1, RF-G.2, RF-G.3."""

import uuid

from taskflow.domain.policies.candidate_fusion import (
    RETRIEVER_WEIGHTS,
    RRF_K,
    CandidateFusion,
)

fusion = CandidateFusion()

T1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
T2 = uuid.UUID("22222222-2222-2222-2222-222222222222")
T3 = uuid.UUID("33333333-3333-3333-3333-333333333333")


class TestRRFFusion:
    """Verifica o algoritmo de fusão RRF — RF-G.2."""

    def test_single_retriever_single_result(self) -> None:
        results = fusion.fuse({"R1_thread": [(T1, 1.0)]})
        assert len(results) == 1
        assert results[0].task_id == T1

    def test_task_with_more_retrievers_wins(self) -> None:
        """Tarefa presente em mais recuperadores deve ter score maior."""
        retriever_results = {
            "R1_thread": [(T1, 1.0)],
            "R3_identifier": [(T1, 0.9)],
            "R5_lexical": [(T2, 0.8)],
        }
        results = fusion.fuse(retriever_results)
        assert results[0].task_id == T1

    def test_rrf_score_formula(self) -> None:
        """Verifica a fórmula: peso / (RRF_K + rank)."""
        retriever_results = {"R1_thread": [(T1, 1.0)]}
        results = fusion.fuse(retriever_results)
        expected_score = RETRIEVER_WEIGHTS["R1_thread"] / (RRF_K + 1)
        assert abs(results[0].fused_score - expected_score) < 1e-10

    def test_ordering_is_stable(self) -> None:
        """Mesma entrada → mesma ordem."""
        retriever_results = {
            "R1_thread": [(T1, 1.0), (T2, 0.5)],
            "R5_lexical": [(T2, 0.9), (T3, 0.3)],
        }
        r1 = fusion.fuse(retriever_results)
        r2 = fusion.fuse(retriever_results)
        assert [r.task_id for r in r1] == [r.task_id for r in r2]

    def test_empty_input(self) -> None:
        results = fusion.fuse({})
        assert results == []

    def test_top_candidate_has_sources(self) -> None:
        retriever_results = {
            "R1_thread": [(T1, 1.0)],
            "R3_identifier": [(T1, 0.9)],
        }
        results = fusion.fuse(retriever_results)
        top = results[0]
        retriever_names = {s.retriever for s in top.sources}
        assert "R1_thread" in retriever_names
        assert "R3_identifier" in retriever_names


class TestDeterministicShortcut:
    """Verifica o atalho determinístico — RF-G.3."""

    def test_single_r1_match_triggers_shortcut(self) -> None:
        """R1 com um único resultado → atalho ativado."""
        retriever_results = {"R1_thread": [(T1, 1.0)]}
        has_shortcut, task_id = fusion.has_strong_deterministic_match(retriever_results)
        assert has_shortcut is True
        assert task_id == T1

    def test_single_r2_match_triggers_shortcut(self) -> None:
        """R2 com um único resultado → atalho ativado."""
        retriever_results = {"R2_event": [(T1, 0.95)]}
        has_shortcut, task_id = fusion.has_strong_deterministic_match(retriever_results)
        assert has_shortcut is True
        assert task_id == T1

    def test_multiple_r1_results_no_shortcut(self) -> None:
        """Mais de um resultado em R1 → sem atalho."""
        retriever_results = {"R1_thread": [(T1, 1.0), (T2, 0.8)]}
        has_shortcut, _ = fusion.has_strong_deterministic_match(retriever_results)
        assert has_shortcut is False

    def test_other_candidates_prevent_shortcut(self) -> None:
        """R1 com 1 resultado, mas outro recuperador retorna task diferente → sem atalho."""
        retriever_results = {
            "R1_thread": [(T1, 1.0)],
            "R5_lexical": [(T2, 0.8)],
        }
        has_shortcut, _ = fusion.has_strong_deterministic_match(retriever_results)
        assert has_shortcut is False

    def test_shortcut_when_all_point_to_same_task(self) -> None:
        """R1 + outros recuperadores apontam para a MESMA tarefa → atalho ativado."""
        retriever_results = {
            "R1_thread": [(T1, 1.0)],
            "R5_lexical": [(T1, 0.7)],
        }
        has_shortcut, task_id = fusion.has_strong_deterministic_match(retriever_results)
        assert has_shortcut is True
        assert task_id == T1

    def test_no_r1_or_r2_no_shortcut(self) -> None:
        """Sem R1 ou R2 → sem atalho."""
        retriever_results = {"R5_lexical": [(T1, 0.9)]}
        has_shortcut, _ = fusion.has_strong_deterministic_match(retriever_results)
        assert has_shortcut is False
