import json

import pytest

import requests
from bikemap.png import png_info
from mock_map import DEFAULT_API_KEY, MockMapServer
from mock_map.server import RENDER_TEXT_KEY

AUTH = {"X-Api-Key": DEFAULT_API_KEY}
SQUARE = [[10.0, 20.0], [10.0, 20.01], [10.01, 20.01]]


def render(server, body, headers=AUTH):
    return requests.post(server.url + "/v1/render", headers=headers, json=body, timeout=5)


def test_render_returns_png_and_id(map_server):
    resp = render(map_server, {"width": 200, "height": 100, "paths": [{"points": SQUARE}]})
    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == "image/png"
    info = png_info(resp.content)
    assert (info.width, info.height) == (200, 100)
    assert resp.headers["X-Render-Id"].startswith("rnd_")
    assert map_server.renders[-1]["render_id"] == resp.headers["X-Render-Id"]


def test_render_describes_drawing(map_server):
    resp = render(map_server, {"paths": [{"points": SQUARE, "color": "#AA0000"}],
                               "markers": [{"at": [10.0, 20.0], "kind": "poi"}]})
    drawn = json.loads(png_info(resp.content).text[RENDER_TEXT_KEY])
    assert drawn["width"] == 640 and drawn["height"] == 480
    assert [s["color"] for s in drawn["segments"]] == ["#aa0000", "#aa0000"]
    assert drawn["segments"][0]["from"] == [10.0, 20.0]
    assert drawn["markers"] == [{"at": [10.0, 20.0], "kind": "poi", "color": "#f4a261"}]
    assert drawn == map_server.renders[-1]["drawn"]


def test_render_is_deterministic(map_server):
    body = {"width": 120, "height": 90, "paths": [{"points": SQUARE}]}
    assert render(map_server, body).content == render(map_server, body).content


@pytest.mark.parametrize("body,status", [
    ({"paths": [{"points": [[95.0, 1.0], [1.0, 1.0]]}]}, 400),
    ({"paths": [{"points": [[1.0, 1.0]]}]}, 400),
    ({"paths": [{"points": SQUARE, "color": "red"}]}, 400),
    ({"width": 5000, "paths": [{"points": SQUARE}]}, 400),
    ({"paths": [{"points": SQUARE}], "markers": [{"at": [1, 1], "kind": "flag"}]}, 400),
])
def test_render_validation(map_server, body, status):
    assert render(map_server, body).status_code == status


def test_render_requires_json_content_type(map_server):
    resp = requests.post(map_server.url + "/v1/render", headers={**AUTH, "Content-Type": "text/plain"}, timeout=5)
    assert resp.status_code == 415


def test_render_requires_key(map_server):
    assert render(map_server, {"paths": [{"points": SQUARE}]}, headers={}).status_code == 401


def test_landmarks_first_page(map_server):
    resp = requests.get(map_server.url + "/v1/landmarks", headers=AUTH, timeout=5)
    page = resp.json()
    assert len(page["data"]) == 10
    assert page["next_page_token"]
    assert set(page["data"][0]) >= {"id", "name", "coordinates"}


def test_landmarks_limit_bounds(map_server):
    assert requests.get(map_server.url + "/v1/landmarks?limit=11", headers=AUTH, timeout=5).status_code == 400
    assert requests.get(map_server.url + "/v1/landmarks?page_token=zzz", headers=AUTH, timeout=5).status_code == 400


def test_requests_are_logged(map_server):
    requests.get(map_server.url + "/v1/landmarks?limit=3", headers=AUTH, timeout=5)
    assert map_server.requests[-1] == {"method": "GET", "path": "/v1/landmarks",
                                       "query": "limit=3", "status": 200}


def test_scenario_data_and_faults():
    scenario = {"landmarks": [{"id": "lm_1", "name": "x", "coordinates": [1.0, 2.0]}],
                "faults": [{"path": "/v1/landmarks", "status": 503, "times": 1}]}
    with MockMapServer(scenario) as server:
        url = server.url + "/v1/landmarks"
        assert requests.get(url, headers=AUTH, timeout=5).status_code == 503
        page = requests.get(url, headers=AUTH, timeout=5).json()
        assert page == {"data": scenario["landmarks"], "next_page_token": None}
