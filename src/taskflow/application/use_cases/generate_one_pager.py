"""Caso de Uso para geração de Relatório Executivo One-Pager — RF-J.4."""

from datetime import date, datetime
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taskflow.adapters.persistence.models import MetricValueORM, ProjectORM, AlertORM, DecisionLogORM
from taskflow.adapters.persistence.unit_of_work import SqlAlchemyUnitOfWork


class GenerateOnePagerUseCase:
    """Consolida os dados do Cockpit em um relatório executivo One-Pager em formato Markdown/HTML."""

    def __init__(self, session: AsyncSession, uow: SqlAlchemyUnitOfWork) -> None:
        self._session = session
        self._uow = uow

    async def execute(self, project_id: uuid.UUID | None = None) -> dict[str, Any]:
        # 1. Buscar métricas mais recentes
        stmt_m = select(MetricValueORM).order_by(MetricValueORM.computed_at.desc()).limit(20)
        res_m = await self._session.execute(stmt_m)
        metrics = res_m.scalars().all()

        # 2. Buscar projetos ativos
        stmt_p = select(ProjectORM).where(ProjectORM.status == "active")
        res_p = await self._session.execute(stmt_p)
        projects = res_p.scalars().all()

        # 3. Buscar alertas ativos
        stmt_a = select(AlertORM).where(AlertORM.status == "open").order_by(AlertORM.created_at.desc()).limit(5)
        res_a = await self._session.execute(stmt_a)
        alerts = res_a.scalars().all()

        # 4. Buscar decisões recentes
        stmt_d = select(DecisionLogORM).order_by(DecisionLogORM.created_at.desc()).limit(5)
        res_d = await self._session.execute(stmt_d)
        decisions = res_d.scalars().all()

        # Montar a estrutura do One-Pager
        today_str = date.today().isoformat()
        
        md_lines = [
            f"# 📄 TaskFlow — Relatório Executivo One-Pager",
            f"**Data de Emissão:** {today_str} | **Escopo:** {'Projeto Específico' if project_id else 'Carteira Geral'}\n",
            "---",
            "## 1. Métricas Chave de Desempenho (KPIs)",
        ]

        for m in metrics[:8]:
            val_str = f"{m.value:.1f}" if m.value is not None else "N/A"
            md_lines.append(f"- **{m.metric_id}**: `{val_str}` ({m.grain})")

        md_lines.append("\n## 2. Alertas Gerenciais em Aberto")
        if not alerts:
            md_lines.append("- *Nenhum alerta crítico pendente.*")
        else:
            for a in alerts:
                md_lines.append(f"- **[{a.severity.upper()}] {a.title}**: {a.message}")

        md_lines.append("\n## 3. Decisões Gerenciais Recentes")
        if not decisions:
            md_lines.append("- *Nenhuma decisão recente registrada.*")
        else:
            for d in decisions:
                md_lines.append(f"- **{d.title}**: {d.decision} *(Expectativa: {d.expected_outcome or 'N/A'})*")

        md_content = "\n".join(md_lines)

        return {
            "generated_at": datetime.utcnow().isoformat(),
            "scope": str(project_id) if project_id else "global",
            "markdown": md_content,
            "metrics_count": len(metrics),
            "alerts_count": len(alerts),
            "decisions_count": len(decisions),
        }
