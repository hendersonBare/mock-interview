"""HTTP client for the card payment gateway (JSON over HTTPS, stdlib only)."""

import json
import urllib.error
import urllib.request
import uuid
from urllib.parse import quote, urlencode

from .errors import GatewayError
from .models import Charge

# Statuses that mean "try again later": the request may not have been processed.
RETRYABLE_STATUS = {500, 502, 503, 504, 429}
# Total number of attempts per logical request, including the first one.
MAX_ATTEMPTS = 3
DEFAULT_TIMEOUT = 5.0


def new_idempotency_key():
    return uuid.uuid4().hex


class PaymentGateway:
    """Client for the gateway's charges API.

    ``base_url`` is the API root (for example ``https://api.gateway.test``) and
    ``api_key`` the secret key sent as a bearer token.
    """

    def __init__(self, base_url, api_key, *, timeout=DEFAULT_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _do_request(self, method, path, body=None, idempotency_key=None):
        """Send one HTTP request and return the decoded JSON response."""
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(self.base_url + path, data=data, method=method)
        request.add_header("Authorization", f"Bearer {self.api_key}")
        request.add_header("Content-Type", "application/json")
        request.add_header("Accept", "application/json")
        if idempotency_key is not None:
            request.add_header("Idempotency-Key", idempotency_key)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            try:
                payload = json.loads(raw)
            except ValueError:
                payload = raw.decode("utf-8", "replace")
            raise GatewayError(exc.code, payload) from None
        return json.loads(raw) if raw else None

    def _request(self, method, path, body=None):
        """Send a request, retrying transient failures.

        POST requests carry an Idempotency-Key so the gateway can recognise a retry
        of a request it already processed.
        """
        for attempt in range(1, MAX_ATTEMPTS + 1):
            idempotency_key = new_idempotency_key() if method == "POST" else None
            try:
                return self._do_request(method, path, body, idempotency_key)
            except GatewayError as exc:
                if attempt == MAX_ATTEMPTS:
                    raise

    def create_charge(self, amount, currency, source="tok_visa", description=None):
        body = {"amount": amount, "currency": currency.lower(), "source": source}
        if description is not None:
            body["description"] = description
        return Charge.from_dict(self._request("POST", "/v1/charges", body))

    def get_charge(self, charge_id):
        return Charge.from_dict(self._request("GET", f"/v1/charges/{quote(charge_id)}"))

    def list_charges(self, limit=2):
        """Return every charge, following the gateway's cursor pagination.

        ``limit`` is the page size requested from the gateway, not a cap on the
        number of charges returned.
        """
        charges = []
        query = {"limit": limit}
        while True:
            page = self._request("GET", "/v1/charges?" + urlencode(query))
            charges.extend(Charge.from_dict(item) for item in page["data"])
            if not page["has_more"]:
                break
            query["starting_after"] = page["data"][-1]["id"]
            return charges
