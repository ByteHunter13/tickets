from collections.abc import Sequence
from datetime import datetime, timezone

from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import Role, TicketEventType, TicketPriority, TicketStatus
from app.models.event import TicketEvent
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.ticket import TicketCreate, TicketStaffUpdate, TicketUpdate
from app.services import notifications
from app.services.users import get_user_or_404


TRACKED_FIELDS_EVENTS = {
    "status": TicketEventType.status_changed,
    "priority": TicketEventType.priority_changed,
    "assigned_to_id": TicketEventType.assignment_changed,
    "category_id": TicketEventType.category_changed,
}


def log_event(
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


def apply_ticket_changes(db: Session, *, ticket: Ticket, changes: dict, actor: User) -> None:
    for field, new_value in changes.items():
        old_value = getattr(ticket, field)
        if old_value == new_value:
            continue
        if field in TRACKED_FIELDS_EVENTS:
            log_event(
                db,
                ticket=ticket,
                actor=actor,
                event_type=TRACKED_FIELDS_EVENTS[field],
                old_value=None if old_value is None else str(old_value),
                new_value=None if new_value is None else str(new_value),
            )
        setattr(ticket, field, new_value)


def create_ticket(
    db: Session, *, creator: User, data: TicketCreate, background: BackgroundTasks
) -> Ticket:
    ticket = Ticket(
        title=data.title,
        description=data.description,
        priority=data.priority,
        category_id=data.category_id,
        created_by_id=creator.id,
    )
    db.add(ticket)
    db.flush()

    log_event(db, ticket=ticket, actor=creator, event_type=TicketEventType.ticket_created)

    db.commit()
    db.refresh(ticket)

    notifications.notify_ticket_created(background, ticket=ticket, creator=creator)

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
    db: Session,
    *,
    actor: User,
    ticket_id: int,
    data: TicketStaffUpdate,
    background: BackgroundTasks,
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

    old_status = ticket.status
    old_assigned_to_id = ticket.assigned_to_id
    new_status = changes.get("status")

    apply_ticket_changes(db, ticket=ticket, changes=changes, actor=actor)

    if new_status is not None and new_status != old_status:
        if new_status == TicketStatus.closed:
            ticket.closed_at = datetime.now(timezone.utc)
        elif old_status == TicketStatus.closed:
            ticket.closed_at = None

    db.commit()
    db.refresh(ticket)

    if ticket.status != old_status:
        notifications.notify_status_changed(background, ticket=ticket)
    if ticket.assigned_to_id != old_assigned_to_id and ticket.assigned_to_id is not None:
        notifications.notify_ticket_assigned(background, ticket=ticket)

    return ticket


def list_ticket_events(db: Session, *, viewer: User, ticket_id: int) -> Sequence[TicketEvent]:
    ticket = get_ticket_or_404(db, viewer=viewer, ticket_id=ticket_id)

    query = (
        select(TicketEvent)
        .where(TicketEvent.ticket_id == ticket.id)
        .order_by(TicketEvent.created_at)
    )
    return db.scalars(query).all()
