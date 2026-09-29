import sys

from sqlalchemy import select

import app.db.base  # noqa: F401  # registra todos los modelos antes de que SQLAlchemy configure los mappers
from app.db.session import SessionLocal
from app.models.ticket import Category

def main() -> None:
    category_name = input("Nueva categoría: ").strip().lower()

    with SessionLocal() as db:
        if db.scalar(select(Category).where(Category.name == category_name)):
            print("Esta categoría ya existe")
            sys.exit()
        db.add(
            Category(
                name=category_name
            )
        )
        db.commit()
    print("Categoría agregada")

if __name__=="__main__":
    main()