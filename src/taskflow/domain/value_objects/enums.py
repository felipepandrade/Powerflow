"""Value Objects para o domínio TaskFlow."""

from enum import Enum


class TaskStatus(str, Enum):
    """Estados possíveis de uma tarefa — conforme máquina de estados RF-D.1."""

    INBOX = "inbox"
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_ON_OTHERS = "waiting_on_others"
    BLOCKED = "blocked"
    DONE = "done"
    CANCELLED = "cancelled"


class Priority(str, Enum):
    """Níveis de prioridade de uma tarefa."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskType(str, Enum):
    """Tipo de tarefa conforme extração de sinal RF-C.2."""

    ACTION = "action"
    DECISION = "decision"
    APPROVAL = "approval"
    INFORMATION_REQUEST = "information_request"
    COMMITMENT_MADE = "commitment_made"


class ActorType(str, Enum):
    """Ator responsável pela mudança de estado."""

    USER = "user"
    SYSTEM = "system"
    LLM = "llm"


class SourceKind(str, Enum):
    """Tipo de item de origem — discriminador canônico."""

    EMAIL = "email"
    TEAMS_CHAT = "teams_chat"
    CALENDAR_EVENT = "calendar_event"


class SignalType(str, Enum):
    """Tipos de sinal extraídos por LLM — RF-C.2 e RF-F.5."""

    COMMITMENT = "commitment"
    PROGRESS_UPDATE = "progress_update"
    COMPLETION = "completion"
    BLOCKER = "blocker"
    DUE_DATE_CHANGE = "due_date_change"
    PREP_REQUIRED = "prep_required"
    AGENDA_COMMITMENT = "agenda_commitment"
    DEADLINE_ANCHOR = "deadline_anchor"
    INTERACTION = "interaction"
    FORUM_AVAILABLE = "forum_available"
    CAPACITY = "capacity"
    SCHEDULE_CHANGE = "schedule_change"
    CONTEXT = "context"


class SignalState(str, Enum):
    """Estado do sinal no pipeline de correlação."""

    PENDING_CORRELATION = "pending_correlation"
    RESOLVED = "resolved"
    EXPIRED = "expired"
    DISCARDED = "discarded"


class DecisionKind(str, Enum):
    """Decisão do motor de correlação — RF-G.8."""

    NEW_TASK = "NEW_TASK"
    UPDATE_EXISTING = "UPDATE_EXISTING"
    TRANSITION_EXISTING = "TRANSITION_EXISTING"
    SPLIT = "SPLIT"
    MERGE_DUPLICATE = "MERGE_DUPLICATE"
    ATTACH_CONTEXT = "ATTACH_CONTEXT"
    NOISE = "NOISE"


class RelationType(str, Enum):
    """Tipo de relação avaliada pelo LLM no estágio G2."""

    SAME_TASK = "same_task"
    STATUS_UPDATE = "status_update"
    DUE_DATE_CHANGE = "due_date_change"
    SCOPE_CHANGE = "scope_change"
    SUBTASK_OF = "subtask_of"
    BLOCKS = "blocks"
    DUPLICATE_OF = "duplicate_of"
    RELATED_CONTEXT = "related_context"
    UNRELATED = "unrelated"


class DueDateConfidence(str, Enum):
    """Confiança na data de prazo extraída."""

    EXPLICIT = "explicit"
    INFERRED = "inferred"
    NONE = "none"


class OwnerType(str, Enum):
    """Tipo de propriedade da tarefa/sinal."""

    ME = "me"
    DELEGATED = "delegated"
    SHARED = "shared"
    UNCLEAR = "unclear"


class ProposalKind(str, Enum):
    """Tipo de proposta de triagem."""

    NEW_TASK = "new_task"
    UPDATE = "update"
    TRANSITION = "transition"
    MERGE = "merge"
    SPLIT = "split"
    DISAMBIGUATE = "disambiguate"


class ProposalStatus(str, Enum):
    """Status de uma proposta de triagem."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MERGED = "merged"
    EXPIRED = "expired"


class FollowUpChannel(str, Enum):
    """Canal de follow-up."""

    EMAIL = "email"
    TEAMS = "teams"
    BRING_TO_MEETING = "bring_to_meeting"


class FollowUpStatus(str, Enum):
    """Status de um follow-up."""

    SUGGESTED = "suggested"
    SENT = "sent"
    DISMISSED = "dismissed"
    SNOOZED = "snoozed"


class EvidenceRole(str, Enum):
    """Papel da evidência vinculada à tarefa."""

    ORIGIN = "origin"
    UPDATE = "update"
    COMPLETION_SIGNAL = "completion_signal"
    CONTEXT = "context"
    MEETING_AGENDA = "meeting_agenda"


class StakeholderRole(str, Enum):
    """Papel do stakeholder em relação à tarefa."""

    REQUESTER = "requester"
    ASSIGNEE = "assignee"
    INFORMED = "informed"


class InteractionType(str, Enum):
    """Tipo de touchpoint registrado no ledger de interações RF-G.11."""

    EMAIL_IN = "email_in"
    EMAIL_OUT = "email_out"
    CHAT = "chat"
    MEETING_HELD = "meeting_held"
    NUDGE_SENT = "nudge_sent"


class CalendarSensitivity(str, Enum):
    """Sensibilidade de evento de calendário — RF-F.3."""

    NORMAL = "normal"
    PERSONAL = "personal"
    PRIVATE = "private"
    CONFIDENTIAL = "confidential"


class ProcessingStatus(str, Enum):
    """Status de processamento de um SourceItem."""

    PENDING = "pending"
    FILTERED = "filtered"
    EXTRACTED = "extracted"
    CORRELATED = "correlated"
    FAILED = "failed"


class DemandOrigin(str, Enum):
    """Origem da demanda — RF-C.2 / Catálogo de métricas."""

    INTERNAL_AREA = "internal_area"
    PEER_AREA = "peer_area"
    MANAGEMENT = "management"
    EXTERNAL = "external"
    SELF = "self"


class MeetingClass(str, Enum):
    """Classificação de reunião — RF-F.9."""

    ONE_ON_ONE = "1:1"
    TEAM = "team"
    PROJECT = "project"
    GOVERNANCE = "governance"
    EXTERNAL = "external"
    PERSONAL_BLOCK = "personal_block"


class MilestoneStatus(str, Enum):
    """Status de um marco de projeto."""

    PLANNED = "planned"
    AT_RISK = "at_risk"
    MET = "met"
    MISSED = "missed"
    CANCELLED = "cancelled"


class AreaKind(str, Enum):
    """Tipo de área organizacional — Seção 8 do PRD."""

    OWN_TEAM = "own_team"
    PEER_AREA = "peer_area"
    MANAGEMENT = "management"
    EXTERNAL = "external"
    VENDOR = "vendor"


class ProjectStatus(str, Enum):
    """Status de projeto."""

    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

