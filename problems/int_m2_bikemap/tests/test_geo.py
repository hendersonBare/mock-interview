import math

import pytest

from bikemap.geo import EARTH_RADIUS_M, bounding_box, haversine_m, valid_position


def test_zero_distance():
    assert haversine_m(52.37, 4.89, 52.37, 4.89) == 0.0


def test_one_degree_of_latitude():
    assert haversine_m(0.0, 0.0, 1.0, 0.0) == pytest.approx(math.pi * EARTH_RADIUS_M / 180)


def test_longitude_shrinks_with_latitude():
    at_equator = haversine_m(0.0, 0.0, 0.0, 1.0)
    at_sixty = haversine_m(60.0, 0.0, 60.0, 1.0)
    assert at_sixty == pytest.approx(at_equator / 2, rel=1e-3)


def test_symmetry():
    assert haversine_m(52.36, 4.88, 52.38, 4.91) == pytest.approx(haversine_m(52.38, 4.91, 52.36, 4.88))


def test_bounding_box():
    assert bounding_box([(52.0, 4.5), (51.5, 5.0), (52.2, 4.7)]) == (51.5, 4.5, 52.2, 5.0)
    with pytest.raises(ValueError):
        bounding_box([])


@pytest.mark.parametrize("lat,lon,ok", [(52.4, 4.9, True), (91, 0, False), (0, 181, False), (-90, -180, True)])
def test_valid_position(lat, lon, ok):
    assert valid_position(lat, lon) is ok
