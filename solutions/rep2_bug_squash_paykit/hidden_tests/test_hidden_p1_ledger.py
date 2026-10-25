"""Acceptance tests: ledger balance and refunds."""

import pytest

from paykit import Charge, Ledger


def ch(id, amount, status="succeeded", refunded=0, currency="usd"):
    return Charge(id=id, amount=amount, currency=currency, status=status, refunded=refunded)


@pytest.mark.parametrize("status", ["failed", "pending", "canceled"])
def test_balance_ignores_unsettled_status(status):
    ledger = Ledger([ch("a", 1000), ch("b", 700, status=status)])
    assert ledger.balance() == 1000


def test_balance_nets_refunds_of_succeeded_only():
    ledger = Ledger([ch("a", 1000, refunded=250), ch("b", 400, status="failed", refunded=0)])
    assert ledger.balance() == 750


def test_balance_filters_by_currency():
    ledger = Ledger([ch("a", 1000), ch("b", 500, currency="eur")])
    assert ledger.balance("eur") == 500
    assert ledger.balance("usd") == 1000


@pytest.mark.parametrize("amount, ok", [(1, True), (200, True), (201, False), (300, False)])
def test_can_refund_bounded_by_remaining(amount, ok):
    ledger = Ledger([ch("a", 1000, refunded=800)])
    assert ledger.can_refund("a", amount) is ok


def test_fully_refunded_charge_cannot_be_refunded():
    ledger = Ledger([ch("a", 500, refunded=500)])
    assert ledger.can_refund("a", 1) is False


def test_refunds_through_api_accumulate_toward_limit():
    ledger = Ledger([ch("a", 1000)])
    ledger.refund("a", 600)
    assert ledger.can_refund("a", 400) is True
    assert ledger.can_refund("a", 401) is False
    with pytest.raises(ValueError):
        ledger.refund("a", 401)
    assert ledger.get("a").refunded == 600


@pytest.mark.parametrize("amount", [0, -5, 1001])
def test_refund_rejects_invalid_amount_and_keeps_state(amount):
    ledger = Ledger([ch("a", 1000)])
    with pytest.raises(ValueError):
        ledger.refund("a", amount)
    assert ledger.get("a").refunded == 0


def test_refund_exact_remaining_amount():
    ledger = Ledger([ch("a", 1000, refunded=300)])
    assert ledger.refund("a", 700) == 1000
    assert ledger.balance() == 0
