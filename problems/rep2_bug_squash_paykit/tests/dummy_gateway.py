"""A fake payment gateway for the test suite: real HTTP on 127.0.0.1, in-process.

Routes (JSON in, JSON out, bearer-token auth):

    GET  /v1/charges?limit=N&starting_after=ID   cursor-paginated list of charges
    GET  /v1/charges/<id>                        one charge
    POST /v1/charges                             create a charge

Two path prefixes simulate an unhealthy gateway in front of the same routes:

    /rejecting/...   always answers 400 (the request is refused as invalid)
    /flaky/...       the first request answers 500, later ones are served normally

Every request is recorded in ``DummyGateway.requests`` (method, path, Idempotency-Key
and Authorization headers) and logged to stdout as ``METHOD path -> status``; run
pytest with ``-s`` to see the log. ``python tests/dummy_gateway.py`` starts a server
by hand and prints its URL.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

API_KEY = "sk_test_paykit_local_0001"
CHARGES_FILE = Path(__file__).resolve().parent.parent / "data" / "charges.json"
SUPPORTED_CURRENCIES = {"usd", "eur", "gbp", "jpy", "kwd"}


class DummyGateway:
    def __init__(self, charges_file=CHARGES_FILE):
        self.charges = json.loads(Path(charges_file).read_text())
        self.requests = []
        self.flaky_failures = 0
        self._lock = threading.Lock()
        self._next_id = 2001
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(self))
        self._server.daemon_threads = True
        self._thread = threading.Thread(
            target=self._server.serve_forever, args=(0.05,), daemon=True
        )

    @property
    def url(self):
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}"

    def start(self):
        self._thread.start()
        return self

    def stop(self):
        self._server.shutdown()
        self._server.server_close()

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()

    # -- request handling -------------------------------------------------------

    def handle(self, method, raw_path, headers, body):
        """Return ``(status, payload)`` for one request."""
        parts = urlsplit(raw_path)
        path, query = parts.path, parse_qs(parts.query)
        with self._lock:
            self.requests.append(
                {
                    "method": method,
                    "path": path,
                    "query": parts.query,
                    "idempotency_key": headers.get("Idempotency-Key"),
                    "authorization": headers.get("Authorization"),
                }
            )
            if headers.get("Authorization") != f"Bearer {API_KEY}":
                return 401, _error("authentication_error", "invalid API key")
            if path.startswith("/rejecting/"):
                return 400, _error("invalid_request_error", "request refused")
            if path.startswith("/flaky/"):
                path = path[len("/flaky") :]
                if self.flaky_failures == 0:
                    self.flaky_failures += 1
                    return 500, _error("api_error", "temporary failure, try again")
            return self._route(method, path, query, body)

    def _route(self, method, path, query, body):
        if path == "/v1/charges" and method == "GET":
            return self._list_charges(query)
        if path == "/v1/charges" and method == "POST":
            return self._create_charge(body)
        if path.startswith("/v1/charges/") and method == "GET":
            charge_id = path[len("/v1/charges/") :]
            for charge in self.charges:
                if charge["id"] == charge_id:
                    return 200, charge
            return 404, _error("invalid_request_error", f"no such charge: {charge_id}")
        return 404, _error("invalid_request_error", f"unknown route {method} {path}")

    def _list_charges(self, query):
        limit = int(query.get("limit", ["10"])[0])
        start = 0
        if "starting_after" in query:
            cursor = query["starting_after"][0]
            ids = [charge["id"] for charge in self.charges]
            if cursor not in ids:
                return 400, _error("invalid_request_error", f"bad cursor: {cursor}")
            start = ids.index(cursor) + 1
        page = self.charges[start : start + limit]
        has_more = start + limit < len(self.charges)
        return 200, {"object": "list", "data": page, "has_more": has_more}

    def _create_charge(self, body):
        amount, currency = body.get("amount"), str(body.get("currency", "")).lower()
        if not isinstance(amount, int) or amount <= 0:
            return 400, _error(
                "invalid_request_error", "amount must be a positive integer"
            )
        if currency not in SUPPORTED_CURRENCIES:
            return 400, _error(
                "invalid_request_error", f"unsupported currency: {currency}"
            )
        charge = {
            "id": f"ch_{self._next_id}",
            "amount": amount,
            "currency": currency,
            "status": "succeeded",
            "refunded": 0,
        }
        self._next_id += 1
        self.charges.append(charge)
        return 200, charge


def _error(kind, message):
    return {"error": {"type": kind, "message": message}}


def _make_handler(gateway):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _serve(self):
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            try:
                body = json.loads(raw) if raw else {}
            except ValueError:
                status, payload = 400, _error(
                    "invalid_request_error", "body is not JSON"
                )
            else:
                status, payload = gateway.handle(
                    self.command, self.path, self.headers, body
                )
            data = json.dumps(payload).encode()
            print(f"dummy_gateway: {self.command} {self.path} -> {status}", flush=True)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        do_GET = do_POST = _serve

        def log_message(self, format, *args):
            pass

    return Handler


if __name__ == "__main__":
    with DummyGateway() as server:
        print(f"dummy gateway listening on {server.url}  (API key: {API_KEY})")
        print("Ctrl-C to stop")
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass
