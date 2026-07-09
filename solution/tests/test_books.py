"""Book endpoint tests - clean version.

Every test is independent: no global state, full rollback after each.
"""

from decimal import Decimal

import pytest


def test_create_book(api_client):
    """Posting a valid book returns 201 with the persisted fields."""
    response = api_client.post(
        "/books/",
        json={
            "title": "Working with Legacy Code",
            "author": "Michael Feathers",
            "isbn": "9780131177055",
            "price": "35.99",
            "stock": 10,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Working with Legacy Code"
    assert Decimal(data["price"]) == Decimal("35.99")
    assert data["stock"] == 10


def test_get_book(api_client, make_book):
    """Fetching an existing book returns 200 with its data."""
    book = make_book(title="Pragmatic Programmer", price=Decimal("29.99"))
    response = api_client.get(f"/books/{book.id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Pragmatic Programmer"


def test_get_book_not_found(api_client):
    """Fetching a missing book returns 404."""
    response = api_client.get("/books/999999")
    assert response.status_code == 404


def test_list_books_returns_all(api_client, make_book):
    """Listing books returns every created book."""
    make_book(title="Book A")
    make_book(title="Book B")
    response = api_client.get("/books/")
    assert response.status_code == 200
    titles = [b["title"] for b in response.json()]
    assert "Book A" in titles
    assert "Book B" in titles


@pytest.mark.parametrize("price", ["-1", "0", "-0.01"])
def test_create_book_rejects_non_positive_price(api_client, price):
    """Creating a book with a non-positive price returns 422."""
    response = api_client.post(
        "/books/",
        json={
            "title": "X",
            "author": "Y",
            "price": price,
            "stock": 0,
        },
    )
    assert response.status_code == 422


def test_create_book_duplicate_isbn_returns_409(api_client, make_book):
    """Creating a book with an already-used ISBN returns 409."""
    make_book(isbn="9780132350884")
    response = api_client.post(
        "/books/",
        json={
            "title": "Another Book",
            "author": "Someone",
            "isbn": "9780132350884",
            "price": "10.00",
            "stock": 1,
        },
    )
    assert response.status_code == 409


def test_update_book_stock(api_client, make_book):
    """Patching a book's stock returns 200 with the new value."""
    book = make_book(stock=10)
    response = api_client.patch(f"/books/{book.id}", json={"stock": 3})
    assert response.status_code == 200
    assert response.json()["stock"] == 3


def test_delete_book(api_client, make_book):
    """Deleting a book returns 204 and the book then 404s."""
    book = make_book()
    assert api_client.delete(f"/books/{book.id}").status_code == 204
    assert api_client.get(f"/books/{book.id}").status_code == 404
