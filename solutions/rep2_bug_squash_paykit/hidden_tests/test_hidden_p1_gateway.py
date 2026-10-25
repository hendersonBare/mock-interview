"""Acceptance tests: gateway client (pagination, retries, idempotency)."""

import pytest
from hidden_gateway_server import API_KEY, HiddenGateway

from paykit import MAX_ATTEMPTS, GatewayError, PaymentGateway


@pytest.fixture
def srv():
    with HiddenGateway() as s:
        yield s


def gw(srv, prefix=""):
    return PaymentGateway(srv.url + prefix, API_KEY, timeout=2)


ALL_IDS = [f"ch_h{n}" for n in range(1, 8)]


# pagination ------------------------------------------------------------------


@pytest.mark.parametrize("limit", [1, 2, 3, 6])
def test_list_charges_returns_every_charge_for_any_page_size(srv, limit):
    assert [c.id for c in gw(srv).list_charges(limit=limit)] == ALL_IDS


def test_list_charges_default_page_size_still_returns_everything(srv):
    assert [c.id for c in gw(srv).list_charges()] == ALL_IDS


def test_list_charges_sends_last_id_as_cursor(srv):
    gw(srv).list_charges(limit=3)
    cursors = [r["query"].get("starting_after", [None])[0] for r in srv.requests]
    assert cursors == [None, "ch_h3", "ch_h6"]
    assert all(r["query"]["limit"] == ["3"] for r in srv.requests)


def test_list_charges_first_request_uses_page_size_without_cursor(srv):
    gw(srv).list_charges(limit=4)
    first = srv.requests[0]["query"]
    assert first == {"limit": ["4"]}


def test_list_charges_single_page(srv):
    charges = gw(srv).list_charges(limit=50)
    assert [c.id for c in charges] == ALL_IDS
    assert len(srv.requests) == 1


def test_list_charges_empty_account():
    with HiddenGateway(charges=[]) as s:
        assert gw(s).list_charges() == []


# retries ---------------------------------------------------------------------


def test_client_error_is_not_retried(srv):
    with pytest.raises(GatewayError) as excinfo:
        gw(srv, "/rejecting").create_charge(100, "usd")
    assert excinfo.value.status == 400
    assert len(srv.requests) == 1


def test_not_found_is_not_retried(srv):
    with pytest.raises(GatewayError) as excinfo:
        gw(srv).get_charge("ch_missing")
    assert excinfo.value.status == 404
    assert len(srv.requests) == 1


def test_rejected_amount_is_not_retried(srv):
    with pytest.raises(GatewayError):
        gw(srv).create_charge(0, "usd")
    assert len(srv.requests) == 1


def test_persistent_server_error_gives_up_after_max_attempts(srv):
    with pytest.raises(GatewayError) as excinfo:
        gw(srv, "/down").create_charge(100, "usd")
    assert excinfo.value.status == 503
    assert len(srv.requests) == MAX_ATTEMPTS == 3


def test_rate_limited_request_is_retried(srv):
    charge = gw(srv, "/throttled").create_charge(100, "usd")
    assert charge.status == "succeeded"
    assert len(srv.requests) == 2


def test_server_error_then_success_on_get(srv):
    assert gw(srv, "/flaky").get_charge("ch_h2").amount == 200
    assert len(srv.requests) == 2


# idempotency -----------------------------------------------------------------


def test_retry_after_500_reuses_key(srv):
    gw(srv, "/flaky").create_charge(100, "usd")
    keys = [r["idempotency_key"] for r in srv.requests]
    assert len(keys) == 2 and keys[0] and keys[0] == keys[1]


def test_all_attempts_share_one_key(srv):
    with pytest.raises(GatewayError):
        gw(srv, "/down").create_charge(100, "usd")
    keys = {r["idempotency_key"] for r in srv.requests}
    assert len(srv.requests) == 3
    assert len(keys) == 1 and None not in keys


def test_separate_charges_use_separate_keys(srv):
    client = gw(srv)
    client.create_charge(100, "usd")
    client.create_charge(100, "usd")
    first, second = (r["idempotency_key"] for r in srv.requests)
    assert first and second and first != second


def test_get_requests_carry_no_idempotency_key(srv):
    gw(srv, "/flaky").get_charge("ch_h1")
    assert [r["idempotency_key"] for r in srv.requests] == [None, None]


def test_requests_carry_auth_and_json_headers(srv):
    gw(srv).create_charge(100, "usd")
    [r] = srv.requests
    assert r["authorization"] == f"Bearer {API_KEY}"
    assert r["content_type"] == "application/json"
