"""Entidades de estrutura organizacional e projetos: Area, Portfolio, Stakeholder, Milestone, Project."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime

from taskflow.domain.value_objects.enums import AreaKind, MilestoneStatus, ProjectStatus


@dataclass
class Area:
    """Área organizacional (unidade, departamento ou parceiro)."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = ""
    short_name: str | None = None
    parent_area_id: uuid.UUID | None = None
    kind: AreaKind = AreaKind.PEER_AREA
    is_own_team: bool = False  # Define tratamento ético (Seção 8)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Portfolio:
    """Portfólio de projetos."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = ""
    description: str | None = None
    owner_id: uuid.UUID | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Stakeholder:
    """Pessoa ou contato interno/externo com quem interagimos."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    email: str | None = None
    display_name: str = ""
    job_title: str | None = None
    department: str | None = None
    area_id: uuid.UUID | None = None
    area_source: str | None = None  # graph | manual
    graph_user_id: str | None = None
    avg_response_hours: float | None = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Project:
    """Projeto gerenciado."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = ""
    description: str | None = None
    status: ProjectStatus = ProjectStatus.ACTIVE
    portfolio_id: uuid.UUID | None = None
    owner_id: uuid.UUID | None = None
    area_id: uuid.UUID | None = None
    start_date: date | None = None
    target_date: date | None = None
    color: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Milestone:
    """Marco ou entrega intermediária de um projeto."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    project_id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = ""
    target_date: date = field(default_factory=date.today)
    owner_id: uuid.UUID | None = None
    status: MilestoneStatus = MilestoneStatus.PLANNED
    completed_at: date | None = None
    source: str = "manual"
    signal_id: uuid.UUID | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
