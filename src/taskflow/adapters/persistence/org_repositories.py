"""Implementações SQLAlchemy dos novos repositórios de domínio."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taskflow.adapters.persistence.models import (
    AreaORM,
    CalendarEventORM,
    MilestoneORM,
    ProjectORM,
    StakeholderORM,
)
from taskflow.domain.entities.org import Area, Milestone, Project, Stakeholder
from taskflow.domain.entities.source import CalendarEvent
from taskflow.domain.ports.ports import (
    AreaRepository,
    CalendarRepository,
    MilestoneRepository,
    ProjectRepository,
    StakeholderRepository,
)
from taskflow.domain.value_objects.enums import AreaKind, MilestoneStatus, ProjectStatus


class SqlAlchemyAreaRepository(AreaRepository):
    """Repositório SQLAlchemy para Áreas."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, area_id: uuid.UUID) -> Area | None:
        stmt = select(AreaORM).where(AreaORM.id == area_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_entity(orm) if orm else None

    async def save(self, area: Area) -> None:
        orm = await self._session.get(AreaORM, area.id)
        if not orm:
            orm = AreaORM(
                id=area.id,
                name=area.name,
                short_name=area.short_name,
                parent_area_id=area.parent_area_id,
                kind=area.kind.value,
                is_own_team=area.is_own_team,
                created_at=area.created_at,
            )
            self._session.add(orm)
        else:
            orm.name = area.name
            orm.short_name = area.short_name
            orm.parent_area_id = area.parent_area_id
            orm.kind = area.kind.value
            orm.is_own_team = area.is_own_team

    async def list_all(self) -> Sequence[Area]:
        stmt = select(AreaORM)
        result = await self._session.execute(stmt)
        orms = result.scalars().all()
        return [self._to_entity(o) for o in orms]

    def _to_entity(self, orm: AreaORM) -> Area:
        return Area(
            id=orm.id,
            name=orm.name,
            short_name=orm.short_name,
            parent_area_id=orm.parent_area_id,
            kind=AreaKind(orm.kind),
            is_own_team=orm.is_own_team,
            created_at=orm.created_at,
        )


class SqlAlchemyStakeholderRepository(StakeholderRepository):
    """Repositório SQLAlchemy para Stakeholders."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, stakeholder_id: uuid.UUID) -> Stakeholder | None:
        stmt = select(StakeholderORM).where(StakeholderORM.id == stakeholder_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_entity(orm) if orm else None

    async def get_by_email(self, email: str) -> Stakeholder | None:
        stmt = select(StakeholderORM).where(StakeholderORM.email == email)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_entity(orm) if orm else None

    async def save(self, stakeholder: Stakeholder) -> None:
        orm = await self._session.get(StakeholderORM, stakeholder.id)
        if not orm:
            orm = StakeholderORM(
                id=stakeholder.id,
                email=stakeholder.email,
                display_name=stakeholder.display_name,
                job_title=stakeholder.job_title,
                department=stakeholder.department,
                area_id=stakeholder.area_id,
                area_source=stakeholder.area_source,
                graph_user_id=stakeholder.graph_user_id,
                avg_response_hours=stakeholder.avg_response_hours,
                is_active=stakeholder.is_active,
                created_at=stakeholder.created_at,
            )
            self._session.add(orm)
        else:
            orm.email = stakeholder.email
            orm.display_name = stakeholder.display_name
            orm.job_title = stakeholder.job_title
            orm.department = stakeholder.department
            orm.area_id = stakeholder.area_id
            orm.area_source = stakeholder.area_source
            orm.graph_user_id = stakeholder.graph_user_id
            orm.avg_response_hours = stakeholder.avg_response_hours
            orm.is_active = stakeholder.is_active

    async def list_all(self) -> Sequence[Stakeholder]:
        stmt = select(StakeholderORM)
        result = await self._session.execute(stmt)
        orms = result.scalars().all()
        return [self._to_entity(o) for o in orms]

    def _to_entity(self, orm: StakeholderORM) -> Stakeholder:
        return Stakeholder(
            id=orm.id,
            email=orm.email,
            display_name=orm.display_name,
            job_title=orm.job_title,
            department=orm.department,
            area_id=orm.area_id,
            area_source=orm.area_source,
            graph_user_id=orm.graph_user_id,
            avg_response_hours=orm.avg_response_hours,
            is_active=orm.is_active,
            created_at=orm.created_at,
        )


class SqlAlchemyProjectRepository(ProjectRepository):
    """Repositório SQLAlchemy para Projetos."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, project_id: uuid.UUID) -> Project | None:
        stmt = select(ProjectORM).where(ProjectORM.id == project_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_entity(orm) if orm else None

    async def save(self, project: Project) -> None:
        orm = await self._session.get(ProjectORM, project.id)
        if not orm:
            orm = ProjectORM(
                id=project.id,
                name=project.name,
                description=project.description,
                status=project.status.value,
                portfolio_id=project.portfolio_id,
                owner_id=project.owner_id,
                area_id=project.area_id,
                start_date=project.start_date,
                target_date=project.target_date,
                color=project.color,
                created_at=project.created_at,
                updated_at=project.updated_at,
            )
            self._session.add(orm)
        else:
            orm.name = project.name
            orm.description = project.description
            orm.status = project.status.value
            orm.portfolio_id = project.portfolio_id
            orm.owner_id = project.owner_id
            orm.area_id = project.area_id
            orm.start_date = project.start_date
            orm.target_date = project.target_date
            orm.color = project.color
            orm.updated_at = datetime.utcnow()

    async def list_all(self) -> Sequence[Project]:
        stmt = select(ProjectORM)
        result = await self._session.execute(stmt)
        orms = result.scalars().all()
        return [self._to_entity(o) for o in orms]

    def _to_entity(self, orm: ProjectORM) -> Project:
        return Project(
            id=orm.id,
            name=orm.name,
            description=orm.description,
            status=ProjectStatus(orm.status),
            portfolio_id=orm.portfolio_id,
            owner_id=orm.owner_id,
            area_id=orm.area_id,
            start_date=orm.start_date,
            target_date=orm.target_date,
            color=orm.color,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )


class SqlAlchemyMilestoneRepository(MilestoneRepository):
    """Repositório SQLAlchemy para Marcos."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, milestone_id: uuid.UUID) -> Milestone | None:
        stmt = select(MilestoneORM).where(MilestoneORM.id == milestone_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_entity(orm) if orm else None

    async def save(self, milestone: Milestone) -> None:
        orm = await self._session.get(MilestoneORM, milestone.id)
        if not orm:
            orm = MilestoneORM(
                id=milestone.id,
                project_id=milestone.project_id,
                name=milestone.name,
                target_date=milestone.target_date,
                owner_id=milestone.owner_id,
                status=milestone.status.value,
                completed_at=milestone.completed_at,
                source=milestone.source,
                signal_id=milestone.signal_id,
                created_at=milestone.created_at,
                updated_at=milestone.updated_at,
            )
            self._session.add(orm)
        else:
            orm.name = milestone.name
            orm.target_date = milestone.target_date
            orm.owner_id = milestone.owner_id
            orm.status = milestone.status.value
            orm.completed_at = milestone.completed_at
            orm.updated_at = datetime.utcnow()

    async def find_by_project(self, project_id: uuid.UUID) -> Sequence[Milestone]:
        stmt = select(MilestoneORM).where(MilestoneORM.project_id == project_id)
        result = await self._session.execute(stmt)
        orms = result.scalars().all()
        return [self._to_entity(o) for o in orms]

    def _to_entity(self, orm: MilestoneORM) -> Milestone:
        return Milestone(
            id=orm.id,
            project_id=orm.project_id,
            name=orm.name,
            target_date=orm.target_date,
            owner_id=orm.owner_id,
            status=MilestoneStatus(orm.status),
            completed_at=orm.completed_at,
            source=orm.source,
            signal_id=orm.signal_id,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )


class SqlAlchemyCalendarRepository(CalendarRepository):
    """Repositório SQLAlchemy para Calendário."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, event: CalendarEvent) -> None:
        orm = await self._session.get(CalendarEventORM, event.source_item_id)
        if not orm:
            orm = CalendarEventORM(
                source_item_id=event.source_item_id,
                graph_event_id=event.graph_event_id,
                series_master_id=event.series_master_id,
                instance_type=event.instance_type,
                body_hash=event.body_hash,
                starts_at=event.starts_at,
                ends_at=event.ends_at,
                duration_minutes=int(event.duration_minutes),
                is_all_day=event.is_all_day,
                timezone=event.timezone,
                location=event.location,
                is_online=event.is_online,
                join_url=event.join_url,
                linked_chat_id=event.linked_chat_id,
                organizer_email=event.organizer_email,
                my_response=event.my_response,
                show_as=event.show_as,
                sensitivity=event.sensitivity.value if hasattr(event.sensitivity, "value") else str(event.sensitivity),
                is_cancelled=event.is_cancelled,
                recurrence_rule=event.recurrence_rule,
                attendee_count=event.attendee_count,
                categories=event.categories,
            )
            self._session.add(orm)
        else:
            orm.starts_at = event.starts_at
            orm.ends_at = event.ends_at
            orm.duration_minutes = int(event.duration_minutes)
            orm.is_cancelled = event.is_cancelled

    async def find_in_range(self, start: datetime, end: datetime) -> Sequence[CalendarEvent]:
        stmt = select(CalendarEventORM).where(
            CalendarEventORM.starts_at >= start,
            CalendarEventORM.ends_at <= end,
        )
        result = await self._session.execute(stmt)
        orms = result.scalars().all()
        return [self._to_entity(o) for o in orms]

    def _to_entity(self, orm: CalendarEventORM) -> CalendarEvent:
        from taskflow.domain.value_objects.enums import CalendarSensitivity
        return CalendarEvent(
            source_item_id=orm.source_item_id,
            graph_event_id=orm.graph_event_id,
            series_master_id=orm.series_master_id,
            instance_type=orm.instance_type,
            body_hash=orm.body_hash,
            starts_at=orm.starts_at,
            ends_at=orm.ends_at,
            is_all_day=orm.is_all_day,
            timezone=orm.timezone,
            location=orm.location,
            is_online=orm.is_online,
            join_url=orm.join_url,
            linked_chat_id=orm.linked_chat_id,
            organizer_email=orm.organizer_email,
            my_response=orm.my_response,
            show_as=orm.show_as,
            sensitivity=CalendarSensitivity(orm.sensitivity) if orm.sensitivity else CalendarSensitivity.NORMAL,
            is_cancelled=orm.is_cancelled,
            recurrence_rule=orm.recurrence_rule,
            attendee_count=orm.attendee_count,
            categories=orm.categories or [],
        )
