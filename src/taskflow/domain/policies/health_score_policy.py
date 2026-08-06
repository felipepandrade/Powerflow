"""Política de cálculo do Score de Saúde do Projeto — RF-H.9 e Seção 11 do PRD."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class HealthScoreResult:
    """Resultado do score de saúde com decomposição explicativa."""

    score: float | None
    components: dict[str, float] = field(default_factory=dict)
    coverage_pct: float = 100.0
    caveat: str | None = None


class HealthScorePolicy:
    """Calcula o Health Score determinístico de um projeto decomposto em 5 componentes."""

    @staticmethod
    def calculate(
        tasks_total: int,
        tasks_open: int,
        tasks_in_progress: int,
        tasks_blocked: int,
        tasks_overdue: int,
        milestones_total: int,
        milestones_at_risk: int,
        milestones_missed: int,
        days_since_activity: int | None,
        oldest_blocked_days: int | None,
    ) -> HealthScoreResult:
        if tasks_total == 0:
            return HealthScoreResult(
                score=None, components={}, coverage_pct=0.0,
                caveat="Saúde desconhecida: projeto sem tarefas observáveis.",
            )

        # 1. WIP Score (WIP ideal <= 30% do total aberto)
        wip_ratio = tasks_in_progress / max(tasks_open, 1)
        wip_score = max(0.0, 100.0 - (wip_ratio * 50.0))

        # 2. Overdue Score (Penaliza tarefas atrasadas)
        overdue_ratio = tasks_overdue / max(tasks_open, 1)
        overdue_score = max(0.0, 100.0 - (overdue_ratio * 100.0))

        # 3. Blocked Score (Penaliza tarefas bloqueadas e tempo no bloqueio)
        blocked_ratio = tasks_blocked / max(tasks_open, 1)
        blocked_penalty = blocked_ratio * 60.0
        if oldest_blocked_days and oldest_blocked_days > 3:
            blocked_penalty += min(40.0, (oldest_blocked_days - 3) * 5.0)
        blocked_score = max(0.0, 100.0 - blocked_penalty)

        # 4. Milestones Score (Penaliza marcos em risco ou perdidos)
        if milestones_total > 0:
            ms_penalty = ((milestones_at_risk * 30.0) + (milestones_missed * 70.0)) / milestones_total
            milestones_score = max(0.0, 100.0 - ms_penalty)
        else:
            milestones_score = 100.0

        # 5. Activity Score (Penaliza dias de inatividade)
        days = days_since_activity or 0
        if days <= 2:
            activity_score = 100.0
        elif days <= 7:
            activity_score = max(0.0, 100.0 - ((days - 2) * 12.0))
        else:
            activity_score = max(0.0, 40.0 - ((days - 7) * 5.0))

        # Média ponderada
        weights = {
            "wip_score": 0.20,
            "overdue_score": 0.30,
            "blocked_score": 0.20,
            "milestones_score": 0.15,
            "activity_score": 0.15,
        }

        components = {
            "wip_score": round(wip_score, 2),
            "overdue_score": round(overdue_score, 2),
            "blocked_score": round(blocked_score, 2),
            "milestones_score": round(milestones_score, 2),
            "activity_score": round(activity_score, 2),
        }

        final_score = sum(components[k] * weights[k] for k in weights)
        return HealthScoreResult(score=round(final_score, 2), components=components)
