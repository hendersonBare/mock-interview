import pytest
from dummy_gateway import API_KEY, DummyGateway

from paykit import GatewayError, PaymentGateway


@pytest.fixture
def server():
    with DummyGateway() as srv:
        yield srv


def client(server, prefix=""):
    return PaymentGateway(server.url + prefix, API_KEY, timeout=2)


def test_create_charge_returns_succeeded_charge(server):
    charge = client(server).create_charge(1500, "USD")

    assert charge.amount == 1500
    assert charge.currency == "usd"
    assert charge.status == "succeeded"
    assert charge.refunded == 0
    [request] = server.requests
    assert request["method"] == "POST"
    assert request["authorization"] == f"Bearer {API_KEY}"


def test_retries_server_error_until_success(server):
    charge = client(server, "/flaky").create_charge(800, "eur")

    assert charge.status == "succeeded"
    assert [r["method"] for r in server.requests] == ["POST", "POST"]


def test_list_charges_follows_pagination(server):
    charges = client(server).list_charges(limit=2)

    assert [c.id for c in charges] == [
        "ch_1001",
        "ch_1002",
        "ch_1003",
        "ch_1004",
        "ch_1005",
    ]


def test_does_not_retry_client_error(server):
    with pytest.raises(GatewayError) as excinfo:
        client(server, "/rejecting").create_charge(500, "usd")

    assert excinfo.value.status == 400
    assert len(server.requests) == 1


def test_retry_reuses_idempotency_key(server):
    client(server, "/flaky").create_charge(2000, "gbp")

    keys = [r["idempotency_key"] for r in server.requests]
    assert len(keys) == 2
    assert keys[0], "POST requests must carry an Idempotency-Key"
    assert keys[0] == keys[1], "the retry was sent with a different Idempotency-Key"
