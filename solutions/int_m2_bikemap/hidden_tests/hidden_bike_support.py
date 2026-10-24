"""Shared helpers for the acceptance tests (not collected by pytest)."""
import hashlib
import json
import math
import os
import socket
from pathlib import Path

WORKDIR = Path(os.environ.get("GRADE_WORKDIR", ".")).resolve()
HERE = Path(__file__).resolve().parent
KEY = "pk_test_pathfinder_51c0"
RIDE = WORKDIR / "data" / "ride_canal_loop.geojson"
EVEN, ODD = "#e4572e", "#2e86ab"


def server(scenario=None):
    from mock_map import MockMapServer
    return MockMapServer(scenario)


def raw_ride(path=RIDE):
    doc = json.loads(Path(path).read_text())
    feature = doc["features"][0]
    return feature["geometry"]["coordinates"], feature["properties"].get("times", [])


def latlon_points(path=RIDE):
    coords, _ = raw_ride(path)
    return [[c[1], c[0]] for c in coords]


def write_ride(tmp_path, coords, times, name="test ride", filename="ride.geojson"):
    doc = {"type": "FeatureCollection", "features": [{
        "type": "Feature", "properties": {"name": name, "times": times},
        "geometry": {"type": "LineString", "coordinates": coords}}]}
    path = Path(tmp_path) / filename
    path.write_text(json.dumps(doc))
    return path


def load(path=RIDE):
    from bikemap.ride import load_ride
    return load_ride(path)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def png_size(path):
    data = Path(path).read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def haversine(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin((p2 - p1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return 2 * 6371000.0 * math.asin(min(1.0, math.sqrt(a)))


def closed_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def posts(api):
    return [r for r in api.requests if r["method"] == "POST" and r["path"] == "/v1/render"]


def landmark_gets(api):
    return [r for r in api.requests if r["method"] == "GET" and r["path"] == "/v1/landmarks"]


def assert_same_positions(got, expected):
    assert len(got) == len(expected)
    for g, e in zip(got, expected):
        assert abs(g[0] - e[0]) < 1e-9 and abs(g[1] - e[1]) < 1e-9, (g, e)
