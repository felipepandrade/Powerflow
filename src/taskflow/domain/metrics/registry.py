"""Catálogo e registro code-first de métricas do TaskFlow — Seção 11 do PRD."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class MetricDefinition:
    """Definição formal e auditável de uma métrica do catálogo."""

    id: str  # ex: "flow.throughput"
    name: str  # ex: "Throughput (Vazão)"
    category: str  # ex: "Fluxo", "Capacidade", "Qualidade"
    description: str
    question: str  # Pergunta de negócio respondida
    expected_action: str  # Ação recomendada se desfavorável
    owner: str  # Papel responsável (ex: "Tech Lead", "Gerente de Projetos")
    unit: str  # ex: "tarefas/semana", "horas", "%"
    grain_support: list[str] = field(default_factory=lambda: ["daily", "weekly", "monthly"])
    is_k_anonymized: bool = False  # Requer K-anonimato mínimo = 3
    compute_fn_name: str = ""


class MetricRegistry:
    """Catálogo central code-first de métricas."""

    _registry: dict[str, MetricDefinition] = {}

    @classmethod
    def register(cls, metric: MetricDefinition) -> MetricDefinition:
        """Registra uma métrica validando todos os metadados obrigatórios."""
        if not metric.id or not metric.name:
            raise ValueError("Métrica deve conter id e name.")
        if not metric.question or not metric.expected_action or not metric.owner:
            raise ValueError(
                f"Métrica {metric.id} viola o Gate CI: 'question', 'expected_action' e 'owner' são OBRIGATÓRIOS!"
            )

        cls._registry[metric.id] = metric
        return metric

    @classmethod
    def get(cls, metric_id: str) -> MetricDefinition | None:
        return cls._registry.get(metric_id)

    @classmethod
    def list_all(cls) -> list[MetricDefinition]:
        return list(cls._registry.values())

    @classmethod
    def validate_all(cls) -> bool:
        """Validação estática usada no CI."""
        for metric in cls._registry.values():
            if not metric.question or not metric.expected_action or not metric.owner:
                return False
        return True


# ── Registro das 10 Métricas Iniciais do Catálogo ─────────────────────

MetricRegistry.register(
    MetricDefinition(
        id="flow.throughput",
        name="Throughput (Vazão)",
        category="Fluxo",
        description="Quantidade de tarefas concluídas no período.",
        question="Quantas entregas foram concluídas nesta janela de tempo?",
        expected_action="Aumentar capacidade ou reduzir gargalos se a vazão cair abruptamente.",
        owner="Tech Lead / Gestor",
        unit="tarefas",
        compute_fn_name="compute_throughput",
    )
)

MetricRegistry.register(
    MetricDefinition(
        id="flow.net_flow",
        name="Fluxo Líquido (Net Flow)",
        category="Fluxo",
        description="Diferença entre tarefas criadas e concluídas (Entradas - Saídas).",
        question="O backlog do projeto está crescendo ou encolhendo?",
        expected_action="Limitar novos ingressos se o fluxo líquido for consistentemente positivo.",
        owner="Gerente de Projetos",
        unit="tarefas",
        compute_fn_name="compute_net_flow",
    )
)

MetricRegistry.register(
    MetricDefinition(
        id="flow.wip",
        name="Trabalho em Progresso (WIP)",
        category="Fluxo",
        description="Total de tarefas atualmente em andamento.",
        question="Quantas tarefas estão sendo executadas simultaneamente?",
        expected_action="Aplicar limite de WIP e focar na conclusão das tarefas ativas.",
        owner="Tech Lead",
        unit="tarefas",
        compute_fn_name="compute_wip",
    )
)

MetricRegistry.register(
    MetricDefinition(
        id="flow.lead_time_p50",
        name="Lead Time (p50)",
        category="Desempenho",
        description="Mediana do tempo decorrido da criação à conclusão da tarefa.",
        question="Qual é o tempo típico de entrega de uma demanda?",
        expected_action="Investigar etapas de espera na cadeia se p50 aumentar.",
        owner="Gerente de Processos",
        unit="dias",
        compute_fn_name="compute_lead_time_p50",
    )
)

MetricRegistry.register(
    MetricDefinition(
        id="flow.lead_time_p85",
        name="Lead Time (p85)",
        category="Desempenho",
        description="Percentil 85 do tempo decorrido até a conclusão da tarefa.",
        question="Em até quantos dias entregamos 85% das nossas demandas?",
        expected_action="Identificar outliers e gargalos sistêmicos de longa duração.",
        owner="Gerente de Processos",
        unit="dias",
        compute_fn_name="compute_lead_time_p85",
    )
)

MetricRegistry.register(
    MetricDefinition(
        id="flow.aging_wip_p85",
        name="Idade do WIP (p85)",
        category="Fluxo",
        description="Percentil 85 da idade das tarefas atualmente em aberto.",
        question="Há quanto tempo as tarefas ativas estão paradas no fluxo?",
        expected_action="Priorizar o desempaque das tarefas mais antigas antes de puxar novas.",
        owner="Tech Lead",
        unit="dias",
        compute_fn_name="compute_aging_wip_p85",
    )
)

MetricRegistry.register(
    MetricDefinition(
        id="capacity.meeting_hours",
        name="Horas em Reuniões",
        category="Capacidade",
        description="Total de horas consumidas em reuniões no período.",
        question="Quanto tempo está sendo investido em reuniões de sincronização?",
        expected_action="Reavaliar pautas e frequência de reuniões se exceder 15h/semana.",
        owner="Gestor de Equipe",
        unit="horas",
        compute_fn_name="compute_meeting_hours",
    )
)

MetricRegistry.register(
    MetricDefinition(
        id="capacity.meeting_ratio",
        name="Percentual de Tempo em Reuniões",
        category="Capacidade",
        description="Proporção da jornada de trabalho ocupada por reuniões.",
        question="Quanto da nossa capacidade útil está comprometida com reuniões?",
        expected_action="Proteger blocos de trabalho focado (focus time) para a equipe.",
        owner="Gestor de Equipe",
        unit="%",
        compute_fn_name="compute_meeting_ratio",
    )
)

MetricRegistry.register(
    MetricDefinition(
        id="capacity.context_switches",
        name="Trocas de Contexto Diárias",
        category="Capacidade",
        description="Quantidade de reuniões e demandas distintas intercaladas no mesmo dia.",
        question="Qual é o nível de fragmentação do dia de trabalho?",
        expected_action="Agrupar reuniões em blocos contínuos (ex: apenas no período da tarde).",
        owner="Gestor de Equipe",
        unit="trocas/dia",
        compute_fn_name="compute_context_switches",
    )
)

MetricRegistry.register(
    MetricDefinition(
        id="project.health_score",
        name="Score de Saúde dos Projetos",
        category="Projetos",
        description="Média ponderada do Health Score dos projetos ativos.",
        question="Qual é a saúde geral da carteira de projetos?",
        expected_action="Realizar ação corretiva imediata nos projetos com score < 60.",
        owner="PMO / Gerente de Projetos",
        unit="pts",
        compute_fn_name="compute_project_health_score",
    )
)
