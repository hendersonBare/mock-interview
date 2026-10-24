"""Tiny software rasterizer used by the render endpoint."""
from __future__ import annotations

BACKGROUND = (246, 244, 238)
GRID = (226, 222, 212)


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


class Canvas:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.pixels = bytearray(bytes(BACKGROUND) * (width * height))
        for x in range(0, width, 64):
            for y in range(height):
                self.set(x, y, GRID)
        for y in range(0, height, 64):
            for x in range(width):
                self.set(x, y, GRID)

    def set(self, x: int, y: int, rgb: tuple[int, int, int]) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            i = (y * self.width + x) * 3
            self.pixels[i:i + 3] = bytes(rgb)

    def stamp(self, x: int, y: int, radius: int, rgb) -> None:
        r2 = radius * radius
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx * dx + dy * dy <= r2:
                    self.set(x + dx, y + dy, rgb)

    def line(self, x0: int, y0: int, x1: int, y1: int, rgb, width: int = 1) -> None:
        radius = max(0, (width - 1) // 2)
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.stamp(x0, y0, radius, rgb)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def marker(self, x: int, y: int, rgb) -> None:
        self.stamp(x, y, 8, (40, 40, 40))
        self.stamp(x, y, 6, rgb)


class Projection:
    """Linear lat/lon -> pixel mapping that fits all positions with a margin."""

    def __init__(self, positions, width: int, height: int, margin: int = 24):
        lats = [p[0] for p in positions]
        lons = [p[1] for p in positions]
        self.min_lat, self.max_lat = min(lats), max(lats)
        self.min_lon, self.max_lon = min(lons), max(lons)
        self.span_lat = max(self.max_lat - self.min_lat, 1e-6)
        self.span_lon = max(self.max_lon - self.min_lon, 1e-6)
        self.width, self.height, self.margin = width, height, margin

    def __call__(self, lat: float, lon: float) -> tuple[int, int]:
        usable_w = self.width - 1 - 2 * self.margin
        usable_h = self.height - 1 - 2 * self.margin
        x = self.margin + (lon - self.min_lon) / self.span_lon * usable_w
        y = self.margin + (self.max_lat - lat) / self.span_lat * usable_h
        return int(round(x)), int(round(y))
