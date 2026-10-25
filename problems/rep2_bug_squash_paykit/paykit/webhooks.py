"""Webhook signature verification and event dispatch.

The gateway signs each webhook delivery and sends the result in a header of the form
``t=<unix timestamp>,v1=<hex HMAC-SHA256>``. The signed string is the timestamp, a
dot, and the raw request body: ``f"{t}.{payload}"``.
"""

import hashlib
import hmac
import json
import time

from .errors import SignatureError

# Maximum age (and clock skew) accepted for a signed delivery, in seconds.
TOLERANCE_SECONDS = 300


def parse_signature_header(header):
    """Return ``(timestamp, signature)`` from a ``t=...,v1=...`` header."""
    fields = {}
    for item in header.split(","):
        key, sep, value = item.strip().partition("=")
        if sep:
            fields[key] = value
    try:
        return int(fields["t"]), fields["v1"]
    except (KeyError, ValueError):
        raise SignatureError("malformed signature header") from None


def verify_signature(payload, header, secret, now=None):
    """Check a webhook delivery and return the parsed JSON event.

    ``payload`` is the raw request body (str or bytes), ``header`` the signature
    header and ``secret`` the endpoint's signing secret. Raises SignatureError when
    the timestamp is too old or the signature does not match.
    """
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")
    timestamp, signature = parse_signature_header(header)
    now = time.time() if now is None else now
    if abs(now - timestamp) > TOLERANCE_SECONDS:
        raise SignatureError("timestamp outside tolerance")
    expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise SignatureError("signature mismatch")
    return json.loads(payload)


def dispatch(event, handlers):
    """Call the handler registered for ``event["type"]`` and return its result.

    ``handlers`` maps event types (for example ``"charge.refunded"``) to callables
    taking the event. Events without a handler are ignored and return None.
    """
    handler = handlers.get(event.get("event_type"))
    if handler is None:
        return None
    return handler(event)
