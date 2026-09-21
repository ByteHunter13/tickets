import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.db.session import get_db
from app.main import app
from app.models.enums import Role
from app.models.user import User

# El esquema ya debe existir vía `alembic upgrade head` (ver CLAUDE.md).
# Las pruebas no crean ni borran tablas: corren contra el esquema migrado,
# cada una dentro de una transacción que se revierte al terminar.
engine = create_engine(settings.database_url)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(
        bind=connection, join_transaction_mode="create_savepoint"
    )

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def make_user(db_session):
    counter = {"n": 0}

    def _make_user(*, role: Role = Role.user, is_active: bool = True) -> User:
        counter["n"] += 1
        user = User(
            email=f"user{counter['n']}@test.com",
            full_name=f"Test User {counter['n']}",
            hashed_password=hash_password("password123"),
            role=role,
            is_active=is_active,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _make_user

@pytest.fixture
def auth_header():
    def _auth_header(user: User) -> dict[str, str]:
        token = create_access_token(str(user.id))
        return {"Authorization": f"Bearer {token}"}

    return _auth_header
