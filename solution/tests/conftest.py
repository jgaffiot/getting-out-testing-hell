"""
Shared test fixtures.

Scope hierarchy:
- session: one real PostgreSQL container for the whole test run
- function (default): each test gets a rolled-back transaction
"""
import pytest
from decimal import Decimal
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from testcontainers.postgres import PostgresContainer

from app.api import books as books_router_module
from app.api import users as users_router_module
from app.database import Base, get_db
from app.main import app
from app.models.book import Book
from app.models.user import User
from solution.api_orders import (
    get_email_client,
    get_payment_client,
    router as orders_router,
)
from solution.fakes import FakeEmailClient, FakePaymentClient
from solution.order_service import OrderService


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


# --- Fakes shared by service-level and API-level tests ---

@pytest.fixture
def payment():
    return FakePaymentClient()


@pytest.fixture
def email():
    return FakeEmailClient()


@pytest.fixture
def service(db, payment, email):
    return OrderService(db=db, payment=payment, email=email)


# --- API client wired to the refactored orders router + fakes ---

@pytest.fixture
def orders_api_client(db, payment, email):
    """
    A TestClient built around the *refactored* orders router (Depends-based
    injection), so payment + email are real fakes and the DB is the
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
