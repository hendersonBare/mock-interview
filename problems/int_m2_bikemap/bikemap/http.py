"""Minimal HTTP transport on top of urllib.

`send` never raises for HTTP error statuses; it returns the response so callers can
decide what to do. It raises TransportError when no response arrives.
"""
from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Mapping

from .errors import ApiError, TransportError

DEFAULT_TIMEOUT = 5.0


@dataclass
class HttpResponse:
    status: int
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    def header(self, name: str, default: str | None = None) -> str | None:
        lowered = name.lower()
        for key, value in self.headers.items():
            if key.lower() == lowered:
                return value
        return default

    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8"))

    def raise_for_status(self) -> None:
        if self.ok:
            return
        message = ""
        try:
            message = self.json().get("error", {}).get("message", "")
        except (ValueError, AttributeError, UnicodeDecodeError):
            message = self.body[:200].decode("utf-8", "replace")
        raise ApiError(self.status, message)


def send(method: str, url: str, *, headers: Mapping[str, str] | None = None,
         json_body: Any = None, timeout: float = DEFAULT_TIMEOUT) -> HttpResponse:
    data = None
    all_headers = {"Accept": "*/*"}
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        all_headers["Content-Type"] = "application/json"
    all_headers.update(headers or {})
    request = urllib.request.Request(url, data=data, method=method.upper(), headers=all_headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            return HttpResponse(resp.status, dict(resp.headers.items()), resp.read())
    except urllib.error.HTTPError as exc:
        body = exc.read()
        response = HttpResponse(exc.code, dict(exc.headers.items()), body)
        exc.close()
        return response
    except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError) as exc:
        raise TransportError(f"{method.upper()} {url}: {exc}") from exc
