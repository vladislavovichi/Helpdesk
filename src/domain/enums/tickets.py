from enum import StrEnum


class TicketStatus(StrEnum):
    NEW = "new"
    QUEUED = "queued"
    ASSIGNED = "assigned"
    ESCALATED = "escalated"
    CLOSED = "closed"


class TicketPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class TicketMessageSenderType(StrEnum):
    CLIENT = "client"
    OPERATOR = "operator"
    SYSTEM = "system"


class TicketSentiment(StrEnum):
    CALM = "calm"
    FRUSTRATED = "frustrated"
    ESCALATION_RISK = "escalation_risk"


class TicketSignalConfidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TicketAttachmentKind(StrEnum):
    PHOTO = "photo"
    DOCUMENT = "document"
    VOICE = "voice"
    VIDEO = "video"


class TicketEventType(StrEnum):
    CREATED = "created"
    QUEUED = "queued"
    STATUS_CHANGED = "status_changed"
    ASSIGNED = "assigned"
    REASSIGNED = "reassigned"
    AUTO_REASSIGNED = "auto_reassigned"
    MESSAGE_ADDED = "message_added"
    CLIENT_MESSAGE_ADDED = "client_message_added"
    OPERATOR_MESSAGE_ADDED = "operator_message_added"
    CLIENT_MESSAGE_DUPLICATE_COLLAPSED = "client_message_duplicate_collapsed"
    CLIENT_SENTIMENT_FLAGGED = "client_sentiment_flagged"
    TAG_ADDED = "tag_added"
    TAG_REMOVED = "tag_removed"
    ESCALATED = "escalated"
    AUTO_ESCALATED = "auto_escalated"
    SLA_BREACHED_FIRST_RESPONSE = "sla_breached_first_response"
    SLA_BREACHED_RESOLUTION = "sla_breached_resolution"
    CLOSED = "closed"
