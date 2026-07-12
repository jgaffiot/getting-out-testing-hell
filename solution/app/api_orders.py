"""Refactored orders router - uses FastAPI Depends() to inject OrderService.

This is the "minimal refactor" of app/api/orders.py: every external
collaborator (DB session, payment client, email client) is wired through
Depends, so tests can swap them via dependency_overrides.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from solution.app.clients.email_client import EmailClient
from solution.app.clients.payment_client import PaymentClient, PaymentError
from solution.app.order_service import OrderService
from solution.app.settings import Settings, get_settings
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.order import Order
from app.schemas.order import OrderCreate, OrderResponse

router = APIRouter(prefix="/orders", tags=["orders"])


def get_payment_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> PaymentClient:
    """Provide the payment client dependency (overridable in tests)."""
    return PaymentClient(settings)


def get_email_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> EmailClient:
    """Provide the email client dependency (overridable in tests)."""
    return EmailClient(settings)


def get_order_service(
    db: Annotated[Session, Depends(get_db)],
    payment: Annotated[PaymentClient, Depends(get_payment_client)],
    email: Annotated[EmailClient, Depends(get_email_client)],
) -> OrderService:
    """Build an OrderService with its collaborators injected via Depends."""
    return OrderService(db=db, payment=payment, email=email)


@router.post("/", response_model=OrderResponse, status_code=201)
def create_order(
    payload: OrderCreate,
    card_token: str,
    service: Annotated[OrderService, Depends(get_order_service)],
) -> Order:
    """Create and confirm an order, returning 400 on domain validation errors."""
    try:
        return service.create_order(
            user_id=payload.user_id,
            items=[i.model_dump() for i in payload.items],
            card_token=card_token,
            promo_code=payload.promo_code,
        )
    except (PaymentError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Annotated[Session, Depends(get_db)]) -> Order:
    """Return the order with the given id, or 404 if it does not exist."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(
    order_id: int,
    service: Annotated[OrderService, Depends(get_order_service)],
) -> Order:
    """Cancel an order, returning 400 on domain validation errors."""
    try:
        return service.cancel_order(order_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
