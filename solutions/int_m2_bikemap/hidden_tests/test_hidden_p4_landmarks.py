import json

import pytest

from hidden_bike_support import (HERE, KEY, WORKDIR, haversine, landmark_gets, load, server,
                                 write_ride)

KEYS = {"point_index", "landmark_id", "landmark_name", "distance_m"}


def nearest(api, ride=None, **kw):
    from bikemap.landmarks import nearest_landmarks
    return nearest_landmarks(ride or load(), base_url=api.url, api_key=kw.pop("key", KEY), **kw)


def one_point_ride(tmp_path, lat, lon):
    return load(write_ride(tmp_path, [[lon, lat]], ["2026-01-01T00:00:00Z"]))


def expected_rows(landmarks, ride):
    rows = []
    for i, p in enumerate(ride.points):
        best = min(((haversine(p.lat, p.lon, lm["coordinates"][0], lm["coordinates"][1]), lm["id"], lm["name"])
                    for lm in landmarks))
        rows.append((i, best[1], best[2], best[0]))
    return rows


def check(rows, expected):
    assert len(rows) == len(expected)
    for row, (i, lid, name, dist) in zip(rows, expected):
        assert set(row) == KEYS
        assert (row["point_index"], row["landmark_id"], row["landmark_name"]) == (i, lid, name)
        assert row["distance_m"] == pytest.approx(round(dist, 1), abs=0.11)


def test_default_data():
    landmarks = json.loads((WORKDIR / "data" / "landmarks.json").read_text())
    with server() as api:
        rows = nearest(api)
    check(rows, expected_rows(landmarks, load()))
    assert (rows[0]["landmark_id"], rows[0]["distance_m"]) == ("lm_013", 190.0)
    assert (rows[5]["landmark_id"], rows[5]["distance_m"]) == ("lm_001", 410.8)


def test_landmark_coordinates_are_latitude_first(tmp_path):
    scenario = {"landmarks": [{"id": "lm_1", "name": "Right", "coordinates": [10.0, 20.003]},
                              {"id": "lm_2", "name": "Swapped", "coordinates": [20.0, 10.0]}]}
    with server(scenario) as api:
        (row,) = nearest(api, one_point_ride(tmp_path, 10.0, 20.0))
    assert row["landmark_id"] == "lm_1"
    assert row["distance_m"] == pytest.approx(round(haversine(10.0, 20.0, 10.0, 20.003), 1), abs=0.11)


def test_equal_distance_goes_to_lowest_id(tmp_path):
    scenario = {"landmarks": [{"id": "lm_9", "name": "East", "coordinates": [10.0, 20.01]},
                              {"id": "lm_3", "name": "West", "coordinates": [10.0, 19.99]},
                              {"id": "lm_7", "name": "Far", "coordinates": [10.5, 20.0]}]}
    with server(scenario) as api:
        (row,) = nearest(api, one_point_ride(tmp_path, 10.0, 20.0))
    assert (row["landmark_id"], row["landmark_name"]) == ("lm_3", "West")


def test_reads_every_page(tmp_path):
    far = [{"id": f"lm_{n:03d}", "name": f"Far {n}", "coordinates": [10.0 + n / 100, 21.0]}
           for n in range(24)]
    near = {"id": "lm_900", "name": "Close", "coordinates": [10.0001, 20.0001]}
    with server({"landmarks": far + [near]}) as api:
        (row,) = nearest(api, one_point_ride(tmp_path, 10.0, 20.0))
        assert len(landmark_gets(api)) >= 3
    assert row["landmark_id"] == "lm_900"


def test_unusable_records_are_skipped(tmp_path):
    scenario = {"landmarks": [
        {"id": "lm_1", "name": "Only one value", "coordinates": [10.0]},
        {"id": "lm_2", "name": "No coordinates", "coordinates": None},
        {"id": "lm_3", "name": "Strings", "coordinates": ["10.0", "20.0"]},
        {"id": "lm_4", "name": "Out of range", "coordinates": [10.0, 200.0]},
        {"id": "lm_5", "name": "Three values", "coordinates": [10.0, 20.0, 1.0]},
        {"id": "", "name": "No id", "coordinates": [10.0, 20.0]},
        {"id": "lm_6", "coordinates": [10.0, 20.0]},
        {"id": "lm_8", "name": "Valid", "coordinates": [10.01, 20.0]},
    ]}
    with server(scenario) as api:
        (row,) = nearest(api, one_point_ride(tmp_path, 10.0, 20.0))
    assert row["landmark_id"] == "lm_8"


def test_failed_page_and_timeout_are_retried():
    landmarks = json.loads((HERE / "hidden_data" / "hidden_p4_landmarks.json").read_text())
    scenario = {"landmarks": landmarks, "faults": [
        {"path": "/v1/landmarks", "delay": 1.2, "times": 1},
        {"path": "/v1/landmarks", "after": 2, "status": 500, "times": 2},
    ]}
    usable = [lm for lm in landmarks if lm["id"] in {f"lm_{n:03d}" for n in range(1, 31)}]
    with server(scenario) as api:
        rows = nearest(api, timeout=0.5)
        assert any(r["status"] == 500 for r in landmark_gets(api))
    check(rows, expected_rows(usable, load()))


def test_gives_up_after_three_attempts():
    from bikemap.errors import BikemapError
    scenario = {"faults": [{"path": "/v1/landmarks", "status": 503, "times": 50}]}
    with server(scenario) as api:
        with pytest.raises(BikemapError):
            nearest(api)
        assert len(landmark_gets(api)) == 3


def test_client_errors_are_not_retried():
    from bikemap.errors import BikemapError
    with server() as api:
        with pytest.raises(BikemapError):
            nearest(api, key="pk_test_wrong")
        assert len(landmark_gets(api)) == 1


def test_export_landmarks_csv(tmp_path):
    from bikemap.landmarks import export_landmarks
    out = tmp_path / "near.csv"
    with server() as api:
        assert export_landmarks(load(), out, base_url=api.url, api_key=KEY) is None
        rows = nearest(api)
    lines = out.read_text().split("\n")
    assert lines[0] == "point_index,lat,lon,landmark_id,landmark_name,distance_m"
    assert lines[1] == "0,52.379185,4.900061,lm_013,Windmill replica,190.0"
    assert lines[-1] == ""
    assert len(lines) == 51
    ride = load()
    for line, row, point in zip(lines[1:-1], rows, ride.points):
        assert line == (f"{row['point_index']},{point.lat:.6f},{point.lon:.6f},"
                        f"{row['landmark_id']},{row['landmark_name']},{row['distance_m']:.1f}")
