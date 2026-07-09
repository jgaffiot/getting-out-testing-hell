from sqlalchemy import Column, Integer, String, Numeric, CheckConstraint
from app.database import Base


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    author = Column(String(255), nullable=False)
    isbn = Column(String(13), unique=True, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    stock = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        CheckConstraint("price > 0", name="ck_books_price_positive"),
        CheckConstraint("stock >= 0", name="ck_books_stock_non_negative"),
    )

    def __repr__(self) -> str:
        return f"<Book id={self.id} title={self.title!r}>"
