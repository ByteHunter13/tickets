from enum import StrEnum

class Role(StrEnum):
    user = "user"
    agent = "agent"
    admin = "admin"

class TicketStatus(StrEnum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"

class TicketPriority(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"

# Tipos de evento del historial del ticket
class TicketEventType(StrEnum):
    ticket_created = "ticket_created"
    status_changed = "status_changed"
    priority_changed = "priority_changed"