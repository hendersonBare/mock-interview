"""Plain data objects returned by the gateway client."""

from dataclasses import dataclass


@dataclass
class Charge:
    """A card charge. ``amount`` and ``refunded`` are integers in minor units."""

    id: str
    amount: int
    currency: str
    status: str
    refunded: int = 0

    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data["id"],
            amount=int(data["amount"]),
            currency=data["currency"].lower(),
            status=data["status"],
            refunded=int(data.get("refunded", 0)),
        )

    def to_dict(self):
        return {
            "id": self.id,
            "amount": self.amount,
            "currency": self.currency,
            "status": self.status,
            "refunded": self.refunded,
        }
