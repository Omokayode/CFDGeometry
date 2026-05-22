"""Bounding box helpers for download queries."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Bbox:
    """WGS84 bounds: west, south, east, north (degrees)."""

    west: float
    south: float
    east: float
    north: float

    def as_osmnx_tuple(self) -> tuple[float, float, float, float]:
        """Return ``(left, bottom, right, top)`` for OSMnx bbox queries."""
        return (self.west, self.south, self.east, self.north)

    def validate(self) -> None:
        if self.west >= self.east:
            raise ValueError(f"west ({self.west}) must be < east ({self.east})")
        if self.south >= self.north:
            raise ValueError(f"south ({self.south}) must be < north ({self.north})")


def bbox_from_sequence(values: tuple[float, float, float, float]) -> Bbox:
    """Parse ``west south east north`` from CLI."""
    west, south, east, north = values
    box = Bbox(west=west, south=south, east=east, north=north)
    box.validate()
    return box
