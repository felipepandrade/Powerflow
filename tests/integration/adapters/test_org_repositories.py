"""Testes de integração para os novos repositórios SQLAlchemy."""

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from taskflow.adapters.persistence.models import Base
from taskflow.adapters.persistence.org_repositories import (
    SqlAlchemyAreaRepository,
    SqlAlchemyMilestoneRepository,
    SqlAlchemyProjectRepository,
    SqlAlchemyStakeholderRepository,
)
from taskflow.domain.entities.org import Area, Milestone, Project, Stakeholder
from taskflow.domain.value_objects.enums import (
    AreaKind,
    MilestoneStatus,
    ProjectStatus,
)


@pytest.fixture
async def db_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_area_repository_crud(db_session: AsyncSession) -> None:
    repo = SqlAlchemyAreaRepository(db_session)
    area = Area(name="TI", kind=AreaKind.OWN_TEAM, is_own_team=True)

    await repo.save(area)
    await db_session.commit()

    fetched = await repo.get_by_id(area.id)
    assert fetched is not None
    assert fetched.name == "TI"
    assert fetched.is_own_team is True

    all_areas = await repo.list_all()
    assert len(all_areas) == 1


@pytest.mark.asyncio
async def test_stakeholder_repository_crud(db_session: AsyncSession) -> None:
    repo = SqlAlchemyStakeholderRepository(db_session)
    st = Stakeholder(email="maria@example.com", display_name="Maria Santos")

    await repo.save(st)
    await db_session.commit()

    fetched_by_id = await repo.get_by_id(st.id)
    assert fetched_by_id is not None
    assert fetched_by_id.display_name == "Maria Santos"

    fetched_by_email = await repo.get_by_email("maria@example.com")
    assert fetched_by_email is not None
    assert fetched_by_email.id == st.id


@pytest.mark.asyncio
async def test_project_and_milestone_repository(db_session: AsyncSession) -> None:
    proj_repo = SqlAlchemyProjectRepository(db_session)
    ms_repo = SqlAlchemyMilestoneRepository(db_session)

    project = Project(name="TaskFlow v1.2", status=ProjectStatus.ACTIVE)
    await proj_repo.save(project)

    ms = Milestone(project_id=project.id, name="M1 Release", target_date=date.today(), status=MilestoneStatus.PLANNED)
    await ms_repo.save(ms)
    await db_session.commit()

    fetched_proj = await proj_repo.get_by_id(project.id)
    assert fetched_proj is not None
    assert fetched_proj.name == "TaskFlow v1.2"

    project_milestones = await ms_repo.find_by_project(project.id)
    assert len(project_milestones) == 1
    assert project_milestones[0].name == "M1 Release"
