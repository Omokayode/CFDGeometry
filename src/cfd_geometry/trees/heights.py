"""Assign tree heights from OSM columns and optional canopy rasters."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

from cfd_geometry.buildings.heights_osm import parse_height_string
from cfd_geometry.raster.elevation import get_elevation_at_point, load_elevation_raster

# Shapefile-safe export names in download/export.py map to these patterns
DEFAULT_TREE_HEIGHT_COLUMNS = (
    "height",
    "Height",
    "HEIGHT",
    "tree_height",
)


def resolve_tree_height_column(
    gdf: gpd.GeoDataFrame,
    height_col: str | None,
) -> str | None:
    if height_col:
        return height_col
    for name in DEFAULT_TREE_HEIGHT_COLUMNS:
        if name in gdf.columns:
            return name
    return None


def _height_from_row(row: pd.Series, col: str | None) -> float | None:
    if not col or col not in row.index or pd.isna(row[col]):
        return None
    return parse_height_string(row[col])


def _sample_canopy_raster(
    x: float,
    y: float,
    elevation_data: dict,
    *,
    buffer_m: float,
    min_height: float,
) -> float | None:
    """Sample canopy height at a point; optional cross pattern within buffer for max."""
    samples: list[float] = []
    if buffer_m <= 0:
        offsets = [(0.0, 0.0)]
    else:
        offsets = [
            (0.0, 0.0),
            (buffer_m, 0.0),
            (-buffer_m, 0.0),
            (0.0, buffer_m),
            (0.0, -buffer_m),
        ]
    for dx, dy in offsets:
        z = get_elevation_at_point(x + dx, y + dy, elevation_data)
        if z >= min_height and z < 200.0:
            samples.append(z)
    if not samples:
        return None
    return float(max(samples))


def assign_tree_heights(
    gdf: gpd.GeoDataFrame,
    *,
    canopy_raster: str | Path | None = None,
    default_height: float = 10.0,
    height_col: str | None = None,
    raster_buffer_m: float = 10.0,
    min_raster_height: float = 2.0,
) -> gpd.GeoDataFrame:
    """
    Set ``tree_height_m`` and ``tree_height_source`` on tree points.

    Priority: OSM height column → canopy GeoTIFF (point / buffer max) → default.
    """
    out = gdf.copy()
    col = resolve_tree_height_column(out, height_col)
    heights: list[float] = []
    sources: list[str] = []

    raster_data = None
    work = out
    if canopy_raster:
        raster_path = str(canopy_raster)
        crs = str(out.crs) if out.crs else "EPSG:4326"
        raster_data = load_elevation_raster(raster_path, crs, build_interpolator=True)
        if out.crs and str(out.crs) != str(raster_data.get("crs", out.crs)):
            work = out.to_crs(raster_data["crs"])

    for idx, row in work.iterrows():
        h: float | None = None
        src = "default"

        if col:
            h = _height_from_row(row, col)
            if h and h > 0:
                src = "osm"

        if h is None and raster_data is not None:
            geom = row.geometry
            if geom is not None and not geom.is_empty:
                h = _sample_canopy_raster(
                    geom.x,
                    geom.y,
                    raster_data,
                    buffer_m=raster_buffer_m,
                    min_height=min_raster_height,
                )
                if h is not None:
                    src = "raster"

        if h is None or h <= 0:
            h = default_height
            src = "default"

        heights.append(h)
        sources.append(src)

    out["tree_height_m"] = heights
    out["tree_height_source"] = sources

    counts = pd.Series(sources).value_counts()
    print("Tree height sources:")
    for name, n in counts.items():
        print(f"  {name}: {n}")
    reliable = int(counts.get("osm", 0) + counts.get("raster", 0))
    if len(out):
        print(f"  With OSM tag or canopy raster: {reliable} ({100 * reliable / len(out):.1f}%)")

    return out
