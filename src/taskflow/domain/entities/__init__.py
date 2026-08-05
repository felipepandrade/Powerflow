"""Domain entities package."""

from taskflow.domain.entities.org import (
    Area,
    Milestone,
    Portfolio,
    Project,
    Stakeholder,
)
from taskflow.domain.entities.source import (
    CalendarEvent,
    CorrelationRun,
    Signal,
    SourceItem,
)
from taskflow.domain.entities.task import (
    FollowUp,
    StakeholderInteraction,
    Task,
    TaskEvidence,
    TaskProposal,
    TaskStatusHistory,
    TaskUpdate,
)

__all__ = [
    "Area",
    "CalendarEvent",
    "CorrelationRun",
    "FollowUp",
    "Milestone",
    "Portfolio",
    "Project",
    "Signal",
    "SourceItem",
    "Stakeholder",
    "StakeholderInteraction",
    "Task",
    "TaskEvidence",
    "TaskProposal",
    "TaskStatusHistory",
    "TaskUpdate",
]

