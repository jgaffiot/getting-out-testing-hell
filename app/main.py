from fastapi import FastAPI
from app.api import books, orders, users

app = FastAPI(title="Bookstore API", version="0.1.0")

app.include_router(books.router)
app.include_router(users.router)
app.include_router(orders.router)


@app.get("/health")
def health():
    return {"status": "ok"}
