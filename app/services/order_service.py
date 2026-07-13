import random
import time
from datetime import datetime, timedelta
from decimal import Decimal

from app.clients.email_client import EmailClient
from app.clients.payment_client import PaymentClient
from app.config import CANCELLATION_WINDOW_HOURS, MAX_ITEMS_PER_ORDER
from app.database import SessionLocal
from app.models.book import Book
from app.models.order import Order, OrderItem, OrderStatus
from app.models.user import User

PROMO_CODES: dict[str, Decimal] = {
    "SAVE10": Decimal("0.10"),
    "SAVE20": Decimal("0.20"),
    "HALFOFF": Decimal("0.50"),
}


class OrderService:
    def __init__(self):
        self._payment = PaymentClient()
        self._email = EmailClient()

        self._check_connections()

    def _check_connections(self) -> None:
        """Check that all the connections are responsive."""
        time.sleep(random.randint(1, 10))  # NOTE: the sleep is to simulate slowness

    def create_order(
        self,
        user_id: int,
        items: list[dict],
        card_token: str,
        promo_code: str | None = None,
    ) -> Order:
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User {user_id} not found")
            if not user.is_active:
                raise ValueError("User account is inactive")

            if len(items) > MAX_ITEMS_PER_ORDER:
                raise ValueError(
                    f"Cannot order more than {MAX_ITEMS_PER_ORDER} different items"
                )

            total = Decimal("0")
            order_items = []

            for item in items:
                book = db.query(Book).filter(Book.id == item["book_id"]).first()
                if not book:
                    raise ValueError(f"Book {item['book_id']} not found")
                if book.stock < item["quantity"]:
                    raise ValueError(
                        f"Insufficient stock for '{book.title}': {book.stock} available"
                    )

                line_total = Decimal(str(book.price)) * item["quantity"]
                total += line_total
                order_items.append(
                    OrderItem(
                        book_id=book.id,
                        quantity=item["quantity"],
                        unit_price=book.price,
                    )
                )
                book.stock -= item["quantity"]

            if promo_code:
                discount = PROMO_CODES.get(promo_code.upper())
                if not discount:
                    raise ValueError(f"Invalid promo code: {promo_code}")
                total = total * (1 - discount)

            charge = self._payment.charge(
                total, card_token, description=f"Order for {user.email}"
            )

            order = Order(
                user_id=user_id,
                status=OrderStatus.CONFIRMED,
                total=total,
                promo_code=promo_code,
                charge_id=charge["id"],
                created_at=datetime.utcnow(),
            )
            order.items = order_items
            db.add(order)
            db.commit()
            db.refresh(order)

            self._email.send(
                to=user.email,
                subject="Order confirmed",
                body=f"Your order #{order.id} for €{total:.2f} has been confirmed.",
            )

            return order
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def cancel_order(self, order_id: int) -> Order:
        db = SessionLocal()
        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                raise ValueError(f"Order {order_id} not found")
            if order.status != OrderStatus.CONFIRMED:
                raise ValueError(f"Cannot cancel order in status {order.status}")

            deadline = order.created_at + timedelta(hours=CANCELLATION_WINDOW_HOURS)
            if datetime.utcnow() > deadline:
                raise ValueError("Cancellation window has expired (1 hour after order)")

            self._payment.refund(order.charge_id)

            for item in order.items:
                book = db.query(Book).filter(Book.id == item.book_id).first()
                if book:
                    book.stock += item.quantity

            order.status = OrderStatus.CANCELLED
            db.commit()
            db.refresh(order)

            user = db.query(User).filter(User.id == order.user_id).first()
            self._email.send(
                to=user.email,
                subject="Order cancelled",
                body=f"Your order #{order.id} has been cancelled and refunded.",
            )

            return order
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
