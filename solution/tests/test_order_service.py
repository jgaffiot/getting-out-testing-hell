"""Unit tests for OrderService.create_order and the pure compute_total function.

No HTTP, no real DB connection management - only the service layer with
fakes injected. Cancellation tests live in test_cancellation.py.
"""

from decimal import Decimal

import pytest
from app.models.order import OrderStatus
from solution.app.fakes import FakeEmailClient, FakePaymentClient
from solution.app.order_service import OrderService, compute_total

# --- Pure function tests ---


class TestComputeTotal:
    """Unit tests for the pure compute_total function."""

    def test_single_item(self):
        """A single line item totals price times quantity."""
        assert compute_total([(Decimal("10.00"), 3)]) == Decimal("30.00")

    def test_multiple_items(self):
        """Multiple line items are summed."""
        total = compute_total([(Decimal("10.00"), 2), (Decimal("5.00"), 4)])
        assert total == Decimal("40.00")

    def test_promo_save10(self):
        """The SAVE10 promo applies a 10% discount."""
        total = compute_total([(Decimal("100.00"), 1)], promo_code="SAVE10")
        assert total == Decimal("90.0")

    def test_promo_halfoff(self):
        """The HALFOFF promo applies a 50% discount."""
        total = compute_total([(Decimal("50.00"), 2)], promo_code="HALFOFF")
        assert total == Decimal("50.0")

    def test_unknown_promo_code_ignored(self):
        """An unrecognised promo code leaves the total unchanged."""
        total = compute_total([(Decimal("100.00"), 1)], promo_code="NOTREAL")
        assert total == Decimal("100.00")

    def test_promo_code_case_insensitive(self):
        """Promo codes are matched case-insensitively."""
        assert compute_total(
            [(Decimal("100.00"), 1)],
            promo_code="save10",
        ) == compute_total([(Decimal("100.00"), 1)], promo_code="SAVE10")

    def test_empty_items(self):
        """An empty item list totals zero."""
        assert compute_total([]) == Decimal(0)


# Service tests with fakes (shared fixtures live in conftest.py)


class TestCreateOrder:
    """Service-level tests for OrderService.create_order with fakes."""

    def test_creates_confirmed_order(self, service, make_user, make_book):
        """A valid request creates a confirmed order with the right total."""
        user = make_user()
        book = make_book(price=Decimal("20.00"), stock=5)

        order = service.create_order(
            user_id=user.id,
            items=[{"book_id": book.id, "quantity": 2}],
            card_token="tok_visa",
        )

        assert order.status == OrderStatus.CONFIRMED
        assert order.total == Decimal("40.00")

    def test_decreases_stock(self, service, make_user, make_book, db):
        """Creating an order decreases the ordered book's stock."""
        user = make_user()
        book = make_book(stock=5)

        service.create_order(
            user_id=user.id,
            items=[{"book_id": book.id, "quantity": 3}],
            card_token="tok_visa",
        )

        db.refresh(book)
        assert book.stock == 2

    def test_applies_promo_code(self, service, make_user, make_book):
        """A recognised promo code is applied to the order total."""
        user = make_user()
        book = make_book(price=Decimal("100.00"), stock=1)

        order = service.create_order(
            user_id=user.id,
            items=[{"book_id": book.id, "quantity": 1}],
            card_token="tok_visa",
            promo_code="SAVE10",
        )

        assert order.total == Decimal("90.0")

    def test_sends_confirmation_email(self, service, make_user, make_book, email):
        """Creating an order sends one confirmation email to the buyer."""
        user = make_user(email="buyer@example.com")
        book = make_book()

        service.create_order(
            user_id=user.id,
            items=[{"book_id": book.id, "quantity": 1}],
            card_token="tok_visa",
        )

        assert len(email.sent) == 1
        assert email.last_email.to == "buyer@example.com"
        assert "confirmed" in email.last_email.subject.lower()

    def test_charges_payment(self, service, make_user, make_book, payment):
        """Creating an order charges the payment client for the order total."""
        user = make_user()
        book = make_book(price=Decimal("25.00"), stock=2)

        service.create_order(
            user_id=user.id,
            items=[{"book_id": book.id, "quantity": 2}],
            card_token="tok_visa",
        )

        assert payment.last_charge is not None
        assert payment.last_charge.amount == 5000  # €50.00 in cents

    def test_raises_for_unknown_user(self, service):
        """Ordering for an unknown user raises a 'not found' error."""
        with pytest.raises(ValueError, match="not found"):
            service.create_order(user_id=9999, items=[], card_token="tok_visa")

    def test_raises_for_inactive_user(self, service, make_user, make_book):
        """Ordering for an inactive user raises an 'inactive' error."""
        user = make_user(is_active=False)
        book = make_book()
        with pytest.raises(ValueError, match="inactive"):
            service.create_order(
                user_id=user.id,
                items=[{"book_id": book.id, "quantity": 1}],
                card_token="tok_visa",
            )

    def test_raises_when_insufficient_stock(self, service, make_user, make_book):
        """Ordering more copies than are in stock raises an error."""
        user = make_user()
        book = make_book(stock=1)
        with pytest.raises(ValueError, match="Insufficient stock"):
            service.create_order(
                user_id=user.id,
                items=[{"book_id": book.id, "quantity": 5}],
                card_token="tok_visa",
            )

    def test_payment_failure_rolls_back_stock(self, db, make_user, make_book):
        """A declined payment leaves the book's stock unchanged."""
        user = make_user()
        book = make_book(stock=3)
        failing_payment = FakePaymentClient(fail_on_token="tok_decline")
        svc = OrderService(db=db, payment=failing_payment, email=FakeEmailClient())

        with pytest.raises(ValueError):  # noqa: PT011
            svc.create_order(
                user_id=user.id,
                items=[{"book_id": book.id, "quantity": 2}],
                card_token="tok_decline",
            )

        db.refresh(book)
        assert book.stock == 3  # stock was not reduced
