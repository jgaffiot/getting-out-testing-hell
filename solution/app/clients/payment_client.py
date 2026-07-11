"""Payment client configured via the :class:`~solution.app.settings.Settings`."""

from decimal import Decimal
from http import HTTPStatus

import httpx
from solution.app.settings import Settings

from app.clients.payment_client import PaymentError


class PaymentClient:
    """Talks to the (fake) payment provider using injected settings."""

    def __init__(self, settings: Settings) -> None:
        """Store the settings used to reach the payment provider."""
        self._settings = settings

    def charge(self, amount: Decimal, card_token: str, description: str = "") -> dict:
        """Charge ``amount`` to ``card_token``, raising PaymentError on failure."""
        response = httpx.post(
            f"{self._settings.payment_api_url}/charges",
            headers={"Authorization": f"Bearer {self._settings.payment_api_key}"},
            json={
                "amount": int(amount * 100),  # cents
                "currency": "eur",
                "source": card_token,
                "description": description,
            },
            timeout=10.0,
        )
        if response.status_code != HTTPStatus.OK:
            raise PaymentError(f"Payment failed: {response.text}")
        return response.json()

    def refund(self, charge_id: str) -> dict:
        """Refund a previous charge, raising PaymentError on failure."""
        response = httpx.post(
            f"{self._settings.payment_api_url}/refunds",
            headers={"Authorization": f"Bearer {self._settings.payment_api_key}"},
            json={"charge_id": charge_id},
            timeout=10.0,
        )
        if response.status_code != HTTPStatus.OK:
            raise PaymentError(f"Refund failed: {response.text}")
        return response.json()
