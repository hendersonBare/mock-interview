import hashlib
import hmac
import json

import pytest

from paykit import SignatureError, dispatch, verify_signature

SECRET = "whsec_test_secret"
NOW = 1_760_000_000


def signed_header(payload, timestamp=NOW, secret=SECRET):
    message = f"{timestamp}.{payload}".encode()
    signature = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={signature}"


PAYLOAD = json.dumps(
    {"id": "evt_1", "type": "charge.succeeded", "data": {"id": "ch_1001"}}
)


def test_verify_accepts_valid_signature():
    event = verify_signature(PAYLOAD, signed_header(PAYLOAD), SECRET, now=NOW + 10)

    assert event["id"] == "evt_1"
    assert event["type"] == "charge.succeeded"


def test_verify_rejects_tampered_payload():
    header = signed_header(PAYLOAD)
    tampered = PAYLOAD.replace("ch_1001", "ch_9999")

    with pytest.raises(SignatureError):
        verify_signature(tampered, header, SECRET, now=NOW)


def test_verify_rejects_timestamp_outside_tolerance():
    header = signed_header(PAYLOAD)

    with pytest.raises(SignatureError, match="tolerance"):
        verify_signature(PAYLOAD, header, SECRET, now=NOW + 301)


def test_dispatch_routes_to_handler():
    seen = []
    handlers = {"charge.refunded": lambda event: seen.append(event["id"]) or "handled"}

    result = dispatch({"id": "evt_9", "type": "charge.refunded"}, handlers)

    assert seen == ["evt_9"]
    assert result == "handled"
