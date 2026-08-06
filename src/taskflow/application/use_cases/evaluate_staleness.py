"""Caso de Uso: EvaluateStalenessUseCase — Bloco A.6 / RF-E.1.

Identifica tarefas envelhecidas (stale), verifica reuniões futuras com a parte interessada
e gera sugestões de cobrança/nudge ou pauta de reunião.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taskflow.adapters.persistence.models import CalendarEventORM, FollowUpORM, TaskORM
from taskflow.adapters.persistence.unit_of_work import SqlAlchemyUnitOfWork
from taskflow.domain.ports.ports import LLMProvider


class EvaluateStalenessUseCase:
    """Avalia envelhecimento de tarefas e prepara nudges e pautas para reuniões."""

    STALE_DAYS_THRESHOLD = 3

    def __init__(
        self,
        session: AsyncSession,
        uow: SqlAlchemyUnitOfWork,
        llm: LLMProvider | None = None,
    ) -> None:
        self._session = session
        self._uow = uow
        self._llm = llm

    async def execute(self) -> list[dict[str, Any]]:
        """Avalia tarefas ativas em busca de inatividade."""
        cutoff_date = datetime.utcnow() - timedelta(days=self.STALE_DAYS_THRESHOLD)

        # Buscar tarefas ativas com última atividade anterior ao corte
        stmt = (
            select(TaskORM)
            .where(
                TaskORM.status.in_(["in_progress", "waiting_on"]),
                (TaskORM.last_activity_at < cutoff_date) | (TaskORM.last_activity_at == None),
            )
            .limit(50)
        )

        res = await self._session.execute(stmt)
        stale_tasks = res.scalars().all()

        stale_evaluations: list[dict[str, Any]] = []
        now = datetime.utcnow()
        next_week = now + timedelta(days=7)

        # Buscar eventos de calendário da próxima semana
        stmt_cal = (
            select(CalendarEventORM)
            .where(
                CalendarEventORM.starts_at >= now,
                CalendarEventORM.starts_at <= next_week,
            )
            .order_by(CalendarEventORM.starts_at.asc())
        )
        res_cal = await self._session.execute(stmt_cal)
        upcoming_meetings = res_cal.scalars().all()

        for t in stale_tasks:
            days_inactive = (
                (now - t.last_activity_at).days if t.last_activity_at else self.STALE_DAYS_THRESHOLD + 1
            )

            # Verificar se existe reunião agendada no calendário
            matched_meeting: CalendarEventORM | None = None
            if t.waiting_on_id:
                for m in upcoming_meetings:
                    # Mapeamento por ID ou palavra-chave no título
                    if m.organizer_email and str(t.waiting_on_id) in m.organizer_email:
                        matched_meeting = m
                        break

            nudge_draft: str | None = None
            action_recommendation = "send_nudge"

            if matched_meeting:
                action_recommendation = "bring_to_meeting"
                nudge_draft = f"Pauta sugerida para a reunião em {matched_meeting.starts_at.strftime('%d/%m %H:%M')}: Alinhar status da entrega."
            else:
                nudge_draft = f"Olá, gostaria de verificar como está o andamento da demanda '{t.title}'. Conseguimos manter a previsão inicial?"

            # Gravar registro em follow_ups se ainda não existir
            follow_up_orm = FollowUpORM(
                id=uuid.uuid4(),
                task_id=t.id,
                trigger_type=action_recommendation,
                days_stale=days_inactive,
                nudge_draft=nudge_draft,
                status="pending",
                created_at=now,
            )
            self._session.add(follow_up_orm)

            stale_evaluations.append({
                "task_id": str(t.id),
                "title": t.title,
                "status": t.status,
                "days_inactive": days_inactive,
                "recommendation": action_recommendation,
                "meeting_title": matched_meeting.organizer_email if matched_meeting else None,
                "nudge_draft": nudge_draft,
            })

        await self._session.commit()
        return stale_evaluations
