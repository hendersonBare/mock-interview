"""Acceptance tests: Money arithmetic and conversion."""

import os
from pathlib import Path

import pytest

from paykit import Money, load_rates


@pytest.fixture(scope="module")
def rates():
    return load_rates(Path(os.environ["GRADE_WORKDIR"]) / "data" / "fx_rates.json")


@pytest.mark.parametrize(
    "src, dst",
    [
        (Money(1000, "usd"), Money(1500, "jpy")),
        (Money(1500, "jpy"), Money(1000, "usd")),
        (Money(1000, "usd"), Money(3100, "kwd")),
        (Money(3100, "kwd"), Money(1500, "jpy")),
        (Money(1500, "jpy"), Money(3100, "kwd")),
        (Money(1, "usd"), Money(2, "jpy")),
    ],
    ids=["usd-jpy", "jpy-usd", "usd-kwd", "kwd-jpy", "jpy-kwd", "one-cent-rounds-half-up"],
)
def test_convert_respects_minor_unit_exponents(rates, src, dst):
    assert src.convert(dst.currency, rates) == dst


@pytest.mark.parametrize(
    "src, dst",
    [
        (Money(1000, "usd"), Money(790, "gbp")),
        (Money(920, "eur"), Money(1000, "usd")),
        (Money(1000, "eur"), Money(1000, "eur")),
    ],
    ids=["usd-gbp", "eur-usd", "same-currency"],
)
def test_convert_between_two_decimal_currencies(rates, src, dst):
    assert src.convert(dst.currency, rates) == dst


def test_convert_accepts_uppercase_target(rates):
    assert Money(1000, "usd").convert("JPY", rates) == Money(1500, "jpy")


@pytest.mark.parametrize("left, right", [("usd", "eur"), ("eur", "usd"), ("jpy", "kwd")])
def test_adding_different_currencies_raises(left, right):
    with pytest.raises(ValueError):
        Money(100, left) + Money(100, right)


def test_add_ignores_case_of_currency_code():
    assert Money(1, "USD") + Money(2, "usd") == Money(3, "usd")


def test_add_non_money_is_type_error():
    with pytest.raises(TypeError):
        Money(1, "usd") + 1
