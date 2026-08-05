"""Domain entities package."""

from taskflow.domain.entities.source import (
    CalendarEvent,
    CorrelationRun,
    Signal,
    SourceItem,
)
from taskflow.domain.entities.task import (
    FollowUp,
    Project,
    Stakeholder,
    StakeholderInteraction,
    Task,
    TaskEvidence,
    TaskProposal,
    TaskStatusHistory,
    TaskUpdate,
)

__all__ = [
    "CalendarEvent",
    "CorrelationRun",
    "FollowUp",
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

