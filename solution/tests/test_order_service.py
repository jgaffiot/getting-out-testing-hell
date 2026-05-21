"""
Unit tests for OrderService.create_order and the pure compute_total function.

No HTTP, no real DB connection management — only the service layer with
fakes injected. Cancellation tests live in test_cancellation.py.
"""
from decimal import Decimal

import pytest

from app.models.order import OrderStatus
from solution.fakes import FakeEmailClient, FakePaymentClient
from solution.order_service import OrderService, compute_total


# --- Pure function tests ---

class TestComputeTotal:
    def test_single_item(self):
        assert compute_total([(Decimal("10.00"), 3)]) == Decimal("30.00")

    def test_multiple_items(self):
        total = compute_total([(Decimal("10.00"), 2), (Decimal("5.00"), 4)])
        assert total == Decimal("40.00")

    def test_promo_save10(self):
        total = compute_total([(Decimal("100.00"), 1)], promo_code="SAVE10")
        assert total == Decimal("90.0")

    def test_promo_halfoff(self):
        total = compute_total([(Decimal("50.00"), 2)], promo_code="HALFOFF")
        assert total == Decimal("50.0")

    def test_unknown_promo_code_ignored(self):
        total = compute_total([(Decimal("100.00"), 1)], promo_code="NOTREAL")
        assert total == Decimal("100.00")

    def test_promo_code_case_insensitive(self):
        assert compute_total([(Decimal("100.00"), 1)], promo_code="save10") == \
               compute_total([(Decimal("100.00"), 1)], promo_code="SAVE10")

    def test_empty_items(self):
        assert compute_total([]) == Decimal("0")


# --- Service tests with fakes (shared payment / email / service fixtures live in conftest.py) ---

class TestCreateOrder:
    def test_creates_confirmed_order(self, service, make_user, make_book):
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
        with pytest.raises(ValueError, match="not found"):
            service.create_order(user_id=9999, items=[], card_token="tok_visa")

    def test_raises_for_inactive_user(self, service, make_user, make_book):
        user = make_user(is_active=False)
        book = make_book()
        with pytest.raises(ValueError, match="inactive"):
            service.create_order(
                user_id=user.id,
                items=[{"book_id": book.id, "quantity": 1}],
                card_token="tok_visa",
            )

    def test_raises_when_insufficient_stock(self, service, make_user, make_book):
        user = make_user()
        book = make_book(stock=1)
        with pytest.raises(ValueError, match="Insufficient stock"):
            service.create_order(
                user_id=user.id,
                items=[{"book_id": book.id, "quantity": 5}],
                card_token="tok_visa",
            )

    def test_payment_failure_rolls_back_stock(self, db, make_user, make_book):
        user = make_user()
        book = make_book(stock=3)
        failing_payment = FakePaymentClient(fail_on_token="tok_decline")
        svc = OrderService(db=db, payment=failing_payment, email=FakeEmailClient())

        with pytest.raises(Exception):
            svc.create_order(
                user_id=user.id,
                items=[{"book_id": book.id, "quantity": 2}],
                card_token="tok_decline",
            )

        db.refresh(book)
        assert book.stock == 3  # stock was not reduced
