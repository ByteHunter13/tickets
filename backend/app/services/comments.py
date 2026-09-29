from collections.abc import Sequence

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.comment import Comment
from app.models.enums import Role, TicketEventType
from app.models.user import User
from app.schemas.comment import CommentCreate
from app.services.tickets import get_ticket_or_404, log_event


def create_comment(db: Session, *, actor: User, ticket_id: int, data: CommentCreate) -> Comment:
    ticket = get_ticket_or_404(db, viewer=actor, ticket_id=ticket_id)

    if data.is_internal and actor.role == Role.user:
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para agregar comentarios internos",
        )

    comment = Comment(
        ticket_id=ticket.id,
        author_id=actor.id,
        body=data.body,
        is_internal=data.is_internal,
    )
    db.add(comment)

    log_event(db, ticket=ticket, actor=actor, event_type=TicketEventType.comment_added)

    db.commit()
    db.refresh(comment)
    return comment


def list_comments(db: Session, *, viewer: User, ticket_id: int) -> Sequence[Comment]:
    ticket = get_ticket_or_404(db, viewer=viewer, ticket_id=ticket_id)

    query = select(Comment).where(Comment.ticket_id == ticket.id).order_by(Comment.created_at)
    if viewer.role == Role.user:
        query = query.where(Comment.is_internal.is_(False))

    return db.scalars(query).all()
