"""Exception types shared by the bikemap package."""
from __future__ import annotations


class BikemapError(Exception):
    """Base class for every error raised by this package."""


class TransportError(BikemapError):
    """No HTTP response arrived (connection refused or reset, timeout)."""


class ApiError(BikemapError):
    """The API answered with an error status."""

    def __init__(self, status: int, message: str = ""):
        self.status = status
        self.message = message
        super().__init__(f"HTTP {status}: {message}" if message else f"HTTP {status}")
