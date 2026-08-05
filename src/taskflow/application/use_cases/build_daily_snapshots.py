"""Use Case: BuildDailySnapshots — UC-Analytics-1.

Gera os snapshots diários de tarefas, projetos e calendário (append-only/idempotente)
que servem como fundação para o motor de métricas e dashboards do Cockpit.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

import structlog
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from taskflow.adapters.persistence.models import (
    CalendarEventORM,
    DailyCalendarSnapshotORM,
    DailyProjectSnapshotORM,
    DailyTaskSnapshotORM,
    MilestoneORM,
    ProjectORM,
    TaskORM,
)
from taskflow.domain.policies.health_score_policy import HealthScorePolicy
from taskflow.domain.ports.ports import UnitOfWork

log = structlog.get_logger()


class BuildDailySnapshotsUseCase:
    """UC-Analytics-1 — Construção de Snapshots Diários Idempotentes."""

    def __init__(self, session: AsyncSession, uow: UnitOfWork) -> None:
        self._session = session
        self._uow = uow

    async def execute(self, snapshot_date: date | None = None) -> dict[str, int]:
        """Executa a geração de snapshots para a data informada (padrão: hoje)."""
        target_date = snapshot_date or date.today()
        log.info("analytics.snapshots.start", target_date=target_date.isoformat())

        async with self._uow:
            # 1. Snapshots de Tarefas
            tasks_count = await self._build_task_snapshots(target_date)

            # 2. Snapshots de Projetos
            projects_count = await self._build_project_snapshots(target_date)

            # 3. Snapshots de Calendário
            calendar_count = await self._build_calendar_snapshots(target_date)

            await self._uow.commit()

        log.info(
            "analytics.snapshots.completed",
            target_date=target_date.isoformat(),
            tasks=tasks_count,
            projects=projects_count,
            calendar=calendar_count,
        )

        return {
            "task_snapshots": tasks_count,
            "project_snapshots": projects_count,
            "calendar_snapshots": calendar_count,
        }

    async def _build_task_snapshots(self, target_date: date) -> int:
        # Remover snapshots existentes da mesma data (idempotência)
        await self._session.execute(
            delete(DailyTaskSnapshotORM).where(DailyTaskSnapshotORM.snapshot_date == target_date)
        )

        # Buscar tarefas ativas ou concluídas no dia
        stmt = select(TaskORM)
        result = await self._session.execute(stmt)
        tasks = result.scalars().all()

        count = 0
        for task in tasks:
            created_dt = task.created_at.date() if isinstance(task.created_at, datetime) else target_date
            last_act_dt = task.last_activity_at.date() if isinstance(task.last_activity_at, datetime) else target_date

            age_days = (target_date - created_dt).days
            days_in_status = (target_date - last_act_dt).days

            due_dt = None
            if task.due_date:
                try:
                    due_dt = date.fromisoformat(task.due_date)
                except ValueError:
                    pass

            is_overdue = due_dt < target_date if (due_dt and task.status not in ("done", "cancelled")) else False

            snapshot = DailyTaskSnapshotORM(
                snapshot_date=target_date,
                task_id=task.id,
                status=task.status,
                priority=task.priority,
                task_type=task.task_type,
                demand_origin=task.demand_origin,
                project_id=task.project_id,
                milestone_id=task.milestone_id,
                waiting_on_id=task.waiting_on_id,
                due_date=due_dt,
                age_days=max(0, age_days),
                days_in_status=max(0, days_in_status),
                cum_days_open=max(0, age_days),
                cum_days_in_progress=0,
                cum_days_waiting=0,
                cum_days_blocked=0,
                is_overdue=is_overdue,
                completed_today=task.completed_at.date() == target_date if task.completed_at else False,
                created_today=created_dt == target_date,
                estimated_effort_minutes=task.estimated_effort_minutes,
            )
            self._session.add(snapshot)
            count += 1

        return count

    async def _build_project_snapshots(self, target_date: date) -> int:
        await self._session.execute(
            delete(DailyProjectSnapshotORM).where(DailyProjectSnapshotORM.snapshot_date == target_date)
        )

        stmt = select(ProjectORM)
        result = await self._session.execute(stmt)
        projects = result.scalars().all()

        count = 0
        for proj in projects:
            # Buscar métricas agregadas do projeto a partir dos snapshots de tarefas do dia
            tasks_stmt = select(DailyTaskSnapshotORM).where(
                DailyTaskSnapshotORM.snapshot_date == target_date,
                DailyTaskSnapshotORM.project_id == proj.id,
            )
            res_tasks = await self._session.execute(tasks_stmt)
            p_tasks = res_tasks.scalars().all()

            tasks_total = len(p_tasks)
            tasks_open = sum(1 for t in p_tasks if t.status not in ("done", "cancelled"))
            tasks_in_progress = sum(1 for t in p_tasks if t.status == "in_progress")
            tasks_waiting = sum(1 for t in p_tasks if t.status == "waiting_on_others")
            tasks_blocked = sum(1 for t in p_tasks if t.status == "blocked")
            tasks_done = sum(1 for t in p_tasks if t.status == "done")
            tasks_overdue = sum(1 for t in p_tasks if t.is_overdue)

            # Marcos
            ms_stmt = select(MilestoneORM).where(MilestoneORM.project_id == proj.id)
            res_ms = await self._session.execute(ms_stmt)
            milestones = res_ms.scalars().all()

            ms_total = len(milestones)
            ms_at_risk = sum(1 for m in milestones if m.status == "at_risk")
            ms_missed = sum(1 for m in milestones if m.status == "missed")

            health_res = HealthScorePolicy.calculate(
                tasks_total=tasks_total,
                tasks_open=tasks_open,
                tasks_in_progress=tasks_in_progress,
                tasks_blocked=tasks_blocked,
                tasks_overdue=tasks_overdue,
                milestones_total=ms_total,
                milestones_at_risk=ms_at_risk,
                milestones_missed=ms_missed,
                days_since_activity=0,
                oldest_blocked_days=0,
            )

            p_snapshot = DailyProjectSnapshotORM(
                snapshot_date=target_date,
                project_id=proj.id,
                portfolio_id=proj.portfolio_id,
                status=proj.status,
                tasks_total=tasks_total,
                tasks_open=tasks_open,
                tasks_in_progress=tasks_in_progress,
                tasks_waiting=tasks_waiting,
                tasks_blocked=tasks_blocked,
                tasks_done=tasks_done,
                tasks_overdue=tasks_overdue,
                milestones_total=ms_total,
                milestones_at_risk=ms_at_risk,
                milestones_missed=ms_missed,
                health_score=health_res.score,
                health_components=health_res.components,
            )
            self._session.add(p_snapshot)
            count += 1

        return count

    async def _build_calendar_snapshots(self, target_date: date) -> int:
        await self._session.execute(
            delete(DailyCalendarSnapshotORM).where(DailyCalendarSnapshotORM.snapshot_date == target_date)
        )

        # Eventos do dia
        start_dt = datetime.combine(target_date, datetime.min.time())
        end_dt = datetime.combine(target_date, datetime.max.time())

        stmt = select(CalendarEventORM).where(
            CalendarEventORM.starts_at >= start_dt,
            CalendarEventORM.starts_at <= end_dt,
        )
        result = await self._session.execute(stmt)
        events = result.scalars().all()

        total_min = sum(e.duration_minutes or 0 for e in events)
        recurring_cnt = sum(1 for e in events if e.is_recurring)

        cal_snapshot = DailyCalendarSnapshotORM(
            snapshot_date=target_date,
            total_meeting_minutes=total_min,
            meeting_count=len(events),
            recurring_count=recurring_cnt,
            available_minutes=480,  # 8h padrão
            utilization_pct=round(min(1.0, total_min / 480.0), 2) if total_min else 0.0,
        )
        self._session.add(cal_snapshot)
        return 1
