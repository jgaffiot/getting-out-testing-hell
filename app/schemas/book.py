from decimal import Decimal
from pydantic import BaseModel, field_validator


class BookCreate(BaseModel):
    title: str
    author: str
    isbn: str | None = None
    price: Decimal
    stock: int = 0

    @field_validator("price")
    @classmethod
    def price_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("price must be positive")
        return v

    @field_validator("stock")
    @classmethod
    def stock_must_be_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("stock cannot be negative")
        return v


class BookUpdate(BaseModel):
    title: str | None = None
    author: str | None = None
    price: Decimal | None = None
    stock: int | None = None


class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    isbn: str | None
    price: Decimal
    stock: int

    model_config = {"from_attributes": True}
