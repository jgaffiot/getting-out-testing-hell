"""In-process fakes for external dependencies.

A fake is a simplified but *working* implementation of a collaborator.
It's faster and more reliable than a mock, and more honest than a stub.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.clients.payment_client import PaymentError


@dataclass
class FakeCharge:
    """A recorded charge, standing in for a real payment provider charge."""

    id: str
    amount: int
    card_token: str
    description: str
    refunded: bool = False


class FakePaymentClient:
    """In-memory payment processor. Never makes HTTP calls."""

    def __init__(self, *, fail_on_token: str | None = None) -> None:
        """Create a fake client that declines charges made with ``fail_on_token``."""
        self.charges: list[FakeCharge] = []
        self._fail_on_token = fail_on_token
        self._next_id = 1

    def charge(self, amount: Decimal, card_token: str, description: str = "") -> dict:
        """Record a charge and return a success payload, or raise if declined."""
        if card_token == self._fail_on_token:
            raise PaymentError("Card declined")
        charge = FakeCharge(
            id=f"ch_{self._next_id:04d}",
            amount=int(amount * 100),
            card_token=card_token,
            description=description,
        )
        self._next_id += 1
        self.charges.append(charge)
        return {"id": charge.id, "status": "succeeded", "amount": charge.amount}

    def refund(self, charge_id: str) -> dict:
        """Mark a recorded charge as refunded, or raise if it is unknown."""
        charge = next((c for c in self.charges if c.id == charge_id), None)
        if not charge:
            raise PaymentError(f"Charge {charge_id} not found")
        charge.refunded = True
        return {"id": f"re_{charge_id}", "status": "succeeded"}

    @property
    def last_charge(self) -> FakeCharge | None:
        """Return the most recent charge, or None if none were made."""
        return self.charges[-1] if self.charges else None


@dataclass
class SentEmail:
    """A recorded outbound email, captured instead of being delivered."""

    to: str
    subject: str
    body: str


class FakeEmailClient:
    """In-memory email sender. Records sent emails for assertions."""

    def __init__(self) -> None:
        """Create a fake client with an empty record of sent emails."""
        self.sent: list[SentEmail] = []

    def send(self, to: str, subject: str, body: str) -> None:
        """Record an email instead of sending it."""
        self.sent.append(SentEmail(to=to, subject=subject, body=body))

    def emails_to(self, address: str) -> list[SentEmail]:
        """Return every recorded email addressed to ``address``."""
        return [e for e in self.sent if e.to == address]

    @property
    def last_email(self) -> SentEmail | None:
        """Return the most recent email, or None if none were sent."""
        return self.sent[-1] if self.sent else None
