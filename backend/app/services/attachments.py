from collections.abc import Sequence

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.attachment import Attachment
from app.models.enums import Role, TicketEventType
from app.models.user import User
from app.services import files as files_service
from app.services.tickets import get_ticket_or_404, log_event


def create_attachment(
    db: Session, *, actor: User, ticket_id: int, file: UploadFile
) -> Attachment:
    ticket = get_ticket_or_404(db, viewer=actor, ticket_id=ticket_id)

    if not files_service.is_allowed_content_type(file.content_type):
        raise HTTPException(status_code=415, detail="Tipo de archivo no permitido")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    data = file.file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail="El archivo excede el tamaño máximo")

    stored_name = files_service.save_file(data, file.content_type)

    try:
        attachment = Attachment(
            ticket_id=ticket.id,
            uploaded_by_id=actor.id,
            filename=file.filename or stored_name,
            stored_name=stored_name,
            content_type=file.content_type,
            size_bytes=len(data),
        )
        db.add(attachment)
        log_event(db, ticket=ticket, actor=actor, event_type=TicketEventType.attachment_added)
        db.commit()
    except Exception:
        db.rollback()
        files_service.delete_file(stored_name)
        raise

    db.refresh(attachment)
    return attachment


def list_attachments(db: Session, *, viewer: User, ticket_id: int) -> Sequence[Attachment]:
    ticket = get_ticket_or_404(db, viewer=viewer, ticket_id=ticket_id)

    query = (
        select(Attachment)
        .where(Attachment.ticket_id == ticket.id)
        .order_by(Attachment.created_at)
    )
    return db.scalars(query).all()


def get_attachment_or_404(db: Session, *, viewer: User, attachment_id: int) -> Attachment:
    attachment = db.get(Attachment, attachment_id)
    if attachment is None:
        raise HTTPException(status_code=404, detail="Adjunto no encontrado")

    # Reutiliza el control de acceso del ticket: si el viewer no puede ver
    # el ticket, tampoco debe poder ver (ni saber que existe) el adjunto.
    get_ticket_or_404(db, viewer=viewer, ticket_id=attachment.ticket_id)

    return attachment


def delete_attachment(db: Session, *, actor: User, attachment_id: int) -> None:
    attachment = get_attachment_or_404(db, viewer=actor, attachment_id=attachment_id)

    if attachment.uploaded_by_id != actor.id and actor.role != Role.admin:
        raise HTTPException(
            status_code=403, detail="No tienes permisos para borrar este adjunto"
        )

    stored_name = attachment.stored_name
    db.delete(attachment)
    db.commit()
    files_service.delete_file(stored_name)
