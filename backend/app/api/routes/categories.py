from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.category import CategoryRead
from app.services import categories as categories_service

router = APIRouter(prefix="/categories", tags=["categories"])

@router.get("", response_model=list[CategoryRead])
def list_categories(db: DbSession, user: CurrentUser):
    return categories_service.list_categories(db)
