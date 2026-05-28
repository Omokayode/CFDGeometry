"""Domain bounds helpers for OpenFOAM case generation."""

from __future__ import annotations


def padded_xy_bounds(
    bounds: dict[str, float],
    buffer_m: float,
) -> tuple[float, float, float, float]:
    """Return ``(x_min, x_max, y_min, y_max)`` with uniform padding."""
    return (
        bounds["x_min"] - buffer_m,
        bounds["x_max"] + buffer_m,
        bounds["y_min"] - buffer_m,
        bounds["y_max"] + buffer_m,
    )


def refinement_box_bounds(
    bounds: dict[str, float],
    *,
    max_building_height: float,
    buffer_m: float = 10.0,
    z_min: float | None = None,
    z_top_margin_m: float = 10.0,
) -> tuple[float, float, float, float, float, float]:
    """
    Tight refinement box around buildings (for snappyHexMesh).

    Horizontal padding ``buffer_m``; top at tallest building + ``z_top_margin_m``.
    """
    z0 = bounds["z_min"] if z_min is None else z_min
    z1 = max(max_building_height, bounds["z_max"]) + z_top_margin_m
    return (
        bounds["x_min"] - buffer_m,
        bounds["y_min"] - buffer_m,
        z0,
        bounds["x_max"] + buffer_m,
        bounds["y_max"] + buffer_m,
        z1,
    )


def suggest_inside_point(
    outer: dict[str, float],
    *,
    building_bounds: dict[str, float] | None = None,
) -> tuple[float, float, float]:
    """
    Point inside the block mesh but away from building footprints.

    Uses a corner of the outer box at mid-height; nudges XY if that overlaps
    the building bbox center.
    """
    ox0, ox1, oy0, oy1 = (
        outer["x_min"],
        outer["x_max"],
        outer["y_min"],
        outer["y_max"],
    )
    z = outer["z_min"] + 0.45 * (outer["z_max"] - outer["z_min"])
    x = ox0 + 0.05 * (ox1 - ox0)
    y = oy0 + 0.05 * (oy1 - oy0)
    if building_bounds:
        bc_x = 0.5 * (building_bounds["x_min"] + building_bounds["x_max"])
        bc_y = 0.5 * (building_bounds["y_min"] + building_bounds["y_max"])
        if building_bounds["x_min"] <= x <= building_bounds["x_max"]:
            x = ox0 + 0.92 * (ox1 - ox0)
        if building_bounds["y_min"] <= y <= building_bounds["y_max"]:
            y = oy0 + 0.92 * (oy1 - oy0)
        if abs(x - bc_x) < 0.15 * (ox1 - ox0):
            x = ox0 + 0.92 * (ox1 - ox0)
        if abs(y - bc_y) < 0.15 * (oy1 - oy0):
            y = oy0 + 0.92 * (oy1 - oy0)
    return (x, y, z)
