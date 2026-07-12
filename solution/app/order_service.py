"""Refactored OrderService - the same business logic, but now testable.

Key changes vs the original:
1. Dependencies injected via __init__ (PaymentClient, EmailClient, Session)
2. `datetime.utcnow` replaced by an injectable `now` callable
3. `compute_total()` extracted as a pure function - no I/O
"""

import logging
import random
import time
from collections.abc import Callable
from datetime import datetime, timedelta, UTC
from decimal import Decimal

from solution.app.clients.email_client import EmailClient
from solution.app.clients.payment_client import (  # noqa: F401
    PaymentClient,
    PaymentError,
)
from sqlalchemy.orm import Session

from app.config import CANCELLATION_WINDOW_HOURS, MAX_ITEMS_PER_ORDER
from app.models.book import Book
from app.models.order import Order, OrderItem, OrderStatus
from app.models.user import User

PROMO_CODES: dict[str, Decimal] = {
    "SAVE10": Decimal("0.10"),
    "SAVE20": Decimal("0.20"),
    "HALFOFF": Decimal("0.50"),
}

log = logging.getLogger(__name__)


def compute_total(
    prices: list[tuple[Decimal, int]],
    promo_code: str | None = None,
) -> Decimal:
    """Pure function - no DB, no I/O, trivially unit-testable."""
    total = sum(price * quantity for price, quantity in prices)
    if promo_code:
        discount = PROMO_CODES.get(promo_code.upper(), Decimal(0))
        total = total * (1 - discount)
    return Decimal(str(total))


class OrderService:
    """Order business logic with all external collaborators injected.

    Persistence, payment and email clients, and the ``now`` clock are passed
    in so the service can be exercised with fakes and a controllable time.
    """

    def __init__(
        self,
        db: Session,
        payment: PaymentClient,
        email: EmailClient,
        now: Callable[[], datetime] = lambda: datetime.now(tz=UTC),
    ) -> None:
        """Store the injected DB session, payment/email clients and clock."""
        self._db = db
        self._payment = payment
        self._email = email
        self._now = now

        self._check_connections()

    def _check_connections(self) -> None:
        """Check that all the connections are responsive."""
        time.sleep(random.randint(1, 10))
        log.info(f"Checking connections at {self._now()}: OK")

    def create_order(
        self,
        user_id: int,
        items: list[dict],
        card_token: str,
        promo_code: str | None = None,
    ) -> Order:
        """Validate, charge, persist and confirm a new order for a user.

        Raises ValueError on unknown/inactive users, too many items, unknown
        books or insufficient stock.
        """
        user = self._db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        if not user.is_active:
            raise ValueError("User account is inactive")

        if len(items) > MAX_ITEMS_PER_ORDER:
            raise ValueError(
                f"Cannot order more than {MAX_ITEMS_PER_ORDER} different items",
            )

        prices: list[tuple[Decimal, int]] = []
        order_items: list[OrderItem] = []

        for item in items:
            book = self._db.query(Book).filter(Book.id == item["book_id"]).first()
            if not book:
                raise ValueError(f"Book {item['book_id']} not found")
            if book.stock < item["quantity"]:
                raise ValueError(
                    f"Insufficient stock for '{book.title}': {book.stock} available",
                )
            prices.append((Decimal(str(book.price)), item["quantity"]))
            order_items.append(
                OrderItem(
                    book_id=book.id,
                    quantity=item["quantity"],
                    unit_price=book.price,
                ),
            )
            book.stock -= item["quantity"]

        total = compute_total(prices, promo_code)
        charge = self._payment.charge(
            total,
            card_token,
            description=f"Order for {user.email}",
        )

        order = Order(
            user_id=user_id,
            status=OrderStatus.CONFIRMED,
            total=total,
            promo_code=promo_code,
            charge_id=charge["id"],
            created_at=self._now(),
        )
        order.items = order_items
        self._db.add(order)
        self._db.commit()
        self._db.refresh(order)

        self._email.send(
            to=user.email,
            subject="Order confirmed",
            body=f"Your order #{order.id} for €{total:.2f} has been confirmed.",
        )
        return order

    def cancel_order(self, order_id: int) -> Order:
        """Refund an order, restore stock and notify the user.

        Raises ValueError if the order is unknown, not cancellable, or past
        the cancellation window.
        """
        order = self._db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise ValueError(f"Order {order_id} not found")
        if order.status != OrderStatus.CONFIRMED:
            raise ValueError(f"Cannot cancel order in status {order.status}")

        deadline = order.created_at + timedelta(hours=CANCELLATION_WINDOW_HOURS)
        if self._now() > deadline:
            raise ValueError("Cancellation window has expired (1 hour after order)")

        self._payment.refund(order.charge_id)

        for item in order.items:
            book = self._db.query(Book).filter(Book.id == item.book_id).first()
            if book:
                book.stock += item.quantity

        order.status = OrderStatus.CANCELLED
        self._db.commit()
        self._db.refresh(order)

        user = self._db.query(User).filter(User.id == order.user_id).first()
        self._email.send(
            to=user.email,
            subject="Order cancelled",
            body=f"Your order #{order.id} has been cancelled and refunded.",
        )
        return order
