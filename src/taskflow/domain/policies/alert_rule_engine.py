"""Motor de Regras de Alerta e Anti-Fadiga — RF-G.9 e Seção 12 do PRD."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Alert:
    """Entidade de Alerta Disparado."""

    id: uuid.UUID
    rule_id: str
    severity: str  # info | warning | critical
    title: str
    message: str
    metric_id: str
    current_value: float
    threshold_value: float
    status: str = "open"  # open | acknowledged | resolved
    created_at: datetime = field(default_factory=datetime.utcnow)


class AlertRuleEngine:
    """Avalia regras de alerta determinísticas e aplica filtro anti-fadiga (máx 7 ativos)."""

    MAX_ACTIVE_ALERTS = 7

    @classmethod
    def evaluate_metrics(cls, metrics_data: list[dict[str, float]]) -> list[Alert]:
        """Avalia métricas contra limiares predefinidos e retorna alertas."""
        generated: list[Alert] = []

        for m in metrics_data:
            metric_id = m.get("metric_id", "")
            val = m.get("value", 0.0)

            # 1. Alerta de WIP elevado
            if metric_id == "flow.wip" and val > 5.0:
                generated.append(
                    Alert(
                        id=uuid.uuid4(),
                        rule_id="rule_wip_overflow",
                        severity="warning",
                        title="Acúmulo de Trabalho em Progresso (WIP)",
                        message=f"WIP atual é de {val:.0f} tarefas (limiar recomendado: 5). Risco de sobrecarga e estrangulamento de vazão.",
                        metric_id=metric_id,
                        current_value=val,
                        threshold_value=5.0,
                    )
                )

            # 2. Alerta de Lead Time elevado (p85)
            elif metric_id == "flow.lead_time_p85" and val > 7.0:
                generated.append(
                    Alert(
                        id=uuid.uuid4(),
                        rule_id="rule_lead_time_high",
                        severity="critical",
                        title="Lead Time Elevado (p85)",
                        message=f"Lead time p85 atingiu {val:.1f} dias (limiar: 7.0 dias). Demora acima do padrão no atendimento a demandas.",
                        metric_id=metric_id,
                        current_value=val,
                        threshold_value=7.0,
                    )
                )

            # 3. Alerta de excesso de tempo em reuniões
            elif metric_id == "capacity.meeting_ratio" and val > 40.0:
                generated.append(
                    Alert(
                        id=uuid.uuid4(),
                        rule_id="rule_meeting_overload",
                        severity="warning",
                        title="Sobrecarga de Reuniões",
                        message=f"Reuniões ocupam {val:.1f}% da jornada de trabalho (limiar: 40%). Risco à capacidade de execução concentrada.",
                        metric_id=metric_id,
                        current_value=val,
                        threshold_value=40.0,
                    )
                )

            # 4. Alerta de degradação de saúde de projetos
            elif metric_id == "project.health_score" and val < 75.0:
                generated.append(
                    Alert(
                        id=uuid.uuid4(),
                        rule_id="rule_project_health_degraded",
                        severity="critical",
                        title="Saúde da Carteira de Projetos Comprometida",
                        message=f"Health Score médio caiu para {val:.1f} pts (limiar de atenção: 75.0 pts). Intervenção necessária.",
                        metric_id=metric_id,
                        current_value=val,
                        threshold_value=75.0,
                    )
                )

        # Aplicar Anti-Fadiga: Ordenar por severidade (critical > warning > info) e cortar no máx 7
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        generated.sort(key=lambda a: severity_order.get(a.severity, 3))

        return generated[: cls.MAX_ACTIVE_ALERTS]
