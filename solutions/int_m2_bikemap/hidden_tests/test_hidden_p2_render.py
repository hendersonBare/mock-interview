import pytest

from hidden_bike_support import (KEY, assert_same_positions, closed_port, latlon_points, load,
                                 png_size, posts, server, sha256)


def render(api, out, **kw):
    from bikemap.render import render_ride
    return render_ride(load(), out, base_url=api.url, api_key=kw.pop("key", KEY), **kw)


def test_render_saves_exact_bytes_and_returns_id(tmp_path):
    out = tmp_path / "ride.png"
    with server() as api:
        render_id = render(api, out)
        record = api.renders[-1]
    assert render_id == record["render_id"]
    assert sha256(out) == record["sha256"]
    assert png_size(out) == (640, 480)


def test_track_is_sent_latitude_first_as_one_path(tmp_path):
    with server() as api:
        render(api, tmp_path / "ride.png")
        drawn = api.renders[-1]["drawn"]
        assert len(posts(api)) == 1
    expected = latlon_points()
    segments = drawn["segments"]
    assert len(segments) == len(expected) - 1
    assert_same_positions([s["from"] for s in segments], expected[:-1])
    assert_same_positions([s["to"] for s in segments], expected[1:])
    assert {s["color"] for s in segments} == {"#1f77b4"}
    assert {s["width"] for s in segments} == {3}
    assert drawn["markers"] == []


def test_custom_size(tmp_path):
    out = tmp_path / "small.png"
    with server() as api:
        render(api, out, width=320, height=200)
        drawn = api.renders[-1]["drawn"]
    assert (drawn["width"], drawn["height"]) == (320, 200)
    assert png_size(out) == (320, 200)


def test_uses_the_given_key(tmp_path):
    with server({"api_keys": ["pk_test_someone_else"]}) as api:
        render(api, tmp_path / "ride.png", key="pk_test_someone_else")
        assert [r["status"] for r in posts(api)] == [200]


def test_auth_error_raises_and_writes_nothing(tmp_path):
    from bikemap.errors import ApiError
    out = tmp_path / "ride.png"
    with server() as api:
        with pytest.raises(ApiError) as info:
            render(api, out, key="pk_test_wrong")
    assert info.value.status == 401
    assert not out.exists()


def test_error_does_not_overwrite_existing_file(tmp_path):
    from bikemap.errors import ApiError
    out = tmp_path / "ride.png"
    out.write_bytes(b"previous")
    scenario = {"faults": [{"method": "POST", "path": "/v1/render", "status": 400, "times": 9}]}
    with server(scenario) as api:
        with pytest.raises(ApiError) as info:
            render(api, out)
    assert info.value.status == 400
    assert out.read_bytes() == b"previous"


def test_unreachable_api_raises_transport_error(tmp_path):
    from bikemap.errors import TransportError
    from bikemap.render import render_ride
    out = tmp_path / "ride.png"
    with pytest.raises(TransportError):
        render_ride(load(), out, base_url=f"http://127.0.0.1:{closed_port()}", api_key=KEY)
    assert not out.exists()
