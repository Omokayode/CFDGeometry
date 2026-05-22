"""Highway centerline to 3D mesh geometry."""

from __future__ import annotations

import numpy as np


def default_highway_config() -> dict[str, dict[str, float]]:
    return {
        "highway": {"width": 12.0, "height": 0.3, "padding": 1.0},
        "primary": {"width": 10.0, "height": 0.25, "padding": 0.8},
        "secondary": {"width": 8.0, "height": 0.2, "padding": 0.6},
        "tertiary": {"width": 6.0, "height": 0.15, "padding": 0.5},
        "residential": {"width": 5.0, "height": 0.1, "padding": 0.3},
        "service": {"width": 3.0, "height": 0.08, "padding": 0.2},
        "path": {"width": 2.0, "height": 0.05, "padding": 0.1},
        "trunk": {"width": 14.0, "height": 0.35, "padding": 1.2},
        "motorway": {"width": 16.0, "height": 0.4, "padding": 1.5},
        "default": {"width": 4.0, "height": 0.1, "padding": 0.3},
    }


def create_highway_geometry(
    line_coords: list,
    width: float,
    height: float,
    padding: float = 0.5,
) -> list:
    """Build a solid road prism from a 2D centerline."""
    triangles: list = []
    total_width = width + 2 * padding

    if len(line_coords) < 2:
        return triangles

    left_coords = []
    right_coords = []

    for i, (x, y) in enumerate(line_coords):
        if i == 0:
            dx = line_coords[i + 1][0] - x
            dy = line_coords[i + 1][1] - y
        elif i == len(line_coords) - 1:
            dx = x - line_coords[i - 1][0]
            dy = y - line_coords[i - 1][1]
        else:
            dx = (x - line_coords[i - 1][0] + line_coords[i + 1][0] - x) / 2
            dy = (y - line_coords[i - 1][1] + line_coords[i + 1][1] - y) / 2

        length = np.hypot(dx, dy)
        if length > 0:
            dx /= length
            dy /= length

        perp_x, perp_y = -dy, dx
        half = total_width / 2
        left_coords.append([x + perp_x * half, y + perp_y * half, height])
        right_coords.append([x - perp_x * half, y - perp_y * half, height])

    for i in range(len(line_coords) - 1):
        p1, p2, p3, p4 = left_coords[i], right_coords[i], left_coords[i + 1], right_coords[i + 1]
        triangles.append([p1, p3, p2])
        triangles.append([p2, p3, p4])

    bottom_left = [[c[0], c[1], 0] for c in left_coords]
    bottom_right = [[c[0], c[1], 0] for c in right_coords]

    for i in range(len(line_coords) - 1):
        p1, p2, p3, p4 = bottom_left[i], bottom_right[i], bottom_left[i + 1], bottom_right[i + 1]
        triangles.append([p1, p2, p3])
        triangles.append([p2, p4, p3])

    for i in range(len(line_coords) - 1):
        tl1, tl2 = left_coords[i], left_coords[i + 1]
        bl1, bl2 = bottom_left[i], bottom_left[i + 1]
        triangles.append([bl1, tl1, bl2])
        triangles.append([bl2, tl1, tl2])

        tr1, tr2 = right_coords[i], right_coords[i + 1]
        br1, br2 = bottom_right[i], bottom_right[i + 1]
        triangles.append([br1, br2, tr1])
        triangles.append([br2, tr2, tr1])

    if len(line_coords) >= 2:
        triangles.append([bottom_left[0], left_coords[0], bottom_right[0]])
        triangles.append([bottom_right[0], left_coords[0], right_coords[0]])
        triangles.append([bottom_left[-1], bottom_right[-1], left_coords[-1]])
        triangles.append([bottom_right[-1], right_coords[-1], left_coords[-1]])

    return triangles
