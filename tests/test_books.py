"""
Tests for the books API.

Run with: pytest tests/test_books.py
Requires a running PostgreSQL instance and the app running on localhost:8000.
"""
import requests

BASE_URL = "http://localhost:8000"

# Global variable shared between tests — tests must run in order!
created_book_id = None


def test_create_book():
    global created_book_id
    response = requests.post(f"{BASE_URL}/books/", json={
        "title": "Clean Code",
        "author": "Robert C. Martin",
        "isbn": "9780132350884",
        "price": 35.99,
        "stock": 10,
    })
    assert response.status_code == 201
    created_book_id = response.json()["id"]


def test_get_book():
    # Depends on test_create_book having run first
    response = requests.get(f"{BASE_URL}/books/{created_book_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Clean Code"


def test_get_book_not_found():
    response = requests.get(f"{BASE_URL}/books/999999")
    assert response.status_code == 404


def test_list_books():
    response = requests.get(f"{BASE_URL}/books/")
    # Only checks it doesn't crash — no assertion on content
    assert response.status_code == 200


def test_update_book():
    # Will crash with TypeError if test_create_book never ran
    response = requests.patch(f"{BASE_URL}/books/{created_book_id}", json={"stock": 5})
    assert response.status_code == 200
    assert response.json()["stock"] == 5


def test_create_book_invalid_price():
    response = requests.post(f"{BASE_URL}/books/", json={
        "title": "Free Book",
        "author": "Nobody",
        "price": -1,
        "stock": 0,
    })
    # Magic number — why 422?
    assert response.status_code == 422


def test_duplicate_isbn():
    # Creates a book that pollutes the DB and is never cleaned up
    requests.post(f"{BASE_URL}/books/", json={
        "title": "Duplicate Test",
        "author": "Test",
        "isbn": "9780132350884",  # same ISBN as created in test_create_book
        "price": 10.0,
        "stock": 1,
    })
    response = requests.post(f"{BASE_URL}/books/", json={
        "title": "Duplicate Test 2",
        "author": "Test",
        "isbn": "9780132350884",
        "price": 10.0,
        "stock": 1,
    })
    assert response.status_code == 409


def test_delete_book():
    # Deletes the book created in test_create_book — order matters!
    response = requests.delete(f"{BASE_URL}/books/{created_book_id}")
    assert response.status_code == 204


def test_get_deleted_book():
    # Depends on test_delete_book having run
    response = requests.get(f"{BASE_URL}/books/{created_book_id}")
    assert response.status_code == 404
