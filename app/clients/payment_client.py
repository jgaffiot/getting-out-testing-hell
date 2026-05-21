from decimal import Decimal
import httpx
from app.config import PAYMENT_API_URL, PAYMENT_API_KEY


class PaymentError(Exception):
    pass


class PaymentClient:
    def charge(self, amount: Decimal, card_token: str, description: str = "") -> dict:
        response = httpx.post(
            f"{PAYMENT_API_URL}/charges",
            headers={"Authorization": f"Bearer {PAYMENT_API_KEY}"},
            json={
                "amount": int(amount * 100),  # cents
                "currency": "eur",
                "source": card_token,
                "description": description,
            },
            timeout=10.0,
        )
        if response.status_code != 200:
            raise PaymentError(f"Payment failed: {response.text}")
        return response.json()

    def refund(self, charge_id: str) -> dict:
        response = httpx.post(
            f"{PAYMENT_API_URL}/refunds",
            headers={"Authorization": f"Bearer {PAYMENT_API_KEY}"},
            json={"charge_id": charge_id},
            timeout=10.0,
        )
        if response.status_code != 200:
            raise PaymentError(f"Refund failed: {response.text}")
        return response.json()
