"""Fake gateway for the acceptance tests (independent copy of the visible test server).

Extra failure prefixes compared with the visible server:
    /rejecting/...  always 400          /flaky/...      500 once, then normal
    /down/...       always 503          /throttled/...  429 once, then normal
Charges are embedded (seven of them) so the tests do not depend on data/ files.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

API_KEY = "sk_test_acceptance_0002"
CHARGES = [
    {"id": f"ch_h{n}", "amount": 100 * n, "currency": "usd", "status": "succeeded", "refunded": 0}
    for n in range(1, 8)
]


class HiddenGateway:
    def __init__(self, charges=None):
        self.charges = [dict(c) for c in (CHARGES if charges is None else charges)]
        self.requests = []
        self.once_failed = set()
        self._lock = threading.Lock()
        self._next_id = 9001
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(self))
        self._server.daemon_threads = True
        self._thread = threading.Thread(target=self._server.serve_forever, args=(0.05,), daemon=True)

    @property
    def url(self):
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}"

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._server.shutdown()
        self._server.server_close()

    def handle(self, method, raw_path, headers, body):
        parts = urlsplit(raw_path)
        path, query = parts.path, parse_qs(parts.query)
        with self._lock:
            self.requests.append(
                {
                    "method": method,
                    "path": path,
                    "query": query,
                    "idempotency_key": headers.get("Idempotency-Key"),
                    "authorization": headers.get("Authorization"),
                    "content_type": headers.get("Content-Type"),
                }
            )
            if headers.get("Authorization") != f"Bearer {API_KEY}":
                return 401, _error("authentication_error", "invalid API key")
            prefix, _, rest = path.lstrip("/").partition("/")
            if prefix == "rejecting":
                return 400, _error("invalid_request_error", "request refused")
            if prefix == "down":
                return 503, _error("api_error", "unavailable")
            if prefix in ("flaky", "throttled"):
                path = "/" + rest
                if prefix not in self.once_failed:
                    self.once_failed.add(prefix)
                    return (500 if prefix == "flaky" else 429), _error("api_error", "try again")
            return self._route(method, path, query, body)

    def _route(self, method, path, query, body):
        if path == "/v1/charges" and method == "GET":
            limit = int(query.get("limit", ["10"])[0])
            start = 0
            if "starting_after" in query:
                ids = [c["id"] for c in self.charges]
                start = ids.index(query["starting_after"][0]) + 1
            page = self.charges[start : start + limit]
            return 200, {"object": "list", "data": page, "has_more": start + limit < len(self.charges)}
        if path == "/v1/charges" and method == "POST":
            if not isinstance(body.get("amount"), int) or body["amount"] <= 0:
                return 400, _error("invalid_request_error", "bad amount")
            charge = {
                "id": f"ch_h{self._next_id}",
                "amount": body["amount"],
                "currency": body["currency"],
                "status": "succeeded",
                "refunded": 0,
            }
            self._next_id += 1
            self.charges.append(charge)
            return 200, charge
        if path.startswith("/v1/charges/") and method == "GET":
            cid = path.rsplit("/", 1)[1]
            for charge in self.charges:
                if charge["id"] == cid:
                    return 200, charge
            return 404, _error("invalid_request_error", "no such charge")
        return 404, _error("invalid_request_error", "unknown route")


def _error(kind, message):
    return {"error": {"type": kind, "message": message}}


def _make_handler(gateway):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _serve(self):
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            body = json.loads(raw) if raw else {}
            status, payload = gateway.handle(self.command, self.path, self.headers, body)
            data = json.dumps(payload).encode()
            print(f"hidden_gateway: {self.command} {self.path} -> {status}", flush=True)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        do_GET = do_POST = _serve

        def log_message(self, format, *args):
            pass

    return Handler
