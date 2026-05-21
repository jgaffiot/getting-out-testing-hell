"""
Cancellation tests — exercise the 1-hour window with an injected `now`.

Demonstrates the value of treating "what time is it?" as a dependency:
no sleep(3700), no flakiness, every boundary directly testable.
"""
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.config import CANCELLATION_WINDOW_HOURS
from app.models.order import OrderStatus
from solution.order_service import OrderService


ORDER_TIME = datetime(2024, 6, 1, 12, 0, 0)
WINDOW = timedelta(hours=CANCELLATION_WINDOW_HOURS)


def _service_at(db, payment, email, when: datetime) -> OrderService:
    return OrderService(db=db, payment=payment, email=email, now=lambda: when)


@pytest.fixture
def existing_order(db, payment, email, make_user, make_book):
    """A confirmed order created at ORDER_TIME, ready to be cancelled."""
    user = make_user(email="buyer@example.com")
    book = make_book(price=Decimal("20.00"), stock=5)
    svc = _service_at(db, payment, email, ORDER_TIME)
    order = svc.create_order(
        user_id=user.id,
        items=[{"book_id": book.id, "quantity": 2}],
        card_token="tok_visa",
    )
    # Reset the email recorder so cancellation assertions are not polluted
    # by the confirmation email.
    email.sent.clear()
    return order


class TestCancellationWindow:
    def test_just_before_deadline_succeeds(self, db, payment, email, existing_order):
        just_before = ORDER_TIME + WINDOW - timedelta(seconds=1)
        svc = _service_at(db, payment, email, just_before)

        cancelled = svc.cancel_order(existing_order.id)

        assert cancelled.status == OrderStatus.CANCELLED

    def test_exactly_at_deadline_succeeds(self, db, payment, email, existing_order):
        # The implementation uses `now > deadline` (strict), so equality is allowed.
        svc = _service_at(db, payment, email, ORDER_TIME + WINDOW)

        cancelled = svc.cancel_order(existing_order.id)

        assert cancelled.status == OrderStatus.CANCELLED

    def test_one_second_after_deadline_raises(self, db, payment, email, existing_order):
        just_after = ORDER_TIME + WINDOW + timedelta(seconds=1)
        svc = _service_at(db, payment, email, just_after)

        with pytest.raises(ValueError, match="expired"):
            svc.cancel_order(existing_order.id)

    def test_hours_after_deadline_raises(self, db, payment, email, existing_order):
        much_later = ORDER_TIME + timedelta(hours=24)
        svc = _service_at(db, payment, email, much_later)

        with pytest.raises(ValueError, match="expired"):
            svc.cancel_order(existing_order.id)


class TestCancellationSideEffects:
    def test_refunds_the_original_charge(self, db, payment, email, existing_order):
        svc = _service_at(db, payment, email, ORDER_TIME + timedelta(minutes=5))

        svc.cancel_order(existing_order.id)

        assert payment.charges[0].refunded is True

    def test_restores_stock_for_every_item(self, db, payment, email, make_user, make_book):
        user = make_user()
        book_a = make_book(title="A", price=Decimal("10.00"), stock=10)
        book_b = make_book(title="B", price=Decimal("15.00"), stock=8)

        svc = _service_at(db, payment, email, ORDER_TIME)
        order = svc.create_order(
            user_id=user.id,
            items=[
                {"book_id": book_a.id, "quantity": 3},
                {"book_id": book_b.id, "quantity": 2},
            ],
            card_token="tok_visa",
        )

        _service_at(db, payment, email, ORDER_TIME + timedelta(minutes=5)).cancel_order(order.id)

        db.refresh(book_a)
        db.refresh(book_b)
        assert book_a.stock == 10
        assert book_b.stock == 8

    def test_sends_cancellation_email(self, db, payment, email, existing_order):
        svc = _service_at(db, payment, email, ORDER_TIME + timedelta(minutes=10))

        svc.cancel_order(existing_order.id)

        assert len(email.sent) == 1
        assert email.last_email.to == "buyer@example.com"
        assert "cancelled" in email.last_email.subject.lower()


class TestCancellationGuards:
    def test_unknown_order_raises(self, db, payment, email):
        svc = _service_at(db, payment, email, ORDER_TIME)
        with pytest.raises(ValueError, match="not found"):
            svc.cancel_order(order_id=9_999_999)

    def test_already_cancelled_order_cannot_be_cancelled_again(
        self, db, payment, email, existing_order
    ):
        svc = _service_at(db, payment, email, ORDER_TIME + timedelta(minutes=5))
        svc.cancel_order(existing_order.id)

        with pytest.raises(ValueError, match="Cannot cancel"):
            svc.cancel_order(existing_order.id)
