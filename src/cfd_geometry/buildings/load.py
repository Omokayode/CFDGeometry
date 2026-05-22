"""Load and prepare building footprint GeoDataFrames."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

from cfd_geometry.buildings.heights import _height_from_area
from cfd_geometry.buildings.heights_osm import apply_osm_heights_to_gdf
from cfd_geometry.geo.crs import fix_shapefile_crs, resolve_target_crs

HeightSource = str  # "osm" | "area" | "column" | "none"

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


def assign_building_heights(
    gdf: gpd.GeoDataFrame,
    *,
    height_source: HeightSource = "osm",
    height_col: str | None = None,
    default_height: float = 9.0,
) -> tuple[gpd.GeoDataFrame, str]:
    """
    Assign heights on ``gdf`` and return (gdf, active_height_column).

    ``height_source``:
    - ``osm``: OSM attribute rules
    - ``area``: footprint-area tiers
    - ``column``: use existing ``height_col`` column
    - ``none``: use ``default_height`` unless ``height_col`` is set
    """
    if height_source == "osm":
        return apply_osm_heights_to_gdf(gdf, default_height=default_height), "estimated_height"

    if height_source == "area":
        out = gdf.copy()
        out["area_sqm"] = out.geometry.area
        out["estimated_height"] = out["area_sqm"].apply(_height_from_area)
        return out, "estimated_height"

    if height_source == "column":
        resolved = resolve_height_column(gdf, height_col)
        if not resolved:
            raise ValueError(
                "height_source='column' requires a height column "
                f"(tried {DEFAULT_HEIGHT_COLUMNS})"
            )
        return gdf, resolved

    if height_col:
        return gdf, height_col
    return gdf, ""


def prepare_buildings_gdf(
    gdf: gpd.GeoDataFrame,
    *,
    target_crs: str | None = None,
    auto_utm: bool = True,
    height_source: HeightSource = "osm",
    height_col: str | None = None,
    default_height: float = 9.0,
    source_label: str = "GeoDataFrame",
) -> tuple[gpd.GeoDataFrame, str, str]:
    """
    Prepare an in-memory building footprint table for extrusion.

    Use this after QGIS/notebook edits instead of writing a temporary shapefile.
    Supports VoxCity-style columns such as ``height``, ``min_height``, and ``id``
    (``id`` is preserved; extrusion uses geometry + height columns).

    Returns (gdf, target_crs_used, active_height_column).
    """
    if not isinstance(gdf, gpd.GeoDataFrame):
        raise TypeError("gdf must be a geopandas.GeoDataFrame")
    if gdf.empty:
        raise ValueError("Building GeoDataFrame is empty")

    print(f"Preparing buildings from {source_label} ({len(gdf)} features)")
    gdf = gdf.copy()

    resolved = resolve_target_crs(gdf, target_crs, auto_utm=auto_utm)
    if gdf.crs is None:
        raise ValueError(
            "Building GeoDataFrame has no CRS. Set gdf.crs or pass target_crs= with auto_utm=False."
        )
    if gdf.crs.to_string() != resolved:
        print(f"Reprojecting to {resolved}")
        gdf = gdf.to_crs(resolved)

    gdf, active_col = assign_building_heights(
        gdf,
        height_source=height_source,
        height_col=height_col,
        default_height=default_height,
    )
    return gdf, resolved, active_col


def load_buildings_gdf(
    shapefile: str | Path,
    *,
    target_crs: str | None = None,
    auto_utm: bool = True,
    height_source: HeightSource = "osm",
    height_col: str | None = None,
    default_height: float = 9.0,
) -> tuple[gpd.GeoDataFrame, str, str]:
    """
    Read a shapefile, resolve CRS, reproject, and assign heights.

    Returns (gdf, target_crs_used, active_height_column).
    """
    shapefile = str(shapefile)
    print(f"Reading shapefile: {shapefile}")

    gdf = gpd.read_file(shapefile)
    if gdf.crs is None:
        gdf = fix_shapefile_crs(shapefile, write_back=False)

    return prepare_buildings_gdf(
        gdf,
        target_crs=target_crs,
        auto_utm=auto_utm,
        height_source=height_source,
        height_col=height_col,
        default_height=default_height,
        source_label=shapefile,
    )


def height_for_row(
    row: pd.Series,
    *,
    height_col: str,
    default_height: float,
) -> float:
    """Resolve extrusion height for one building row."""
    if height_col and height_col in row.index and pd.notna(row[height_col]):
        try:
            height = float(row[height_col])
            if height > 0:
                return height
        except (ValueError, TypeError):
            pass
    return default_height


def min_height_for_row(
    row: pd.Series,
    *,
    min_height_col: str | None,
    default_ground: float,
) -> float:
    """Per-footprint base Z when a ``min_height`` (or similar) column is present."""
    if min_height_col and min_height_col in row.index and pd.notna(row[min_height_col]):
        try:
            return float(row[min_height_col])
        except (ValueError, TypeError):
            pass
    return default_ground
