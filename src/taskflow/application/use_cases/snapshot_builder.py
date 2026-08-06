"""Append-only daily snapshot builder reconstructed from historical facts."""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taskflow.adapters.persistence.models import (
    CalendarEventORM,
    DailyCalendarSnapshotORM,
    DailyProjectSnapshotORM,
    DailyTaskSnapshotORM,
    MilestoneORM,
    ProjectORM,
    StakeholderORM,
    TaskORM,
    TaskStatusHistoryORM,
)
from taskflow.domain.policies.capacity_policy import CapacityPolicy, TimeBlock
from taskflow.domain.policies.health_score_policy import HealthScorePolicy
from taskflow.domain.ports.ports import UnitOfWork


class BuildDailySnapshotsUseCase:
    """Publishes immutable read-model rows; repeated builds are no-ops."""

    def __init__(
        self,
        session: AsyncSession,
        uow: UnitOfWork,
        capacity_policy: CapacityPolicy | None = None,
    ) -> None:
        self._session = session
        self._uow = uow
        self._capacity = capacity_policy or CapacityPolicy(buffer_minutes=0)

    async def execute(self, snapshot_date: date | None = None) -> dict[str, int]:
        target = snapshot_date or datetime.now(UTC).date()
        async with self._uow:
            tasks = await self._build_tasks(target)
            projects = await self._build_projects(target)
            calendars = await self._build_calendar(target)
            await self._uow.commit()
        return {"task_snapshots": tasks, "project_snapshots": projects,
                "calendar_snapshots": calendars}

    async def _build_tasks(self, target: date) -> int:
        existing = list((await self._session.execute(
            select(DailyTaskSnapshotORM).where(
                DailyTaskSnapshotORM.snapshot_date == target)
        )).scalars().all())
        if existing:
            return len(existing)

        day_end = datetime.combine(target, time.max)
        tasks = list((await self._session.execute(
            select(TaskORM).where(TaskORM.created_at <= day_end)
        )).scalars().all())
        histories = list((await self._session.execute(
            select(TaskStatusHistoryORM).where(
                TaskStatusHistoryORM.is_undone.is_(False),
            ).order_by(TaskStatusHistoryORM.created_at)
        )).scalars().all())
        by_task: dict[uuid.UUID, list[TaskStatusHistoryORM]] = defaultdict(list)
        for history in histories:
            by_task[history.task_id].append(history)

        projects = {project.id: project for project in
                    (await self._session.execute(select(ProjectORM))).scalars().all()}
        stakeholders = {stakeholder.id: stakeholder for stakeholder in
                        (await self._session.execute(select(StakeholderORM))).scalars().all()}

        for task in tasks:
            task_histories = by_task.get(task.id, [])
            status = self._status_at(task, task_histories, day_end)
            created_date = task.created_at.date()
            transitions = [(history.created_at.date(), history.to_status)
                           for history in task_histories]
            cumulative = self._cumulative_days(created_date, target, status, transitions)
            due_date = self._parse_date(task.due_date)
            original_due = self._parse_date(task.original_due_date)
            completed_today = any(history.to_status == "done"
                                  and history.created_at.date() == target
                                  for history in task_histories)
            if not task_histories and task.completed_at is not None:
                completed_today = task.completed_at.date() == target
            project = projects.get(task.project_id) if task.project_id else None
            requester = stakeholders.get(task.requester_id) if task.requester_id else None
            waiting = stakeholders.get(task.waiting_on_id) if task.waiting_on_id else None
            self._session.add(DailyTaskSnapshotORM(
                snapshot_date=target, task_id=task.id, status=status,
                priority=task.priority, task_type=task.task_type,
                demand_origin=task.demand_origin, project_id=task.project_id,
                portfolio_id=project.portfolio_id if project else None,
                milestone_id=task.milestone_id,
                requester_area_id=requester.area_id if requester else None,
                waiting_on_id=task.waiting_on_id,
                waiting_on_area_id=waiting.area_id if waiting else None,
                due_date=due_date, original_due_date=original_due,
                age_days=max(0, (target - created_date).days),
                days_in_status=self._days_in_status(target, task_histories, created_date),
                cum_days_open=cumulative["open"],
                cum_days_in_progress=cumulative["in_progress"],
                cum_days_waiting=cumulative["waiting_on_others"],
                cum_days_blocked=cumulative["blocked"],
                is_overdue=bool(due_date and due_date < target
                                and status not in ("done", "cancelled")),
                completed_today=completed_today, created_today=created_date == target,
                estimated_effort_minutes=task.estimated_effort_minutes,
            ))
        return len(tasks)

    @staticmethod
    def _status_at(
        task: TaskORM, histories: list[TaskStatusHistoryORM], day_end: datetime,
    ) -> str:
        before = [history for history in histories if history.created_at <= day_end]
        if before:
            return before[-1].to_status
        after = [history for history in histories if history.created_at > day_end]
        if after and after[0].from_status:
            return str(after[0].from_status)
        return str(task.status)

    @staticmethod
    def _parse_date(raw: str | None) -> date | None:
        if not raw:
            return None
        try:
            return date.fromisoformat(raw[:10])
        except ValueError:
            return None

    @staticmethod
    def _days_in_status(
        target: date, histories: list[TaskStatusHistoryORM], created: date,
    ) -> int:
        relevant = [history.created_at.date() for history in histories
                    if history.created_at.date() <= target]
        entered = relevant[-1] if relevant else created
        return max(0, (target - entered).days)

    @staticmethod
    def _cumulative_days(
        created: date, target: date, status: str,
        transitions: list[tuple[date, str]],
    ) -> dict[str, int]:
        totals = {"open": 0, "in_progress": 0, "waiting_on_others": 0, "blocked": 0}
        current_status = transitions[0][1] if transitions else status
        cursor = created
        for transition_date, next_status in transitions:
            if transition_date > target:
                break
            if current_status in totals:
                totals[current_status] += max(0, (transition_date - cursor).days)
            current_status, cursor = next_status, transition_date
        if current_status in totals:
            totals[current_status] += max(0, (target - cursor).days)
        totals["open"] = max(totals["open"], max(0, (target - created).days))
        return totals

    async def _build_projects(self, target: date) -> int:
        existing = list((await self._session.execute(
            select(DailyProjectSnapshotORM).where(
                DailyProjectSnapshotORM.snapshot_date == target)
        )).scalars().all())
        if existing:
            return len(existing)
        projects = list((await self._session.execute(
            select(ProjectORM).where(ProjectORM.created_at <= datetime.combine(target, time.max))
        )).scalars().all())
        snapshots = list((await self._session.execute(
            select(DailyTaskSnapshotORM).where(
                DailyTaskSnapshotORM.snapshot_date == target)
        )).scalars().all())
        milestones = list((await self._session.execute(
            select(MilestoneORM).where(
                MilestoneORM.created_at <= datetime.combine(target, time.max))
        )).scalars().all())
        for project in projects:
            tasks = [item for item in snapshots if item.project_id == project.id]
            project_milestones = [item for item in milestones if item.project_id == project.id]
            open_tasks = [item for item in tasks if item.status not in ("done", "cancelled")]
            blocked = [item for item in tasks if item.status == "blocked"]
            last_activity_days = min((item.days_in_status for item in tasks), default=None)
            oldest_blocked = max((item.days_in_status for item in blocked), default=None)
            health = HealthScorePolicy.calculate(
                tasks_total=len(tasks), tasks_open=len(open_tasks),
                tasks_in_progress=sum(item.status == "in_progress" for item in tasks),
                tasks_blocked=len(blocked), tasks_overdue=sum(item.is_overdue for item in tasks),
                milestones_total=len(project_milestones),
                milestones_at_risk=sum(item.status == "at_risk" for item in project_milestones),
                milestones_missed=sum(item.status == "missed" for item in project_milestones),
                days_since_activity=last_activity_days, oldest_blocked_days=oldest_blocked,
            )
            self._session.add(DailyProjectSnapshotORM(
                snapshot_date=target, project_id=project.id,
                portfolio_id=project.portfolio_id, status=project.status,
                tasks_total=len(tasks), tasks_open=len(open_tasks),
                tasks_in_progress=sum(item.status == "in_progress" for item in tasks),
                tasks_waiting=sum(item.status == "waiting_on_others" for item in tasks),
                tasks_blocked=len(blocked), tasks_done=sum(item.status == "done" for item in tasks),
                tasks_overdue=sum(item.is_overdue for item in tasks),
                milestones_total=len(project_milestones),
                milestones_at_risk=sum(item.status == "at_risk" for item in project_milestones),
                milestones_missed=sum(item.status == "missed" for item in project_milestones),
                days_since_activity=last_activity_days, oldest_blocked_days=oldest_blocked,
                health_score=health.score, health_components=health.components,
            ))
        return len(projects)

    async def _build_calendar(self, target: date) -> int:
        existing = await self._session.get(DailyCalendarSnapshotORM, target)
        if existing is not None:
            return 1
        start = datetime.combine(target, time.min)
        end = datetime.combine(target, time.max)
        events = list((await self._session.execute(select(CalendarEventORM).where(
            CalendarEventORM.starts_at <= end, CalendarEventORM.ends_at >= start,
            CalendarEventORM.is_cancelled.is_(False),
        ))).scalars().all())
        occupied = [event for event in events
                    if not event.is_all_day and event.my_response != "declined"
                    and event.show_as != "free"]
        blocks = [TimeBlock(event.starts_at, event.ends_at, is_all_day=event.is_all_day)
                  for event in occupied]
        capacity = self._capacity.compute(start, blocks)
        meeting_minutes = round(capacity.meeting_minutes)
        available = round(capacity.total_work_minutes)
        self._session.add(DailyCalendarSnapshotORM(
            snapshot_date=target, total_meeting_minutes=meeting_minutes,
            meeting_count=len(occupied),
            recurring_count=sum(event.is_recurring for event in occupied),
            with_agenda_count=sum(event.has_agenda for event in occupied),
            produced_actions_count=sum(event.produced_action_items for event in occupied),
            available_minutes=available,
            utilization_pct=(round(meeting_minutes / available, 4) if available else None),
            declined_count=sum(event.my_response == "declined" for event in events),
            minutes_by_class=self._minutes_by(occupied, "meeting_class"),
            minutes_by_project=self._minutes_by(occupied, "attributed_project_id"),
        ))
        return 1

    @staticmethod
    def _minutes_by(events: list[CalendarEventORM], attribute: str) -> dict[str, int]:
        result: dict[str, int] = {}
        for event in events:
            key = str(getattr(event, attribute) or "unknown")
            result[key] = result.get(key, 0) + int(event.duration_minutes or 0)
        return result
