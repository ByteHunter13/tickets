from collections.abc import Sequence

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import Role
from app.models.user import User

def list_users(db: Session) -> Sequence[User]:
    return db.scalars(select(User).order_by(User.full_name)).all()

def get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user

def update_role(db: Session, *, actor: User, user_id: int, role: Role) -> User:
    if actor.id == user_id and role != Role.admin:
        raise HTTPException(
            status_code=400, detail="No puedes quitarte tu propio rol de admin"
        )

    user = get_user_or_404(db, user_id)
    user.role = role
    db.commit()
    db.refresh(user)
    return user

def update_active(db: Session, *, actor: User, user_id: int, is_active: bool) -> User:
    if actor.id == user_id and not is_active:
        raise HTTPException(
            status_code=400, detail="No puedes desactivar tu propia cuenta"
        )

    user = get_user_or_404(db, user_id)
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    return user
