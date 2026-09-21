from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import DbSession, require_roles
from app.models.enums import Role
from app.models.user import User
from app.schemas.user import UserActiveUpdate, UserRead, UserRoleUpdate
from app.services import users as users_service

router = APIRouter(prefix="/users", tags=["users"])

@router.get(
    "",
    response_model=list[UserRead],
    dependencies=[Depends(require_roles(Role.admin, Role.agent))],
)
def list_users(db: DbSession):
    return users_service.list_users(db)

@router.patch("/{user_id}/role", response_model=UserRead)
def update_user_role(
    user_id: int,
    data: UserRoleUpdate,
    db: DbSession,
    admin: Annotated[User, Depends(require_roles(Role.admin))],
):
    return users_service.update_role(db, actor=admin, user_id=user_id, role=data.role)

@router.patch("/{user_id}/active", response_model=UserRead)
def update_user_active(
    user_id: int,
    data: UserActiveUpdate,
    db: DbSession,
    admin: Annotated[User, Depends(require_roles(Role.admin))],
):
    return users_service.update_active(
        db, actor=admin, user_id=user_id, is_active=data.is_active
    )
