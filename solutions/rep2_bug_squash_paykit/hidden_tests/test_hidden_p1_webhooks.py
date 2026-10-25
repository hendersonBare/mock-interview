"""Acceptance tests: webhook verification and dispatch."""

import hashlib
import hmac
import json

import pytest

from paykit import SignatureError, dispatch, verify_signature

SECRET = "whsec_acceptance"
T = 1_800_000_000
BODY = json.dumps({"id": "evt_h1", "type": "charge.refunded", "data": {"amount": 5}})


def sign(message, secret=SECRET):
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()


def header(payload=BODY, t=T, secret=SECRET):
    return f"t={t},v1={sign(f'{t}.{payload}', secret)}"


def test_valid_signature_returns_event():
    assert verify_signature(BODY, header(), SECRET, now=T)["id"] == "evt_h1"


def test_valid_signature_with_bytes_payload():
    assert verify_signature(BODY.encode(), header(), SECRET, now=T + 5)["type"] == "charge.refunded"


def test_valid_signature_at_tolerance_edge():
    assert verify_signature(BODY, header(), SECRET, now=T - 300)["id"] == "evt_h1"


def test_signature_over_body_alone_is_rejected():
    forged = f"t={T},v1={sign(BODY)}"
    with pytest.raises(SignatureError, match="mismatch"):
        verify_signature(BODY, forged, SECRET, now=T)


def test_replayed_signature_with_new_timestamp_is_rejected():
    original = sign(f"{T}.{BODY}")
    with pytest.raises(SignatureError):
        verify_signature(BODY, f"t={T + 60},v1={original}", SECRET, now=T + 60)


def test_wrong_secret_is_rejected():
    with pytest.raises(SignatureError, match="mismatch"):
        verify_signature(BODY, header(secret="whsec_other"), SECRET, now=T)


def test_stale_timestamp_rejected_before_signature_check():
    with pytest.raises(SignatureError, match="tolerance"):
        verify_signature(BODY, header(), SECRET, now=T + 301)


def test_dispatch_returns_handler_result():
    calls = []
    handlers = {"charge.refunded": lambda e: calls.append(e["id"]) or 42}
    assert dispatch({"id": "evt_h2", "type": "charge.refunded"}, handlers) == 42
    assert calls == ["evt_h2"]


def test_dispatch_uses_type_field_only():
    handlers = {"a": lambda e: "A", "b": lambda e: "B"}
    assert dispatch({"id": "evt_h3", "type": "a", "event_type": "b"}, handlers) == "A"


def test_dispatch_verified_event_end_to_end():
    event = verify_signature(BODY, header(), SECRET, now=T)
    assert dispatch(event, {"charge.refunded": lambda e: e["data"]["amount"]}) == 5


def test_dispatch_unknown_type_returns_none():
    called = []
    assert dispatch({"id": "evt_h4", "type": "payout.paid"}, {"x": called.append}) is None
    assert called == []
