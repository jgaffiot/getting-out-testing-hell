from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel
from app.models.order import OrderStatus


class OrderItemRequest(BaseModel):
    book_id: int
    quantity: int


class OrderCreate(BaseModel):
    user_id: int
    items: list[OrderItemRequest]
    promo_code: str | None = None


class OrderItemResponse(BaseModel):
    book_id: int
    quantity: int
    unit_price: Decimal

    # For compatibility with the ORM
    # See https://pydantic.dev/docs/validation/latest/concepts/models/#arbitrary-class-instances
    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    id: int
    user_id: int
    status: OrderStatus
    total: Decimal
    promo_code: str | None
    charge_id: str | None
    created_at: datetime
    items: list[OrderItemResponse]

    model_config = {"from_attributes": True}
