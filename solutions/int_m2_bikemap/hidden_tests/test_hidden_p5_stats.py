import pytest

from hidden_bike_support import HERE, RIDE, haversine, write_ride

KEYS = {"points", "used_points", "skipped_points", "elapsed_s", "distance_m", "avg_speed_kmh",
        "max_speed_kmh"}


def stats(path):
    from bikemap.stats import ride_stats
    return ride_stats(path)


def test_clean_ride():
    result = stats(RIDE)
    assert set(result) == KEYS
    assert (result["points"], result["used_points"], result["skipped_points"]) == (49, 49, [])
    assert result["elapsed_s"] == 1251.0
    assert result["distance_m"] == pytest.approx(7518.0, abs=0.11)
    assert result["avg_speed_kmh"] == pytest.approx(21.63, abs=0.011)
    assert result["max_speed_kmh"] == pytest.approx(34.38, abs=0.011)


def test_ride_with_glitches():
    result = stats(HERE / "hidden_data" / "hidden_p5_rough_ride.geojson")
    assert result["points"] == 18
    assert result["skipped_points"] == [2, 4, 6, 7, 9, 13, 17]
    assert result["used_points"] == 11
    assert result["elapsed_s"] == 205.0
    assert result["distance_m"] == pytest.approx(1445.0, abs=0.11)
    assert result["avg_speed_kmh"] == pytest.approx(25.38, abs=0.011)
    assert result["max_speed_kmh"] == pytest.approx(28.5, abs=0.011)


def test_values_follow_the_definitions(tmp_path):
    coords = [[0.0, 0.0], [0.0, 0.01, 5.0], [0.0, 0.02], [0.0, 0.05]]
    times = ["2026-01-01T00:00:00Z", "2026-01-01T00:01:00Z", "2026-01-01T00:01:30.500Z",
             "2026-01-01T00:04:00Z"]
    result = stats(write_ride(tmp_path, coords, times))
    d = [haversine(0.0, 0.0, 0.01, 0.0), haversine(0.01, 0.0, 0.02, 0.0), haversine(0.02, 0.0, 0.05, 0.0)]
    dt = [60.0, 30.5, 149.5]
    assert result["elapsed_s"] == 240.0
    assert result["distance_m"] == pytest.approx(round(sum(d), 1), abs=0.11)
    assert result["avg_speed_kmh"] == pytest.approx(round(sum(d) / 240.0 * 3.6, 2), abs=0.011)
    assert result["max_speed_kmh"] == pytest.approx(
        round(max(x / t * 3.6 for x, t in zip(d, dt)), 2), abs=0.011)


def test_same_timestamp_pair_is_ignored_for_max_speed(tmp_path):
    coords = [[0.0, 0.0], [0.0, 0.001], [0.0, 0.002]]
    times = ["2026-01-01T00:00:00Z", "2026-01-01T00:01:00Z", "2026-01-01T00:01:00Z"]
    result = stats(write_ride(tmp_path, coords, times))
    assert result["skipped_points"] == []
    assert result["elapsed_s"] == 60.0
    assert result["max_speed_kmh"] == pytest.approx(round(haversine(0, 0, 0.001, 0) / 60 * 3.6, 2), abs=0.011)
    assert result["distance_m"] == pytest.approx(round(2 * haversine(0, 0, 0.001, 0), 1), abs=0.11)


@pytest.mark.parametrize("coord,stamp", [
    ([0.0, 0.03], None),
    ([0.0, 0.03], "2026-01-01T02:03:00+02:00"),
    ([0.0, 0.03], "2026-01-01 00:03:00"),
    ([0.0, 0.03], "2026-01-01T00:03:00"),
    ([0.0], "2026-01-01T00:03:00Z"),
    (["0.0", "0.03"], "2026-01-01T00:03:00Z"),
    ([0.0, 95.0], "2026-01-01T00:03:00Z"),
    ([0.0, 0.03, 1.0, 2.0], "2026-01-01T00:03:00Z"),
    (None, "2026-01-01T00:03:00Z"),
])
def test_unusable_point_is_skipped(tmp_path, coord, stamp):
    coords = [[0.0, 0.0], [0.0, 0.01], coord, [0.0, 0.02]]
    times = ["2026-01-01T00:00:00Z", "2026-01-01T00:01:00Z", stamp, "2026-01-01T00:02:00Z"]
    result = stats(write_ride(tmp_path, coords, times))
    assert result["skipped_points"] == [2]
    assert result["used_points"] == 3
    assert result["elapsed_s"] == 120.0
    assert result["distance_m"] == pytest.approx(round(haversine(0, 0, 0.02, 0), 1), abs=0.11)


def test_missing_trailing_times(tmp_path):
    coords = [[0.0, 0.0], [0.0, 0.01], [0.0, 0.02], [0.0, 0.03]]
    result = stats(write_ride(tmp_path, coords, ["2026-01-01T00:00:00Z", "2026-01-01T00:01:00Z"]))
    assert result["skipped_points"] == [2, 3]
    assert result["elapsed_s"] == 60.0


def test_too_few_usable_points(tmp_path):
    coords = [[0.0, 0.0], [0.0]]
    result = stats(write_ride(tmp_path, coords, ["2026-01-01T00:00:00Z", "2026-01-01T00:01:00Z"]))
    assert result == {"points": 2, "used_points": 1, "skipped_points": [1], "elapsed_s": 0.0,
                      "distance_m": 0.0, "avg_speed_kmh": 0.0, "max_speed_kmh": 0.0}
