from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TicketPriority, TicketStatus
from app.schemas.user import UserRead

class TicketCreate(BaseModel):
    title: str = Field(min_length=5, max_length=200)
    description: str = Field(min_length=10)
    priority: TicketPriority = Field(default=TicketPriority.medium)
    category_id: int

class TicketUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=5, max_length=200)
    description: str | None = Field(default=None, min_length=10)
    category_id: int | None = None

class TicketStaffUpdate(BaseModel):
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    assigned_to_id: int | None = None

class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    category_id: int | None
    created_by: UserRead
    assigned_to: UserRead | None
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None

class TicketPage(BaseModel):
    items: list[TicketRead]
    total: int
    page: int
    page_size: int