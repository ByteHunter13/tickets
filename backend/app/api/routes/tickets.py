from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUser, DbSession, require_roles
from app.models.enums import Role, TicketPriority, TicketStatus
from app.models.user import User
from app.schemas.ticket import TicketCreate, TicketPage, TicketRead, TicketStaffUpdate, TicketUpdate
from app.services import tickets as tickets_service

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketRead, status_code=201)
def create_ticket(data: TicketCreate, db: DbSession, user: CurrentUser):
    return tickets_service.create_ticket(db, creator=user, data=data)


@router.get("", response_model=TicketPage)
def list_tickets(
    db: DbSession,
    user: CurrentUser,
    status: TicketStatus | None = None,
    priority: TicketPriority | None = None,
    assigned_to_id: int | None = None,
    created_by_id: int | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    items, total = tickets_service.list_tickets(
        db,
        viewer=user,
        status=status,
        priority=priority,
        assigned_to_id=assigned_to_id,
        created_by_id=created_by_id,
        page=page,
        page_size=page_size,
    )
    return TicketPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/{ticket_id}", response_model=TicketRead)
def get_ticket(ticket_id: int, db: DbSession, user: CurrentUser):
    return tickets_service.get_ticket_or_404(db, viewer=user, ticket_id=ticket_id)


@router.patch("/{ticket_id}", response_model=TicketRead)
def update_ticket(ticket_id: int, data: TicketUpdate, db: DbSession, user: CurrentUser):
    return tickets_service.update_ticket(db, actor=user, ticket_id=ticket_id, data=data)


@router.patch("/{ticket_id}/staff", response_model=TicketRead)
def update_ticket_staff(
    ticket_id: int,
    data: TicketStaffUpdate,
    db: DbSession,
    agent: Annotated[User, Depends(require_roles(Role.admin, Role.agent))],
):
    return tickets_service.update_ticket_staff(db, actor=agent, ticket_id=ticket_id, data=data)
