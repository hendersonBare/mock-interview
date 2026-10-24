"""In-process HTTP server that imitates the Pathfinder maps API.

Tests start it on an ephemeral port::

    with MockMapServer() as api:
        ...  # api.url, api.requests, api.renders

A scenario (dict or JSON file) can replace the landmark data and configure faults.
Every request is logged as "METHOD /path?query -> status" (stdout unless quiet, plus an
optional log file) and kept in ``requests``. Each successful render is kept in
``renders`` with the request body, what was drawn, and the PNG digest.
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

from bikemap.png import encode_png

from .raster import Canvas, Projection, hex_to_rgb

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_API_KEY = "pk_test_pathfinder_51c0"
DEFAULT_PATH_COLOR = "#1f77b4"
MARKER_COLORS = {"start": "#2a9d8f", "end": "#e63946", "poi": "#f4a261"}
MAX_SIZE = 2048
MIN_SIZE = 64
MAX_POINTS = 5000
LANDMARK_PAGE_MAX = 10
RENDER_TEXT_KEY = "pathfinder:render"
_COLOR = re.compile(r"#[0-9a-fA-F]{6}")


class RequestProblem(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def load_scenario(source=None) -> dict:
    if source is None:
        return {}
    if isinstance(source, dict):
        return json.loads(json.dumps(source))
    return json.loads(Path(source).read_text(encoding="utf-8"))


def _position(value, where: str) -> list[float]:
    if (not isinstance(value, (list, tuple)) or len(value) != 2
            or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in value)):
        raise RequestProblem(400, f"{where} must be a [latitude, longitude] pair")
    lat, lon = float(value[0]), float(value[1])
    if not -90 <= lat <= 90:
        raise RequestProblem(400, f"{where}: latitude {lat} is out of range")
    if not -180 <= lon <= 180:
        raise RequestProblem(400, f"{where}: longitude {lon} is out of range")
    return [lat, lon]


def _color(value, default: str, where: str) -> str:
    if value is None:
        return default
    if not isinstance(value, str) or not _COLOR.fullmatch(value):
        raise RequestProblem(400, f"{where} must look like #rrggbb")
    return value.lower()


def normalize_render(body) -> dict:
    """Validate a render request and return the canonical description of the drawing."""
    if not isinstance(body, dict):
        raise RequestProblem(400, "body must be a JSON object")
    size = {}
    for key, default in (("width", 640), ("height", 480)):
        value = body.get(key, default)
        if not isinstance(value, int) or isinstance(value, bool) or not MIN_SIZE <= value <= MAX_SIZE:
            raise RequestProblem(400, f"{key} must be an integer between {MIN_SIZE} and {MAX_SIZE}")
        size[key] = value
    paths = body.get("paths")
    if not isinstance(paths, list) or not paths:
        raise RequestProblem(400, "paths must be a non-empty list")
    segments, total_points = [], 0
    for i, path in enumerate(paths):
        if not isinstance(path, dict):
            raise RequestProblem(400, f"paths[{i}] must be an object")
        points = path.get("points")
        if not isinstance(points, list) or len(points) < 2:
            raise RequestProblem(400, f"paths[{i}].points needs at least 2 positions")
        total_points += len(points)
        if total_points > MAX_POINTS:
            raise RequestProblem(413, f"at most {MAX_POINTS} positions per render")
        positions = [_position(p, f"paths[{i}].points[{j}]") for j, p in enumerate(points)]
        if "colors" in path and "color" in path:
            raise RequestProblem(400, f"paths[{i}]: use either color or colors")
        if "colors" in path:
            colors = path["colors"]
            if not isinstance(colors, list) or not colors:
                raise RequestProblem(400, f"paths[{i}].colors must be a non-empty list")
            colors = [_color(c, DEFAULT_PATH_COLOR, f"paths[{i}].colors[{k}]") for k, c in enumerate(colors)]
        else:
            colors = [_color(path.get("color"), DEFAULT_PATH_COLOR, f"paths[{i}].color")]
        width = path.get("width", 3)
        if not isinstance(width, int) or isinstance(width, bool) or not 1 <= width <= 9:
            raise RequestProblem(400, f"paths[{i}].width must be an integer between 1 and 9")
        for k in range(len(positions) - 1):
            segments.append({"from": positions[k], "to": positions[k + 1],
                             "color": colors[k % len(colors)], "width": width})
    markers = []
    raw_markers = body.get("markers", [])
    if not isinstance(raw_markers, list):
        raise RequestProblem(400, "markers must be a list")
    for i, marker in enumerate(raw_markers):
        if not isinstance(marker, dict):
            raise RequestProblem(400, f"markers[{i}] must be an object")
        kind = marker.get("kind", "poi")
        if kind not in MARKER_COLORS:
            raise RequestProblem(400, f"markers[{i}].kind must be one of start, end, poi")
        markers.append({"at": _position(marker.get("at"), f"markers[{i}].at"), "kind": kind,
                        "color": _color(marker.get("color"), MARKER_COLORS[kind], f"markers[{i}].color")})
    return {"width": size["width"], "height": size["height"], "segments": segments, "markers": markers}


def draw(drawn: dict) -> bytes:
    positions = [s["from"] for s in drawn["segments"]] + [s["to"] for s in drawn["segments"]]
    positions += [m["at"] for m in drawn["markers"]]
    canvas = Canvas(drawn["width"], drawn["height"])
    project = Projection(positions, drawn["width"], drawn["height"])
    for seg in drawn["segments"]:
        x0, y0 = project(*seg["from"])
        x1, y1 = project(*seg["to"])
        canvas.line(x0, y0, x1, y1, hex_to_rgb(seg["color"]), seg["width"])
    for marker in drawn["markers"]:
        canvas.marker(*project(*marker["at"]), hex_to_rgb(marker["color"]))
    text = json.dumps(drawn, sort_keys=True, separators=(",", ":"))
    return encode_png(drawn["width"], drawn["height"], bytes(canvas.pixels), {RENDER_TEXT_KEY: text})


class MapState:
    def __init__(self, scenario: dict):
        self.api_keys = set(scenario.get("api_keys", [DEFAULT_API_KEY]))
        if "landmarks" in scenario:
            self.landmarks = list(scenario["landmarks"])
        else:
            rel = scenario.get("landmarks_file", "data/landmarks.json")
            path = Path(rel) if Path(rel).is_absolute() else REPO_ROOT / rel
            self.landmarks = json.loads(path.read_text(encoding="utf-8"))
        self.faults = []
        for spec in scenario.get("faults", []):
            fault = dict(spec)
            fault["remaining"] = int(fault.get("times", 1))
            fault["seen"] = 0
            self.faults.append(fault)
        self.lock = threading.Lock()
        self.renders: list[dict] = []

    def take_fault(self, method: str, path: str, query: dict):
        with self.lock:
            for fault in self.faults:
                if fault["remaining"] <= 0:
                    continue
                if fault.get("method", "GET") != method or fault.get("path") != path:
                    continue
                if any(query.get(k) != str(v) for k, v in fault.get("query", {}).items()):
                    continue
                fault["seen"] += 1
                if fault["seen"] <= int(fault.get("after", 0)):
                    continue
                fault["remaining"] -= 1
                return fault
        return None

    def handle(self, method: str, path: str, query: dict, headers, body: bytes):
        """Return (status, content_type, payload bytes, extra headers)."""
        if path == "/v1/health":
            return self._json(200, {"status": "ok"})
        if headers.get("X-Api-Key", "") not in self.api_keys:
            return self._error(401, "authentication_error", "Missing or invalid X-Api-Key header.")
        fault = self.take_fault(method, path, query)
        if fault is not None:
            if fault.get("delay"):
                time.sleep(float(fault["delay"]))
            if fault.get("status"):
                return self._error(int(fault["status"]), "api_error",
                                   fault.get("message", "Temporary failure, please retry."))
        if path == "/v1/render":
            if method != "POST":
                return self._error(405, "invalid_request_error", "Use POST for /v1/render.")
            return self._render(headers, body)
        if path == "/v1/landmarks":
            if method != "GET":
                return self._error(405, "invalid_request_error", "Use GET for /v1/landmarks.")
            return self._landmarks(query)
        return self._error(404, "invalid_request_error", f"Unknown path {path}.")

    def _render(self, headers, body: bytes):
        ctype = headers.get("Content-Type", "").split(";")[0].strip().lower()
        if ctype != "application/json":
            return self._error(415, "invalid_request_error", "Content-Type must be application/json.")
        try:
            payload = json.loads(body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return self._error(400, "invalid_request_error", "Body is not valid JSON.")
        try:
            drawn = normalize_render(payload)
        except RequestProblem as exc:
            return self._error(exc.status, "invalid_request_error", exc.message)
        png = draw(drawn)
        digest = hashlib.sha256(png).hexdigest()
        render_id = "rnd_" + digest[:16]
        with self.lock:
            self.renders.append({"render_id": render_id, "request": payload, "drawn": drawn,
                                 "sha256": digest, "size": len(png)})
        return 200, "image/png", png, {"X-Render-Id": render_id}

    def _landmarks(self, query: dict):
        raw_limit = query.get("limit", str(LANDMARK_PAGE_MAX))
        try:
            limit = int(raw_limit)
        except ValueError:
            return self._error(400, "invalid_request_error", f"Invalid limit {raw_limit!r}.")
        if not 1 <= limit <= LANDMARK_PAGE_MAX:
            return self._error(400, "invalid_request_error",
                               f"limit must be between 1 and {LANDMARK_PAGE_MAX}.")
        offset = 0
        token = query.get("page_token")
        if token:
            if not re.fullmatch(r"lmp_[0-9]+", token) or int(token[4:]) > len(self.landmarks):
                return self._error(400, "invalid_request_error", "Invalid page_token.")
            offset = int(token[4:])
        page = self.landmarks[offset:offset + limit]
        nxt = offset + limit
        return self._json(200, {"data": page,
                                "next_page_token": f"lmp_{nxt}" if nxt < len(self.landmarks) else None})

    @staticmethod
    def _json(status: int, payload, extra=None):
        return status, "application/json", json.dumps(payload).encode("utf-8"), extra or {}

    def _error(self, status: int, kind: str, message: str):
        return self._json(status, {"error": {"type": kind, "message": message}})


class _Handler(BaseHTTPRequestHandler):
    server_version = "PathfinderMock/1.0"
    protocol_version = "HTTP/1.1"

    def _dispatch(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        parts = urlsplit(self.path)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        mock: MockMapServer = self.server.mock  # type: ignore[attr-defined]
        status, ctype, payload, extra = mock.state.handle(self.command, parts.path, query,
                                                          self.headers, body)
        mock.record(self.command, parts.path, parts.query, status)
        try:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(payload)))
            for key, value in extra.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            pass

    do_GET = _dispatch
    do_POST = _dispatch
    do_PUT = _dispatch
    do_DELETE = _dispatch

    def log_message(self, format, *args):
        return


class MockMapServer:
    def __init__(self, scenario=None, host: str = "127.0.0.1", port: int = 0,
                 quiet: bool = True, log_file: str | None = None):
        self.state = MapState(load_scenario(scenario))
        self.quiet = quiet
        self.log_file = log_file
        self.requests: list[dict] = []
        self._lock = threading.Lock()
        self._httpd = ThreadingHTTPServer((host, port), _Handler)
        self._httpd.daemon_threads = True
        self._httpd.mock = self  # type: ignore[attr-defined]
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        host, port = self._httpd.server_address[:2]
        return f"http://{host}:{port}"

    @property
    def renders(self) -> list[dict]:
        return self.state.renders

    def record(self, method: str, path: str, query: str, status: int) -> None:
        entry = {"method": method, "path": path, "query": query, "status": status}
        line = f"{method} {path}{'?' + query if query else ''} -> {status}"
        with self._lock:
            self.requests.append(entry)
            if self.log_file:
                with open(self.log_file, "a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
        if not self.quiet:
            print(line, flush=True)

    def start(self) -> "MockMapServer":
        self._thread = threading.Thread(
            target=self._httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True
        )
        self._thread.start()
        return self

    def serve_forever(self) -> None:
        self._httpd.serve_forever()

    def stop(self) -> None:
        if self._thread is not None:
            self._httpd.shutdown()
            self._thread.join(timeout=5)
            self._thread = None
        self._httpd.server_close()

    def __enter__(self) -> "MockMapServer":
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()


def start_server(scenario=None, port: int = 0, quiet: bool = True) -> MockMapServer:
    return MockMapServer(scenario, port=port, quiet=quiet).start()
