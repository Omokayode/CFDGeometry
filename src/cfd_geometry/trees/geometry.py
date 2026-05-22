"""Procedural tree trunk and canopy geometry."""

from __future__ import annotations

import numpy as np
from shapely.geometry import Point


def default_tree_config() -> dict:
    return {
        "canopy_shape": "cylinder",
        "trunk_height_ratio": 0.3,
        "canopy_radius_ratio": 0.4,
        "trunk_radius": 0.1,
        "detail_level": 12,
        "min_tree_height": 2.0,
        "max_tree_height": 25.0,
    }


def create_tree_canopy(
    point: Point,
    canopy_radius: float,
    trunk_height: float,
    canopy_height: float,
    trunk_radius: float,
    *,
    canopy_shape: str = "cylinder",
    sides: int = 8,
) -> list:
    """Build triangles for a simple trunk + canopy at a point."""
    x, y = point.x, point.y
    triangles = []
    angles = np.linspace(0, 2 * np.pi, sides + 1)[:-1]

    if trunk_height > 0 and trunk_radius > 0:
        trunk_bottom = [
            [x + trunk_radius * np.cos(a), y + trunk_radius * np.sin(a), 0]
            for a in angles
        ]
        trunk_top = [
            [x + trunk_radius * np.cos(a), y + trunk_radius * np.sin(a), trunk_height]
            for a in angles
        ]
        trunk_center_bottom = [x, y, 0]
        trunk_center_top = [x, y, trunk_height]
        for i in range(sides):
            n = (i + 1) % sides
            triangles.append([trunk_center_bottom, trunk_bottom[i], trunk_bottom[n]])
            triangles.append([trunk_center_top, trunk_top[n], trunk_top[i]])
            triangles.append([trunk_bottom[i], trunk_top[i], trunk_bottom[n]])
            triangles.append([trunk_bottom[n], trunk_top[i], trunk_top[n]])

    canopy_base_z = trunk_height
    canopy_top_z = trunk_height + canopy_height

    if canopy_shape == "cylinder":
        canopy_bottom = [
            [x + canopy_radius * np.cos(a), y + canopy_radius * np.sin(a), canopy_base_z]
            for a in angles
        ]
        canopy_top = [
            [x + canopy_radius * np.cos(a), y + canopy_radius * np.sin(a), canopy_top_z]
            for a in angles
        ]
        c_bot = [x, y, canopy_base_z]
        c_top = [x, y, canopy_top_z]
        for i in range(sides):
            n = (i + 1) % sides
            triangles.append([c_bot, canopy_bottom[i], canopy_bottom[n]])
            triangles.append([c_top, canopy_top[n], canopy_top[i]])
            triangles.append([canopy_bottom[i], canopy_bottom[n], canopy_top[i]])
            triangles.append([canopy_bottom[n], canopy_top[n], canopy_top[i]])

    elif canopy_shape == "sphere":
        lat_divs = max(2, sides // 2)
        lon_divs = sides
        z_offset = (canopy_base_z + canopy_top_z) / 2
        for lat_i in range(lat_divs):
            lat1 = np.pi * (-0.5 + lat_i / lat_divs)
            lat2 = np.pi * (-0.5 + (lat_i + 1) / lat_divs)
            for lon_i in range(lon_divs):
                lon1 = 2 * np.pi * lon_i / lon_divs
                lon2 = 2 * np.pi * (lon_i + 1) / lon_divs
                r = canopy_radius

                def sph(lat, lon):
                    return [
                        x + r * np.cos(lat) * np.cos(lon),
                        y + r * np.cos(lat) * np.sin(lon),
                        z_offset + r * np.sin(lat),
                    ]

                p1, p2 = sph(lat1, lon1), sph(lat2, lon1)
                p3, p4 = sph(lat2, lon2), sph(lat1, lon2)
                triangles.append([p1, p2, p3])
                triangles.append([p1, p3, p4])

    return triangles
