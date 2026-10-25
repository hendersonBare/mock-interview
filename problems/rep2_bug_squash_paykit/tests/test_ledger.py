import pytest

from paykit import Charge, Ledger


def charge(id, amount, status="succeeded", refunded=0, currency="usd"):
    return Charge(
        id=id, amount=amount, currency=currency, status=status, refunded=refunded
    )


def test_refund_updates_refunded_total():
    ledger = Ledger([charge("ch_a", 1000)])

    assert ledger.refund("ch_a", 300) == 300
    assert ledger.refund("ch_a", 200) == 500
    assert ledger.balance() == 500


def test_can_refund_allows_remaining_amount():
    ledger = Ledger([charge("ch_a", 1000, refunded=800)])

    assert ledger.can_refund("ch_a", 200) is True
    assert ledger.can_refund("ch_a", 0) is False


def test_balance_excludes_non_succeeded():
    ledger = Ledger(
        [charge("ch_a", 1000, refunded=800), charge("ch_b", 500, status="failed")]
    )

    assert ledger.balance() == 200


def test_can_refund_blocks_over_refund():
    ledger = Ledger([charge("ch_a", 1000, refunded=800)])

    assert ledger.can_refund("ch_a", 300) is False


def test_refund_rejects_over_refund():
    ledger = Ledger([charge("ch_a", 1000)])

    with pytest.raises(ValueError):
        ledger.refund("ch_a", 1200)
