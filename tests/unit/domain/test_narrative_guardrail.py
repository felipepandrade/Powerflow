"""Testes unitários para NarrativeGuardrailPolicy e GenerateNarrativeInsightUseCase."""

from taskflow.domain.policies.narrative_guardrail_policy import NarrativeGuardrailPolicy


def test_narrative_guardrail_valid_text() -> None:
    evidence = [10.0, 50.0, 85.0]
    narrative = "O throughput do projeto foi 10.0 tarefas, com lead time p85 de 85.0 dias."

    result = NarrativeGuardrailPolicy.validate(narrative, evidence)
    assert result.is_valid is True
    assert len(result.discrepancies) == 0


def test_narrative_guardrail_catches_hallucinated_number() -> None:
    evidence = [10.0, 50.0]
    narrative = "O throughput foi 10.0 tarefas, registrando um aumento de 999.0% sem precedentes."

    result = NarrativeGuardrailPolicy.validate(narrative, evidence)
    assert result.is_valid is False
    assert 999.0 in result.discrepancies


def test_narrative_guardrail_does_not_ignore_small_numbers() -> None:
    result = NarrativeGuardrailPolicy.validate("Existem 2 riscos.", [10.0])
    assert result.is_valid is False
    assert result.discrepancies == [2.0]
