from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import TicketEventType
from app.schemas.user import UserRead

class TicketEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor: UserRead
    event_type: TicketEventType
    old_value: str | None
    new_value: str | None
    created_at: datetime
