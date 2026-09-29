from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.user import UserRead

class AttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    content_type: str
    size_bytes: int
    uploaded_by: UserRead
    created_at: datetime
