import socket

import pytest

from bikemap import http
from bikemap.errors import ApiError, TransportError
from mock_map import DEFAULT_API_KEY


def test_get_json(map_server):
    resp = http.send("GET", map_server.url + "/v1/health")
    assert resp.ok and resp.json() == {"status": "ok"}
    assert resp.header("content-type") == "application/json"


def test_error_status_is_returned_not_raised(map_server):
    resp = http.send("GET", map_server.url + "/v1/landmarks")
    assert resp.status == 401
    with pytest.raises(ApiError) as info:
        resp.raise_for_status()
    assert info.value.status == 401
    assert "X-Api-Key" in info.value.message


def test_json_body_sets_content_type(map_server):
    resp = http.send("POST", map_server.url + "/v1/render", headers={"X-Api-Key": DEFAULT_API_KEY},
                     json_body={"paths": []})
    assert resp.status == 400
    assert "paths" in resp.json()["error"]["message"]


def test_transport_error_when_nothing_listens():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    with pytest.raises(TransportError):
        http.send("GET", f"http://127.0.0.1:{port}/v1/health", timeout=1)
