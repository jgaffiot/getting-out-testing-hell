"""Cancellation tests - exercise the 1-hour window with an injected `now`.

Demonstrates the value of treating "what time is it?" as a dependency:
no sleep(3700), no flakiness, every boundary directly testable.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from app.config import CANCELLATION_WINDOW_HOURS
from app.models.order import OrderStatus
from solution.app.order_service import OrderService

ORDER_TIME = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)
WINDOW = timedelta(hours=CANCELLATION_WINDOW_HOURS)


def _service_at(db, fake_payment, fake_email, when: datetime) -> OrderService:
    """Build an OrderService whose clock is pinned to ``when``."""
    return OrderService(db=db, payment=fake_payment, email=fake_email, now=lambda: when)


@pytest.fixture
def existing_order(db, fake_payment, fake_email, make_user, make_book):
    """Return a confirmed order created at ORDER_TIME, ready to be cancelled."""
    user = make_user(email="buyer@example.com")
    book = make_book(price=Decimal("20.00"), stock=5)
    svc = _service_at(db, fake_payment, fake_email, ORDER_TIME)
    order = svc.create_order(
        user_id=user.id,
        items=[{"book_id": book.id, "quantity": 2}],
        card_token="tok_visa",
    )
    # Reset the email recorder so cancellation assertions are not polluted
    # by the confirmation email.
    fake_email.sent.clear()
    return order


class TestCancellationWindow:
    """Cancellation is allowed up to the deadline and rejected after it."""

    def test_just_before_deadline_succeeds(
        self,
        db,
        fake_payment,
        fake_email,
        existing_order,
    ):
        """Cancelling one second before the deadline succeeds."""
        just_before = ORDER_TIME + WINDOW - timedelta(seconds=1)
        svc = _service_at(db, fake_payment, fake_email, just_before)

        cancelled = svc.cancel_order(existing_order.id)

        assert cancelled.status == OrderStatus.CANCELLED

    def test_exactly_at_deadline_succeeds(
        self,
        db,
        fake_payment,
        fake_email,
        existing_order,
    ):
        """Cancelling exactly at the deadline succeeds (strict comparison)."""
        # The implementation uses `now > deadline` (strict), so equality is allowed.
        svc = _service_at(db, fake_payment, fake_email, ORDER_TIME + WINDOW)

        cancelled = svc.cancel_order(existing_order.id)

        assert cancelled.status == OrderStatus.CANCELLED

    def test_one_second_after_deadline_raises(
        self,
        db,
        fake_payment,
        fake_email,
        existing_order,
    ):
        """Cancelling one second after the deadline raises an expiry error."""
        just_after = ORDER_TIME + WINDOW + timedelta(seconds=1)
        svc = _service_at(db, fake_payment, fake_email, just_after)

        with pytest.raises(ValueError, match="expired"):
            svc.cancel_order(existing_order.id)

    def test_hours_after_deadline_raises(
        self,
        db,
        fake_payment,
        fake_email,
        existing_order,
    ):
        """Cancelling many hours after the deadline raises an expiry error."""
        much_later = ORDER_TIME + timedelta(hours=24)
        svc = _service_at(db, fake_payment, fake_email, much_later)

        with pytest.raises(ValueError, match="expired"):
            svc.cancel_order(existing_order.id)


class TestCancellationSideEffects:
    """Cancelling an order refunds, restores stock and notifies the buyer."""

    def test_refunds_the_original_charge(
        self,
        db,
        fake_payment,
        fake_email,
        existing_order,
    ):
        """Cancelling refunds the charge made when the order was created."""
        svc = _service_at(
            db,
            fake_payment,
            fake_email,
            ORDER_TIME + timedelta(minutes=5),
        )

        svc.cancel_order(existing_order.id)

        assert fake_payment.charges[0].refunded is True

    def test_restores_stock_for_every_item(
        self,
        db,
        fake_payment,
        fake_email,
        make_user,
        make_book,
    ):
        """Cancelling restores stock for every item in the order."""
        user = make_user()
        book_a = make_book(title="A", price=Decimal("10.00"), stock=10)
        book_b = make_book(title="B", price=Decimal("15.00"), stock=8)

        svc = _service_at(db, fake_payment, fake_email, ORDER_TIME)
        order = svc.create_order(
            user_id=user.id,
            items=[
                {"book_id": book_a.id, "quantity": 3},
                {"book_id": book_b.id, "quantity": 2},
            ],
            card_token="tok_visa",
        )

        _service_at(
            db,
            fake_payment,
            fake_email,
            ORDER_TIME + timedelta(minutes=5),
        ).cancel_order(
            order.id,
        )

        db.refresh(book_a)
        db.refresh(book_b)
        assert book_a.stock == 10
        assert book_b.stock == 8

    def test_sends_cancellation_email(
        self,
        db,
        fake_payment,
        fake_email,
        existing_order,
    ):
        """Cancelling sends a single cancellation email to the buyer."""
        svc = _service_at(
            db,
            fake_payment,
            fake_email,
            ORDER_TIME + timedelta(minutes=10),
        )

        svc.cancel_order(existing_order.id)

        assert len(fake_email.sent) == 1
        assert fake_email.last_email.to == "buyer@example.com"
        assert "cancelled" in fake_email.last_email.subject.lower()


class TestCancellationGuards:
    """Cancellation rejects unknown and already-cancelled orders."""

    def test_unknown_order_raises(self, db, fake_payment, fake_email):
        """Cancelling an unknown order raises a 'not found' error."""
        svc = _service_at(db, fake_payment, fake_email, ORDER_TIME)
        with pytest.raises(ValueError, match="not found"):
            svc.cancel_order(order_id=9_999_999)

    def test_already_cancelled_order_cannot_be_cancelled_again(
        self,
        db,
        fake_payment,
        fake_email,
        existing_order,
    ):
        """Cancelling an already-cancelled order raises a 'Cannot cancel' error."""
        svc = _service_at(
            db,
            fake_payment,
            fake_email,
            ORDER_TIME + timedelta(minutes=5),
        )
        svc.cancel_order(existing_order.id)

        with pytest.raises(ValueError, match="Cannot cancel"):
            svc.cancel_order(existing_order.id)
