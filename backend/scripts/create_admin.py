import sys
from getpass import getpass

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.enums import Role
from app.models.user import User

def main() -> None:
    email = input("Email del admin: ").strip().lower()
    name = input("Nombre completo: ").strip()
    password = getpass("Contraseña: ")

    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)):
            print("Ese correo ya existe")
            sys.exit(1)
        db.add(
            User(
                email=email,
                full_name=name,
                hashed_password=hash_password(password),
                role=Role.admin
            )
        )
        db.commit()
    print("Admin creado")

if __name__=="__main__":
    main()
