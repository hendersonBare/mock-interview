"""Small geodesy helpers (spherical Earth, see DOCS.md "Distances")."""
from __future__ import annotations

import math
from typing import Iterable

EARTH_RADIUS_M = 6_371_000.0


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres between two (latitude, longitude) positions in degrees."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))


def bounding_box(positions: Iterable[tuple[float, float]]) -> tuple[float, float, float, float]:
    """Return (min_lat, min_lon, max_lat, max_lon) for (lat, lon) pairs."""
    lats, lons = [], []
    for lat, lon in positions:
        lats.append(lat)
        lons.append(lon)
    if not lats:
        raise ValueError("no positions")
    return min(lats), min(lons), max(lats), max(lons)


def valid_position(lat: float, lon: float) -> bool:
    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0
