from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ticket import Category

def list_categories(db: Session) -> Sequence[Category]:
    return db.scalars(select(Category).order_by(Category.name)).all()
