from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser, DbSession
from app.services import attachments as attachments_service
from app.services import files as files_service

router = APIRouter(prefix="/attachments", tags=["attachments"])


@router.get("/{attachment_id}/download")
def download_attachment(attachment_id: int, db: DbSession, user: CurrentUser):
    attachment = attachments_service.get_attachment_or_404(
        db, viewer=user, attachment_id=attachment_id
    )

    file_path = files_service.get_file_path(attachment.stored_name)
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Adjunto no encontrado")

    filename = files_service.sanitize_filename(attachment.filename)
    return FileResponse(path=file_path, media_type=attachment.content_type, filename=filename)


@router.delete("/{attachment_id}", status_code=204)
def delete_attachment(attachment_id: int, db: DbSession, user: CurrentUser):
    attachments_service.delete_attachment(db, actor=user, attachment_id=attachment_id)
