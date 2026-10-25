"""In-memory ledger of charges and refunds."""


class Ledger:
    """Tracks charges by id. All amounts are integers in minor units."""

    def __init__(self, charges=()):
        self._charges = {}
        for charge in charges:
            self.add(charge)

    def add(self, charge):
        if charge.id in self._charges:
            raise ValueError(f"duplicate charge id: {charge.id}")
        self._charges[charge.id] = charge

    def get(self, charge_id):
        try:
            return self._charges[charge_id]
        except KeyError:
            raise KeyError(f"unknown charge: {charge_id}") from None

    def __len__(self):
        return len(self._charges)

    def balance(self, currency="usd"):
        """Money actually collected in ``currency``: succeeded charges net of refunds."""
        return sum(
            charge.amount - charge.refunded
            for charge in self._charges.values()
            if charge.currency == currency
        )

    def can_refund(self, charge_id, amount):
        """True when ``amount`` can still be refunded on the charge."""
        charge = self.get(charge_id)
        return 0 < amount <= charge.amount

    def refund(self, charge_id, amount):
        """Refund part of a charge and return the new refunded total."""
        charge = self.get(charge_id)
        charge.refunded += amount
        return charge.refunded
