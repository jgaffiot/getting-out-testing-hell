"""
Order tests. These are "integration" tests but require:
- A real PostgreSQL at localhost:5432
- The app running at localhost:8000
- A real payment API (or specific env vars)

Many tests will silently skip or lie if the environment isn't set up correctly.
"""

import os
import requests
import psycopg2

BASE_URL = "http://localhost:8000"
DB_DSN = "postgresql://bookstore:bookstore@localhost:5432/bookstore"

# State shared across test file - fragile
_user_id = None
_book_id = None
_order_id = None


def setup_test_data():
    """Called manually from some tests, not others - inconsistent."""
    global _user_id, _book_id
    user_resp = requests.post(
        f"{BASE_URL}/users/", json={"email": "tester@example.com", "name": "Tester"}
    )
    _user_id = user_resp.json()["id"]
    book_resp = requests.post(
        f"{BASE_URL}/books/",
        json={"title": "Test Book", "author": "Author", "price": 20.0, "stock": 5},
    )
    _book_id = book_resp.json()["id"]


def test_create_order_success():
    global _order_id
    setup_test_data()  # sets up data - but also contaminates DB permanently

    response = requests.post(
        f"{BASE_URL}/orders/",
        params={"card_token": "tok_visa"},
        json={
            "user_id": _user_id,
            "items": [{"book_id": _book_id, "quantity": 2}],
        },
    )
    # Will fail if payment API is not reachable - no indication it's an integration test
    assert response.status_code == 201
    _order_id = response.json()["id"]
    assert response.json()["status"] == "confirmed"


def test_order_reduces_stock():
    # Directly queries DB - bypasses the API entirely
    conn = psycopg2.connect(DB_DSN)
    cursor = conn.cursor()
    cursor.execute("SELECT stock FROM books WHERE id = %s", (_book_id,))
    row = cursor.fetchone()
    conn.close()
    # Magic number - 3 because we started with 5 and ordered 2
    assert row[0] == 3


def test_order_with_promo_code():
    # Calls setup again - creates duplicate user (409) and duplicate book, silently ignores errors
    setup_test_data()

    response = requests.post(
        f"{BASE_URL}/orders/",
        params={"card_token": "tok_visa"},
        json={
            "user_id": _user_id,
            "items": [{"book_id": _book_id, "quantity": 1}],
            "promo_code": "SAVE10",
        },
    )
    if response.status_code != 201:
        return  # Silently passes if it fails!
    data = response.json()
    assert data["promo_code"] == "SAVE10"
    # Does not check that the discount was actually applied to the total


def test_cancel_order():
    # Depends on test_create_order_success having populated _order_id
    response = requests.post(f"{BASE_URL}/orders/{_order_id}/cancel")
    assert response.status_code == 200


def test_cancel_expired_order():
    """Test that cancellation fails after the 1-hour window."""
    # This test actually waits - commented out in practice because it takes too long
    # Uncomment to run (takes ~3700 seconds):
    # time.sleep(3700)
    # response = requests.post(f"{BASE_URL}/orders/{_order_id}/cancel")
    # assert response.status_code == 400
    # assert "expired" in response.json()["detail"]
    pass  # always passes, tests nothing


def test_order_not_found():
    response = requests.get(f"{BASE_URL}/orders/9999999")
    assert response.status_code == 404


def test_order_invalid_user():
    response = requests.post(
        f"{BASE_URL}/orders/",
        params={"card_token": "tok_visa"},
        json={
            "user_id": 9999999,
            "items": [{"book_id": 1, "quantity": 1}],
        },
    )
    assert response.status_code == 400


def test_db_state_after_tests():
    """Verify the DB has the expected rows - highly environment-dependent."""
    if not os.getenv("CHECK_DB_STATE"):
        return  # Skip silently unless env var is set
    conn = psycopg2.connect(DB_DSN)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM orders")
    count = cursor.fetchone()[0]
    conn.close()
    assert count > 0  # Checks almost nothing
