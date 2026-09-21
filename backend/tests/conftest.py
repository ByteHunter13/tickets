import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.db.session import get_db
from app.main import app
from app.models.enums import Role, TicketPriority, TicketStatus
from app.models.ticket import Category, Ticket
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
def make_category(db_session):
    counter = {"n": 0}

    def _make_category() -> Category:
        counter["n"] += 1
        category = Category(name=f"Category {counter['n']}")
        db_session.add(category)
        db_session.commit()
        db_session.refresh(category)
        return category

    return _make_category

@pytest.fixture
def make_ticket(db_session, make_user, make_category):
    def _make_ticket(
        *,
        created_by: User | None = None,
        status: TicketStatus = TicketStatus.open,
        priority: TicketPriority = TicketPriority.medium,
        assigned_to_id: int | None = None,
        category_id: int | None = None,
    ) -> Ticket:
        creator = created_by or make_user()
        ticket = Ticket(
            title="Test ticket",
            description="Test ticket description",
            status=status,
            priority=priority,
            created_by_id=creator.id,
            assigned_to_id=assigned_to_id,
            category_id=category_id,
        )
        db_session.add(ticket)
        db_session.commit()
        db_session.refresh(ticket)
        return ticket

    return _make_ticket

@pytest.fixture
def auth_header():
    def _auth_header(user: User) -> dict[str, str]:
        token = create_access_token(str(user.id))
        return {"Authorization": f"Bearer {token}"}

    return _auth_header
