from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.order import Order
from app.schemas.order import OrderCreate, OrderResponse
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/", response_model=OrderResponse, status_code=201)
def create_order(payload: OrderCreate, card_token: str, db: Session = Depends(get_db)):
    service = OrderService()  # new instance per request, no way to inject a fake
    try:
        order = service.create_order(
            user_id=payload.user_id,
            items=[i.model_dump() for i in payload.items],
            card_token=card_token,
            promo_code=payload.promo_code,
        )
        return order
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(order_id: int):
    service = OrderService()
    try:
        return service.cancel_order(order_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
