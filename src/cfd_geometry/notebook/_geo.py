"""Geocoding helpers for notebook map initial views."""

from __future__ import annotations


def resolve_map_center(
    *,
    center: tuple[float, float] | None = None,
    place: str | None = None,
    default: tuple[float, float] = (43.0389, -87.9065),
) -> tuple[float, float]:
    """
    Return ``(lat, lon)`` for an ipyleaflet map center.

    ``center`` is ``(lat, lon)``. If ``place`` is set, geocode when OSMnx is installed.
    """
    if center is not None:
        lat, lon = center
        return float(lat), float(lon)

    if place:
        try:
            import osmnx as ox

            point = ox.geocode(place)
            # OSMnx: (latitude, longitude)
            return float(point[0]), float(point[1])
        except Exception:
            pass

    return default
