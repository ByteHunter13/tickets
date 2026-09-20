from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Importamos las configuraciones globales
from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)

# Obtención de la sesión con la base de datos
SessionLocal = sessionmaker(
    bind=engine, 
    autoflush=False, 
    expire_on_commit=False)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

