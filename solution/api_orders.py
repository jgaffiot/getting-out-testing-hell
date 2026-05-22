"""
Refactored orders router — uses FastAPI Depends() to inject OrderService.

This is the "minimal refactor" of app/api/orders.py: every external
collaborator (DB session, payment client, email client) is wired through
Depends, so tests can swap them via dependency_overrides.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.clients.email_client import EmailClient
from app.clients.payment_client import PaymentClient
from app.database import get_db
from app.models.order import Order
from app.schemas.order import OrderCreate, OrderResponse
from solution.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])


def get_payment_client() -> PaymentClient:
    return PaymentClient()


def get_email_client() -> EmailClient:
    return EmailClient()


def get_order_service(
    db: Session = Depends(get_db),
    payment: PaymentClient = Depends(get_payment_client),
    email: EmailClient = Depends(get_email_client),
) -> OrderService:
    return OrderService(db=db, payment=payment, email=email)


@router.post("/", response_model=OrderResponse, status_code=201)
def create_order(
    payload: OrderCreate,
    card_token: str,
    service: OrderService = Depends(get_order_service),
):
    try:
        return service.create_order(
            user_id=payload.user_id,
            items=[i.model_dump() for i in payload.items],
            card_token=card_token,
            promo_code=payload.promo_code,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(
    order_id: int,
    service: OrderService = Depends(get_order_service),
):
    try:
        return service.cancel_order(order_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
