import pytest

from paykit import Money, load_rates


@pytest.fixture
def rates():
    return load_rates()


def test_currency_code_is_lowercased():
    assert Money(500, "USD") == Money(500, "usd")
    assert Money(500, "USD").currency == "usd"


def test_add_same_currency():
    assert Money(1050, "eur") + Money(250, "eur") == Money(1300, "eur")


def test_add_rejects_currency_mismatch():
    with pytest.raises(ValueError):
        Money(1000, "usd") + Money(1000, "eur")


def test_convert_usd_to_eur(rates):
    assert Money(1000, "usd").convert("eur", rates) == Money(920, "eur")


def test_convert_across_exponents(rates):
    # $10.00 at 150 JPY per USD is 1500 yen; the yen has no minor unit.
    assert Money(1000, "usd").convert("jpy", rates) == Money(1500, "jpy")
