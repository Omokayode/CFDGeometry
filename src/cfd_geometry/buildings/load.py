"""Load and prepare building footprint GeoDataFrames."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

from cfd_geometry.buildings.heights import _height_from_area
from cfd_geometry.buildings.heights_osm import apply_osm_heights_to_gdf
from cfd_geometry.geo.crs import fix_shapefile_crs, resolve_target_crs

HeightSource = str  # "osm" | "area" | "column" | "none"


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
        if not height_col:
            raise ValueError("height_col is required when height_source='column'")
        return gdf, height_col

    if height_col:
        return gdf, height_col
    return gdf, ""


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

    resolved = resolve_target_crs(gdf, target_crs, auto_utm=auto_utm)
    if gdf.crs is None or gdf.crs.to_string() != resolved:
        print(f"Reprojecting to {resolved}")
        gdf = gdf.to_crs(resolved)

    gdf, active_col = assign_building_heights(
        gdf,
        height_source=height_source,
        height_col=height_col,
        default_height=default_height,
    )
    return gdf, resolved, active_col


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
