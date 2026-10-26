import pytest

from hidden_bike_support import (EVEN, KEY, ODD, assert_same_positions, closed_port,
                                 latlon_points, load, posts, server, sha256, write_ride)


def render(api, out, ride=None, **kw):
    from bikemap.render import render_ride
    return render_ride(ride or load(), out, base_url=api.url, api_key=KEY, **kw)


def test_alternating_segment_colors(tmp_path):
    with server() as api:
        render(api, tmp_path / "a.png", annotate=True)
        drawn = api.renders[-1]["drawn"]
        assert len(posts(api)) == 1
    expected = latlon_points()
    segments = drawn["segments"]
    assert len(segments) == len(expected) - 1
    assert_same_positions([s["from"] for s in segments], expected[:-1])
    assert_same_positions([s["to"] for s in segments], expected[1:])
    assert [s["color"] for s in segments] == [EVEN if k % 2 == 0 else ODD for k in range(len(segments))]


def test_start_and_end_markers(tmp_path):
    with server() as api:
        render(api, tmp_path / "a.png", annotate=True)
        markers = api.renders[-1]["drawn"]["markers"]
    expected = latlon_points()
    assert len(markers) == 2
    by_kind = {m["kind"]: m for m in markers}
    assert set(by_kind) == {"start", "end"}
    assert_same_positions([by_kind["start"]["at"], by_kind["end"]["at"]], [expected[0], expected[-1]])
    assert by_kind["start"]["color"] == "#2a9d8f"
    assert by_kind["end"]["color"] == "#e63946"


def test_two_point_ride(tmp_path):
    path = write_ride(tmp_path, [[4.9, 52.37], [4.91, 52.38]],
                      ["2026-01-01T00:00:00Z", "2026-01-01T00:01:00Z"])
    with server() as api:
        render(api, tmp_path / "a.png", ride=load(path), annotate=True)
        drawn = api.renders[-1]["drawn"]
    assert [(s["from"], s["to"], s["color"]) for s in drawn["segments"]] == [
        ([52.37, 4.9], [52.38, 4.91], EVEN)]


@pytest.mark.parametrize("statuses", [[503], [500, 502], [504]])
def test_busy_renderer_is_retried(tmp_path, statuses):
    faults = [{"method": "POST", "path": "/v1/render", "status": s, "times": 1} for s in statuses]
    out = tmp_path / "r.png"
    with server({"faults": faults}) as api:
        render_id = render(api, out, annotate=True)
        assert [r["status"] for r in posts(api)] == statuses + [200]
        assert render_id == api.renders[-1]["render_id"]
        assert sha256(out) == api.renders[-1]["sha256"]


def test_gives_up_after_three_attempts(tmp_path):
    from bikemap.errors import ApiError
    out = tmp_path / "r.png"
    scenario = {"faults": [{"method": "POST", "path": "/v1/render", "status": 503, "times": 50}]}
    with server(scenario) as api:
        with pytest.raises(ApiError) as info:
            render(api, out)
        assert len(posts(api)) == 3
    assert info.value.status == 503
    assert not out.exists()


def test_client_errors_are_not_retried(tmp_path):
    from bikemap.errors import ApiError
    scenario = {"faults": [{"method": "POST", "path": "/v1/render", "status": 400, "times": 50}]}
    with server(scenario) as api:
        with pytest.raises(ApiError):
            render(api, tmp_path / "r.png", annotate=True)
        assert len(posts(api)) == 1


def test_unreachable_api(tmp_path):
    from bikemap.errors import BikemapError
    from bikemap.render import render_ride
    with pytest.raises(BikemapError):
        render_ride(load(), tmp_path / "r.png", base_url=f"http://127.0.0.1:{closed_port()}",
                    api_key=KEY, annotate=True)
    assert not (tmp_path / "r.png").exists()
