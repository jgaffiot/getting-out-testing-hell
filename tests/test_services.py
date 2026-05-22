"""
Service-layer tests. These look like unit tests but are secretly coupled
to the real database and use overly-patched mocks that test nothing real.
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.services.order_service import OrderService, PROMO_CODES


# --- Tests that look like unit tests but require a real DB ---


class TestOrderServiceCalculation:
    def test_promo_code_save10(self):
        # Calls calculate_order_total which opens a real DB connection
        service = OrderService()
        # This will raise OperationalError if no DB is running — no clear error message
        total = service.calculate_order_total(
            items=[{"book_id": 1, "quantity": 1}],
            promo_code="SAVE10",
        )
        # Only checks it's not None — would pass even if discount wasn't applied
        assert total is not None

    def test_promo_codes_are_defined(self):
        # Tests a dict constant, not any behavior
        assert "SAVE10" in PROMO_CODES
        assert "SAVE20" in PROMO_CODES
        assert PROMO_CODES["SAVE10"] == Decimal("0.10")


# --- Tests that mock so much they verify nothing ---


class TestOrderCreation:
    @patch("app.services.order_service.SessionLocal")
    @patch("app.services.order_service.PaymentClient")
    @patch("app.services.order_service.EmailClient")
    def test_create_order_calls_payment(
        self, mock_email_cls, mock_payment_cls, mock_session_cls
    ):
        # Build a maze of mocks
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = "user@example.com"
        mock_user.is_active = True

        mock_book = MagicMock()
        mock_book.id = 1
        mock_book.price = Decimal("20.00")
        mock_book.stock = 5
        mock_book.title = "Test Book"

        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        # Returns user first call, book second call
        mock_query.first.side_effect = [mock_user, mock_book]

        mock_payment = MagicMock()
        mock_payment_cls.return_value = mock_payment
        mock_payment.charge.return_value = {"id": "ch_123", "status": "succeeded"}

        mock_email = MagicMock()
        mock_email_cls.return_value = mock_email

        service = OrderService()
        service.create_order(
            user_id=1,
            items=[{"book_id": 1, "quantity": 2}],
            card_token="tok_visa",
        )

        # Only verifies the mock was called — not that business logic is correct
        mock_payment.charge.assert_called_once()

    @patch("app.services.order_service.SessionLocal")
    @patch("app.services.order_service.PaymentClient")
    @patch("app.services.order_service.EmailClient")
    def test_create_order_sends_email(
        self, mock_email_cls, mock_payment_cls, mock_session_cls
    ):
        # Copy-paste of the above setup — no shared fixture
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = "user@example.com"
        mock_user.is_active = True

        mock_book = MagicMock()
        mock_book.id = 1
        mock_book.price = Decimal("20.00")
        mock_book.stock = 5

        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.side_effect = [mock_user, mock_book]

        mock_payment = MagicMock()
        mock_payment_cls.return_value = mock_payment
        mock_payment.charge.return_value = {"id": "ch_456", "status": "succeeded"}

        mock_email = MagicMock()
        mock_email_cls.return_value = mock_email

        service = OrderService()
        service.create_order(
            user_id=1,
            items=[{"book_id": 1, "quantity": 1}],
            card_token="tok_visa",
        )

        # Checks the mock was called — does not check email content or recipient
        mock_email.send.assert_called_once()

    @patch("app.services.order_service.SessionLocal")
    @patch("app.services.order_service.PaymentClient")
    @patch("app.services.order_service.EmailClient")
    def test_inactive_user_raises(
        self, mock_email_cls, mock_payment_cls, mock_session_cls
    ):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        mock_user = MagicMock()
        mock_user.is_active = False

        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_user

        service = OrderService()
        with pytest.raises(ValueError):
            service.create_order(user_id=1, items=[], card_token="tok_visa")


# --- Test that never fails ---


def test_order_service_instantiation():
    # Instantiating the service tries to connect to the payment API URL — but doesn't fail yet
    # This test always passes and asserts nothing meaningful
    service = OrderService()
    assert service is not None
