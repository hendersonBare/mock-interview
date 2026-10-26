from datetime import datetime, timezone

from hidden_bike_support import RIDE, load, raw_ride, write_ride


def test_first_point_is_latitude_longitude():
    ride = load()
    p = ride.points[0]
    assert (p.lat, p.lon) == (52.379185, 4.900061)
    assert p.ele == 2.9
    assert p.time == datetime(2026, 5, 3, 7, 42, 10, tzinfo=timezone.utc)


def test_every_point_matches_file():
    ride = load()
    coords, times = raw_ride()
    assert ride.name == "Canal loop"
    assert len(ride.points) == len(coords) == 49
    for point, position in zip(ride.points, coords):
        assert (point.lat, point.lon) == (position[1], position[0])
        assert point.ele == (position[2] if len(position) > 2 else None)


def test_missing_elevation_and_fractional_time():
    ride = load()
    assert ride.points[4].ele is None
    assert ride.points[7].time == datetime(2026, 5, 3, 7, 45, 34, 500000, tzinfo=timezone.utc)
    assert all(p.time.tzinfo is not None for p in ride.points)


def test_null_time_becomes_none(tmp_path):
    path = write_ride(tmp_path, [[-0.12, 51.5, 10.0], [-0.11, 51.505]],
                      ["2026-01-01T08:00:00Z", None], name="Two points")
    ride = load(path)
    assert ride.name == "Two points"
    assert ride.points[1].time is None
    assert (ride.points[1].lat, ride.points[1].lon, ride.points[1].ele) == (51.505, -0.11, None)


def summary_of(path):
    from bikemap.ride import summary
    return summary(load(path))


def test_summary():
    assert summary_of(RIDE).split("\n") == [
        "name: Canal loop",
        "points: 49",
        "start: 52.379185,4.900061",
        "end: 52.379560,4.899680",
        "bbox: 52.358036,4.877936,52.379560,4.915433",
    ]


def test_summary_spec_example(tmp_path):
    path = write_ride(tmp_path, [[-0.12, 51.5], [-0.11, 51.505, 3.0], [-0.1, 51.51]],
                      ["2026-01-01T08:00:00Z", "2026-01-01T08:01:00Z", "2026-01-01T08:02:00Z"],
                      name="Morning spin")
    assert summary_of(path).split("\n") == [
        "name: Morning spin",
        "points: 3",
        "start: 51.500000,-0.120000",
        "end: 51.510000,-0.100000",
        "bbox: 51.500000,-0.120000,51.510000,-0.100000",
    ]


def test_bbox_uses_extremes_not_endpoints(tmp_path):
    path = write_ride(tmp_path, [[5.0, 50.0], [6.5, 49.0], [4.0, 51.25], [5.5, 50.5]],
                      ["2026-01-01T08:00:00Z"] * 4, name="Zigzag")
    lines = summary_of(path).split("\n")
    assert len(lines) == 5
    assert lines[-1] == "bbox: 49.000000,4.000000,51.250000,6.500000"
