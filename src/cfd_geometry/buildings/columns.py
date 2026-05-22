"""Height / base column resolution (no strategy or load dependencies)."""

from __future__ import annotations

import geopandas as gpd

# Common height / base columns (VoxCity-style and OSM exports)
DEFAULT_HEIGHT_COLUMNS = (
    "height",
    "Height",
    "building_height",
    "estimated_height",
    "HEIGHT",
)
DEFAULT_MIN_HEIGHT_COLUMNS = ("min_height", "min_height_m", "base_height", "elevation")


def resolve_height_column(
    gdf: gpd.GeoDataFrame,
    height_col: str | None,
) -> str | None:
    """Pick an explicit height column when ``height_col`` is not set."""
    if height_col:
        return height_col
    for name in DEFAULT_HEIGHT_COLUMNS:
        if name in gdf.columns:
            return name
    return None


def resolve_min_height_column(
    gdf: gpd.GeoDataFrame,
    min_height_col: str | None,
) -> str | None:
    if min_height_col:
        return min_height_col
    for name in DEFAULT_MIN_HEIGHT_COLUMNS:
        if name in gdf.columns:
            return name
    return None
