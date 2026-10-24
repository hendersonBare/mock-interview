"""Plain data types used across the package."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class TrackPoint:
    lat: float
    lon: float
    time: datetime | None = None
    ele: float | None = None


@dataclass
class Ride:
    name: str
    points: list[TrackPoint] = field(default_factory=list)


@dataclass(frozen=True)
class Landmark:
    id: str
    name: str
    lat: float
    lon: float
