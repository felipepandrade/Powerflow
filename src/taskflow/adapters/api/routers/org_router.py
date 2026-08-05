"""Router FastAPI para estrutura organizacional (Áreas, Portfólios, Projetos, Marcos, Stakeholders)."""

import uuid
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taskflow.adapters.api.schemas.schemas import (
    AreaCreateRequest,
    AreaSchema,
    MilestoneCreateRequest,
    MilestoneSchema,
    PortfolioCreateRequest,
    PortfolioSchema,
    ProjectCreateRequest,
    ProjectSchema,
    StakeholderCreateRequest,
    StakeholderSchema,
)
from taskflow.adapters.persistence.models import (
    AreaORM,
    MilestoneORM,
    PortfolioORM,
    ProjectORM,
    StakeholderORM,
)
from taskflow.config.container import get_db_session

router = APIRouter(prefix="/api/org", tags=["Organization"])


# ── Áreas ─────────────────────────────────────────────────────────────

@router.get("/areas", response_model=list[AreaSchema])
async def list_areas(session: AsyncSession = Depends(get_db_session)) -> list[AreaSchema]:
    stmt = select(AreaORM)
    result = await session.execute(stmt)
    orms = result.scalars().all()
    return [AreaSchema.model_validate(o) for o in orms]


@router.post("/areas", response_model=AreaSchema, status_code=201)
async def create_area(
    req: AreaCreateRequest, session: AsyncSession = Depends(get_db_session)
) -> AreaSchema:
    orm = AreaORM(
        id=uuid.uuid4(),
        name=req.name,
        short_name=req.short_name,
        parent_area_id=req.parent_area_id,
        kind=req.kind,
        is_own_team=req.is_own_team,
    )
    session.add(orm)
    await session.commit()
    return AreaSchema.model_validate(orm)


# ── Portfólios ────────────────────────────────────────────────────────

@router.get("/portfolios", response_model=list[PortfolioSchema])
async def list_portfolios(session: AsyncSession = Depends(get_db_session)) -> list[PortfolioSchema]:
    stmt = select(PortfolioORM)
    result = await session.execute(stmt)
    orms = result.scalars().all()
    return [PortfolioSchema.model_validate(o) for o in orms]


@router.post("/portfolios", response_model=PortfolioSchema, status_code=201)
async def create_portfolio(
    req: PortfolioCreateRequest, session: AsyncSession = Depends(get_db_session)
) -> PortfolioSchema:
    orm = PortfolioORM(
        id=uuid.uuid4(),
        name=req.name,
        description=req.description,
        owner_id=req.owner_id,
    )
    session.add(orm)
    await session.commit()
    return PortfolioSchema.model_validate(orm)


# ── Stakeholders ──────────────────────────────────────────────────────

@router.get("/stakeholders", response_model=list[StakeholderSchema])
async def list_stakeholders(session: AsyncSession = Depends(get_db_session)) -> list[StakeholderSchema]:
    stmt = select(StakeholderORM)
    result = await session.execute(stmt)
    orms = result.scalars().all()
    return [StakeholderSchema.model_validate(o) for o in orms]


@router.post("/stakeholders", response_model=StakeholderSchema, status_code=201)
async def create_stakeholder(
    req: StakeholderCreateRequest, session: AsyncSession = Depends(get_db_session)
) -> StakeholderSchema:
    orm = StakeholderORM(
        id=uuid.uuid4(),
        email=req.email,
        display_name=req.display_name,
        job_title=req.job_title,
        department=req.department,
        area_id=req.area_id,
    )
    session.add(orm)
    await session.commit()
    return StakeholderSchema.model_validate(orm)


# ── Projetos ──────────────────────────────────────────────────────────

@router.get("/projects", response_model=list[ProjectSchema])
async def list_projects(session: AsyncSession = Depends(get_db_session)) -> list[ProjectSchema]:
    stmt = select(ProjectORM)
    result = await session.execute(stmt)
    orms = result.scalars().all()
    return [ProjectSchema.model_validate(o) for o in orms]


@router.post("/projects", response_model=ProjectSchema, status_code=201)
async def create_project(
    req: ProjectCreateRequest, session: AsyncSession = Depends(get_db_session)
) -> ProjectSchema:
    orm = ProjectORM(
        id=uuid.uuid4(),
        name=req.name,
        description=req.description,
        status=req.status,
        portfolio_id=req.portfolio_id,
        owner_id=req.owner_id,
        area_id=req.area_id,
        color=req.color,
    )
    session.add(orm)
    await session.commit()
    return ProjectSchema.model_validate(orm)


# ── Marcos ────────────────────────────────────────────────────────────

@router.get("/projects/{project_id}/milestones", response_model=list[MilestoneSchema])
async def list_milestones(
    project_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)
) -> list[MilestoneSchema]:
    stmt = select(MilestoneORM).where(MilestoneORM.project_id == project_id)
    result = await session.execute(stmt)
    orms = result.scalars().all()
    return [MilestoneSchema.model_validate(o) for o in orms]


@router.post("/milestones", response_model=MilestoneSchema, status_code=201)
async def create_milestone(
    req: MilestoneCreateRequest, session: AsyncSession = Depends(get_db_session)
) -> MilestoneSchema:
    orm = MilestoneORM(
        id=uuid.uuid4(),
        project_id=req.project_id,
        name=req.name,
        target_date=date.fromisoformat(req.target_date),
        status=req.status,
    )
    session.add(orm)
    await session.commit()
    return MilestoneSchema.model_validate(orm)
