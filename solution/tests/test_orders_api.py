"""End-to-end tests for the orders API using the refactored router.

These tests drive the real FastAPI app via TestClient, with:
- a real PostgreSQL (Testcontainers) on a per-test transactional session,
- in-process fakes for PaymentClient and EmailClient.

No live server, no live payment endpoint, no live SMTP - but the HTTP
layer, validation, dependency injection and DB schema are all real.
"""

from decimal import Decimal

import pytest
from app.models.order import OrderStatus


@pytest.fixture
def user(make_user):
    """Return an active buyer used across the orders endpoint tests."""
    return make_user(email="buyer@example.com")


@pytest.fixture
def book(make_book):
    """Return a stocked book used across the orders endpoint tests."""
    return make_book(title="Refactoring", price=Decimal("30.00"), stock=10)


class TestCreateOrderEndpoint:
    """End-to-end behaviour of POST /orders/."""

    def test_returns_201_with_confirmed_order(self, orders_api_client, user, book):
        """A valid order request returns 201 with a confirmed order."""
        response = orders_api_client.post(
            "/orders/",
            params={"card_token": "tok_visa"},
            json={
                "user_id": user.id,
                "items": [{"book_id": book.id, "quantity": 2}],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == user.id
        assert data["status"] == OrderStatus.CONFIRMED.value
        assert Decimal(data["total"]) == Decimal("60.00")
        assert data["items"][0]["quantity"] == 2

    def test_charges_the_payment_client(self, orders_api_client, user, book, payment):
        """Creating an order charges the payment client for the right amount."""
        orders_api_client.post(
            "/orders/",
            params={"card_token": "tok_visa"},
            json={
                "user_id": user.id,
                "items": [{"book_id": book.id, "quantity": 1}],
            },
        )

        assert payment.last_charge is not None
        assert payment.last_charge.card_token == "tok_visa"
        assert payment.last_charge.amount == 3000  # €30 in cents

    def test_sends_a_confirmation_email(self, orders_api_client, user, book, email):
        """Creating an order sends one confirmation email to the buyer."""
        orders_api_client.post(
            "/orders/",
            params={"card_token": "tok_visa"},
            json={
                "user_id": user.id,
                "items": [{"book_id": book.id, "quantity": 1}],
            },
        )

        assert len(email.sent) == 1
        assert email.last_email.to == "buyer@example.com"

    def test_decreases_book_stock(self, orders_api_client, user, book, db):
        """Creating an order decreases the ordered book's stock."""
        orders_api_client.post(
            "/orders/",
            params={"card_token": "tok_visa"},
            json={
                "user_id": user.id,
                "items": [{"book_id": book.id, "quantity": 4}],
            },
        )

        db.refresh(book)
        assert book.stock == 6

    def test_applies_promo_code(self, orders_api_client, user, book):
        """A recognised promo code is applied to the order total."""
        response = orders_api_client.post(
            "/orders/",
            params={"card_token": "tok_visa"},
            json={
                "user_id": user.id,
                "items": [{"book_id": book.id, "quantity": 1}],
                "promo_code": "SAVE10",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["promo_code"] == "SAVE10"
        assert Decimal(data["total"]) == Decimal("27.00")  # 30 * 0.9

    def test_unknown_user_returns_400(self, orders_api_client, book):
        """Ordering for an unknown user returns 400 with a 'not found' detail."""
        response = orders_api_client.post(
            "/orders/",
            params={"card_token": "tok_visa"},
            json={
                "user_id": 9_999_999,
                "items": [{"book_id": book.id, "quantity": 1}],
            },
        )

        assert response.status_code == 400
        assert "not found" in response.json()["detail"]

    def test_inactive_user_returns_400(self, orders_api_client, make_user, book):
        """Ordering for an inactive user returns 400 with an 'inactive' detail."""
        inactive = make_user(email="ghost@example.com", is_active=False)
        response = orders_api_client.post(
            "/orders/",
            params={"card_token": "tok_visa"},
            json={
                "user_id": inactive.id,
                "items": [{"book_id": book.id, "quantity": 1}],
            },
        )

        assert response.status_code == 400
        assert "inactive" in response.json()["detail"]

    def test_insufficient_stock_returns_400(self, orders_api_client, user, make_book):
        """Ordering more copies than are in stock returns 400."""
        scarce = make_book(stock=1, price=Decimal("10.00"))
        response = orders_api_client.post(
            "/orders/",
            params={"card_token": "tok_visa"},
            json={
                "user_id": user.id,
                "items": [{"book_id": scarce.id, "quantity": 5}],
            },
        )

        assert response.status_code == 400
        assert "stock" in response.json()["detail"].lower()


class TestGetOrderEndpoint:
    """End-to-end behaviour of GET /orders/{id}."""

    def test_returns_existing_order(self, orders_api_client, user, book):
        """Fetching an existing order returns 200 with its id."""
        created = orders_api_client.post(
            "/orders/",
            params={"card_token": "tok_visa"},
            json={
                "user_id": user.id,
                "items": [{"book_id": book.id, "quantity": 1}],
            },
        ).json()

        response = orders_api_client.get(f"/orders/{created['id']}")

        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    def test_unknown_order_returns_404(self, orders_api_client):
        """Fetching an unknown order returns 404."""
        response = orders_api_client.get("/orders/9999999")
        assert response.status_code == 404


class TestCancelOrderEndpoint:
    """End-to-end behaviour of POST /orders/{id}/cancel."""

    def test_cancels_within_window(self, orders_api_client, user, book, payment):
        """Cancelling within the window returns 200 and refunds the charge."""
        created = orders_api_client.post(
            "/orders/",
            params={"card_token": "tok_visa"},
            json={
                "user_id": user.id,
                "items": [{"book_id": book.id, "quantity": 2}],
            },
        ).json()

        response = orders_api_client.post(f"/orders/{created['id']}/cancel")

        assert response.status_code == 200
        assert response.json()["status"] == OrderStatus.CANCELLED.value
        assert payment.charges[0].refunded is True

    def test_unknown_order_returns_400(self, orders_api_client):
        """Cancelling an unknown order returns 400 (mapped from ValueError)."""
        # The service raises ValueError("Order ... not found"), which the
        # router maps to 400 (same shape as other domain errors).
        response = orders_api_client.post("/orders/9999999/cancel")
        assert response.status_code == 400
