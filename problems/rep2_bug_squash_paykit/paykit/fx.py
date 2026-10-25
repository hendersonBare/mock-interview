"""Exchange rates, expressed as units of each currency per 1 USD."""

import json
from decimal import Decimal
from pathlib import Path

DEFAULT_RATES_PATH = Path(__file__).resolve().parent.parent / "data" / "fx_rates.json"


def load_rates(path=DEFAULT_RATES_PATH):
    """Read a rates file and return ``{currency: Decimal(units per 1 USD)}``."""
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    rates = {code.lower(): Decimal(str(value)) for code, value in raw["rates"].items()}
    if rates.get("usd") != 1:
        raise ValueError("rates must be quoted against 1 USD")
    return rates


def rate_for(rates, currency):
    try:
        return Decimal(str(rates[currency.lower()]))
    except KeyError:
        raise ValueError(f"no exchange rate for {currency!r}") from None
