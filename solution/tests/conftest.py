"""Shared test fixtures.

Scope hierarchy:
- session: one real PostgreSQL container for the whole test run
- function (default): each test gets a rolled-back transaction
"""

from decimal import Decimal

import pytest
from app.api import books as books_router_module
from app.api import users as users_router_module
from app.database import Base, get_db
from app.main import app
from app.models.book import Book
from app.models.user import User
from fastapi import FastAPI
from fastapi.testclient import TestClient
from solution.app.api_orders import (
    get_email_client,
    get_payment_client,
)
from solution.app.api_orders import (
    router as orders_router,
)
from solution.app.order_service import OrderService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer

from .fakes import FakeEmailClient, FakePaymentClient


@pytest.fixture(scope="session")
def pg_container():
    """Start one PostgreSQL container shared by the whole test session."""
    with PostgresContainer("postgres:16") as pg:
        yield pg


@pytest.fixture(scope="session")
def db_engine(pg_container):
    """Create the schema on the container and yield a SQLAlchemy engine."""
    engine = create_engine(pg_container.get_connection_url())
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db(db_engine):
    """Each test gets a transaction that is rolled back on teardown."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()

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


# --- Fakes shared by service-level and API-level tests ---


@pytest.fixture
def fake_payment():
    """Provide a fresh in-memory fake payment client."""
    return FakePaymentClient()


@pytest.fixture
def fake_email():
    """Provide a fresh in-memory fake email client."""
    return FakeEmailClient()


@pytest.fixture
def service(db, fake_payment, fake_email):
    """Build an OrderService wired to the test DB session and fakes."""
    return OrderService(db=db, payment=fake_payment, email=fake_email)


# --- API client wired to the refactored orders router + fakes ---


@pytest.fixture
def orders_api_client(db, payment, email):
    """Return a TestClient built around the *refactored* orders router.

    Depends-based injection, so payment + email are real fakes and the DB is the
    rolled-back transactional session.
    """
    test_app = FastAPI()
    test_app.include_router(books_router_module.router)
    test_app.include_router(users_router_module.router)
    test_app.include_router(orders_router)

    test_app.dependency_overrides[get_db] = lambda: db
    test_app.dependency_overrides[get_payment_client] = lambda: payment
    test_app.dependency_overrides[get_email_client] = lambda: email

    with TestClient(test_app) as client:
        yield client


# --- Data factories ---


@pytest.fixture
def make_book(db):
    """Return a factory that inserts a Book into the test session."""

    def _make(
        title="Test Book",
        author="Author",
        price=Decimal("20.00"),
        stock=10,
        isbn=None,
    ):
        """Create, flush and return a Book with the given attributes."""
        book = Book(title=title, author=author, price=price, stock=stock, isbn=isbn)
        db.add(book)
        db.flush()
        return book

    return _make


@pytest.fixture
def make_user(db):
    """Return a factory that inserts a User into the test session."""

    def _make(email="user@example.com", name="Test User", is_active=True):  # noqa: FBT002
        """Create, flush and return a User with the given attributes."""
        user = User(email=email, name=name, is_active=is_active)
        db.add(user)
        db.flush()
        return user

    return _make
