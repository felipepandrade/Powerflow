"""Guardião Ético do Cockpit Gerencial — Seção 8 do PRD.

Garante que o sistema seja usado estritamente como diagnóstico do sistema de trabalho,
bloqueando qualquer tentativa de monitoramento individual de pessoas ou ranking.
"""

from __future__ import annotations


class EthicsViolationError(ValueError):
    """Exceção lançada quando uma métrica ou consulta viola as diretrizes éticas."""


class EthicsGuard:
    """Validador determinístico de diretrizes de governança ética."""

    FORBIDDEN_KEYWORDS = [
        "ranking",
        "individual_performance",
        "employee_score",
        "user_activity_ranking",
        "third_party_presence",
        "availability_monitor",
    ]

    @classmethod
    def validate_metric_query(cls, metric_id: str, group_by: str | None = None) -> None:
        """Garante que consultas não sejam agrupadas por indivíduo/pessoa."""
        if group_by in ("user_id", "author_email", "assignee_id", "person_id"):
            raise EthicsViolationError(
                f"Consulta à métrica '{metric_id}' bloqueada: proibida agregação ou ranking individual por '{group_by}' (Seção 8 do PRD)."
            )

        for kw in cls.FORBIDDEN_KEYWORDS:
            if kw in metric_id.lower():
                raise EthicsViolationError(
                    f"Métrica '{metric_id}' bloqueada pelo Guardião Ético: viola o princípio de não-monitoramento individual."
                )
