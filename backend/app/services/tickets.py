from collections.abc import Sequence
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import Role, TicketEventType, TicketPriority, TicketStatus
from app.models.event import TicketEvent
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.ticket import TicketCreate, TicketStaffUpdate, TicketUpdate
from app.services.users import get_user_or_404


def _log_event(
    db: Session,
    *,
    ticket: Ticket,
    actor: User,
    event_type: TicketEventType,
    old_value: str | None = None,
    new_value: str | None = None,
) -> None:
    db.add(
        TicketEvent(
            ticket_id=ticket.id,
            actor_id=actor.id,
            event_type=event_type,
            old_value=old_value,
            new_value=new_value,
        )
    )


def create_ticket(db: Session, *, creator: User, data: TicketCreate) -> Ticket:
    ticket = Ticket(
        title=data.title,
        description=data.description,
        priority=data.priority,
        category_id=data.category_id,
        created_by_id=creator.id,
    )
    db.add(ticket)
    db.flush()

    _log_event(db, ticket=ticket, actor=creator, event_type=TicketEventType.ticket_created)

    db.commit()
    db.refresh(ticket)
    return ticket


def list_tickets(
    db: Session,
    *,
    viewer: User,
    status: TicketStatus | None = None,
    priority: TicketPriority | None = None,
    assigned_to_id: int | None = None,
    created_by_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[Sequence[Ticket], int]:
    if viewer.role == Role.user:
        created_by_id = viewer.id

    query = select(Ticket)
    count_query = select(func.count()).select_from(Ticket)

    if status is not None:
        query = query.where(Ticket.status == status)
        count_query = count_query.where(Ticket.status == status)
    if priority is not None:
        query = query.where(Ticket.priority == priority)
        count_query = count_query.where(Ticket.priority == priority)
    if assigned_to_id is not None:
        query = query.where(Ticket.assigned_to_id == assigned_to_id)
        count_query = count_query.where(Ticket.assigned_to_id == assigned_to_id)
    if created_by_id is not None:
        query = query.where(Ticket.created_by_id == created_by_id)
        count_query = count_query.where(Ticket.created_by_id == created_by_id)

    total = db.scalar(count_query) or 0

    query = (
        query.order_by(Ticket.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = db.scalars(query).all()

    return items, total


def get_ticket_or_404(db: Session, *, viewer: User, ticket_id: int) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    not_found = HTTPException(status_code=404, detail="Ticket no encontrado")

    if ticket is None:
        raise not_found
    if viewer.role == Role.user and ticket.created_by_id != viewer.id:
        raise not_found

    return ticket


def update_ticket(db: Session, *, actor: User, ticket_id: int, data: TicketUpdate) -> Ticket:
    ticket = get_ticket_or_404(db, viewer=actor, ticket_id=ticket_id)

    if ticket.status != TicketStatus.open:
        raise HTTPException(
            status_code=400,
            detail="Solo puedes editar el ticket mientras está abierto",
        )

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(ticket, field, value)

    db.commit()
    db.refresh(ticket)
    return ticket


def update_ticket_staff(
    db: Session, *, actor: User, ticket_id: int, data: TicketStaffUpdate
) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    changes = data.model_dump(exclude_unset=True)

    if "assigned_to_id" in changes and changes["assigned_to_id"] is not None:
        assignee = get_user_or_404(db, changes["assigned_to_id"])
        if assignee.role not in (Role.agent, Role.admin):
            raise HTTPException(
                status_code=400,
                detail="Solo se puede asignar el ticket a un agent o admin",
            )

    if "status" in changes and changes["status"] != ticket.status:
        old_status = ticket.status
        new_status = changes["status"]
        ticket.status = new_status
        _log_event(
            db,
            ticket=ticket,
            actor=actor,
            event_type=TicketEventType.status_changed,
            old_value=old_status,
            new_value=new_status,
        )
        if new_status == TicketStatus.closed:
            ticket.closed_at = datetime.now(timezone.utc)
        elif old_status == TicketStatus.closed:
            ticket.closed_at = None

    if "priority" in changes and changes["priority"] != ticket.priority:
        old_priority = ticket.priority
        new_priority = changes["priority"]
        ticket.priority = new_priority
        _log_event(
            db,
            ticket=ticket,
            actor=actor,
            event_type=TicketEventType.priority_changed,
            old_value=old_priority,
            new_value=new_priority,
        )

    if "assigned_to_id" in changes and changes["assigned_to_id"] != ticket.assigned_to_id:
        old_assigned = ticket.assigned_to_id
        new_assigned = changes["assigned_to_id"]
        ticket.assigned_to_id = new_assigned
        _log_event(
            db,
            ticket=ticket,
            actor=actor,
            event_type=TicketEventType.assignment_changed,
            old_value=str(old_assigned) if old_assigned is not None else None,
            new_value=str(new_assigned) if new_assigned is not None else None,
        )

    db.commit()
    db.refresh(ticket)
    return ticket
