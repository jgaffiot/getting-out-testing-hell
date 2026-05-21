"""
Shared test fixtures.

Scope hierarchy:
- session: one real PostgreSQL container for the whole test run
- function (default): each test gets a rolled-back transaction
"""
import pytest
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from testcontainers.postgres import PostgresContainer

from app.database import Base, get_db
from app.main import app
from app.models.book import Book
from app.models.user import User


@pytest.fixture(scope="session")
def pg_container():
    with PostgresContainer("postgres:16") as pg:
        yield pg


@pytest.fixture(scope="session")
def db_engine(pg_container):
    engine = create_engine(pg_container.get_connection_url())
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db(db_engine):
    """Each test gets a transaction that is rolled back on teardown."""
    connection = db_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def api_client(db):
    """FastAPI TestClient with the test DB session injected."""
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


# --- Data factories ---

@pytest.fixture
def make_book(db):
    def _make(title="Test Book", author="Author", price=Decimal("20.00"), stock=10, isbn=None):
        book = Book(title=title, author=author, price=price, stock=stock, isbn=isbn)
        db.add(book)
        db.flush()
        return book
    return _make


@pytest.fixture
def make_user(db):
    def _make(email="user@example.com", name="Test User", is_active=True):
        user = User(email=email, name=name, is_active=is_active)
        db.add(user)
        db.flush()
        return user
    return _make
