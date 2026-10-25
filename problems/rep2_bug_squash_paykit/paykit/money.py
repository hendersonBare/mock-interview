"""Integer minor-unit money values."""

from decimal import ROUND_HALF_UP, Decimal

from .fx import rate_for

# Number of decimal places in each currency's minor unit.
EXPONENT = {"usd": 2, "eur": 2, "gbp": 2, "jpy": 0, "kwd": 3}


class Money:
    """An amount of one currency, stored as an integer number of minor units.

    ``Money(1050, "usd")`` is $10.50, ``Money(1050, "jpy")`` is 1050 yen and
    ``Money(1050, "kwd")`` is 1.050 dinar.
    """

    __slots__ = ("minor_units", "currency")

    def __init__(self, minor_units, currency):
        currency = currency.lower()
        if currency not in EXPONENT:
            raise ValueError(f"unsupported currency: {currency!r}")
        if int(minor_units) != minor_units:
            raise ValueError("minor_units must be a whole number")
        self.minor_units = int(minor_units)
        self.currency = currency

    @classmethod
    def from_decimal(cls, amount, currency):
        """Build from a major-unit amount, e.g. ``Money.from_decimal("10.50", "usd")``."""
        currency = currency.lower()
        scaled = Decimal(str(amount)).scaleb(EXPONENT[currency])
        return cls(int(scaled.quantize(Decimal(1), rounding=ROUND_HALF_UP)), currency)

    def to_decimal(self):
        """The amount in major units, e.g. ``Decimal("10.50")``."""
        return Decimal(self.minor_units).scaleb(-EXPONENT[self.currency])

    def __eq__(self, other):
        if not isinstance(other, Money):
            return NotImplemented
        return (self.minor_units, self.currency) == (other.minor_units, other.currency)

    def __hash__(self):
        return hash((self.minor_units, self.currency))

    def __repr__(self):
        return f"Money({self.minor_units}, {self.currency!r})"

    def __str__(self):
        return f"{self.to_decimal()} {self.currency.upper()}"

    def __add__(self, other):
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self.minor_units + other.minor_units, self.currency)

    def convert(self, to_currency, rates):
        """Convert to another currency using ``rates`` (units per 1 USD).

        The result is rounded half-up to the target currency's minor unit.
        """
        to_currency = to_currency.lower()
        if to_currency not in EXPONENT:
            raise ValueError(f"unsupported currency: {to_currency!r}")
        usd = Decimal(self.minor_units) / rate_for(rates, self.currency)
        minor = usd * rate_for(rates, to_currency)
        return Money(
            int(minor.quantize(Decimal(1), rounding=ROUND_HALF_UP)), to_currency
        )
