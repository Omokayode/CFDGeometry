"""Load and prepare building footprint GeoDataFrames."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

from cfd_geometry.buildings.columns import (
    DEFAULT_HEIGHT_COLUMNS,
    DEFAULT_MIN_HEIGHT_COLUMNS,
    resolve_height_column,
    resolve_min_height_column,
)
from cfd_geometry.buildings.geometry_prep import repair_building_geometries, warn_if_areas_look_like_degrees
from cfd_geometry.buildings.overlaps import resolve_overlapping_footprints
from cfd_geometry.geo.crs import fix_shapefile_crs, resolve_target_crs
from cfd_geometry.sources.base import HeightAssignOptions, HeightSourceStrategy

HeightSource = str  # "osm" | "area" | "column" | "none" | "raster" | "composite" | "default"


def assign_building_heights(
    gdf: gpd.GeoDataFrame,
    *,
    height_source: HeightSource = "osm",
    height_col: str | None = None,
    default_height: float = 9.0,
    height_strategy: HeightSourceStrategy | None = None,
    height_options: HeightAssignOptions | None = None,
    complement_raster: str | None = None,
) -> tuple[gpd.GeoDataFrame, str]:
    """
    Assign heights on ``gdf`` and return (gdf, active_height_column).

    Pass ``height_strategy`` for explicit control, or ``height_source`` name for CLI compat.
    Use ``height_source='composite'`` for column → OSM → area → raster/GDF complement.
    """
    if height_strategy is not None:
        return height_strategy.apply(gdf)

    from cfd_geometry.sources.height import height_source_from_name

    opts = height_options or HeightAssignOptions(
        default_height=default_height,
        height_col=height_col,
        complement_raster=complement_raster,
    )
    strategy = height_source_from_name(
        height_source,
        options=opts,
        height_col=height_col,
        default_height=default_height,
        raster_path=complement_raster if height_source == "raster" else None,
    )
    return strategy.apply(gdf)


def prepare_buildings_gdf(
    gdf: gpd.GeoDataFrame,
    *,
    target_crs: str | None = None,
    auto_utm: bool = True,
    height_source: HeightSource = "osm",
    height_col: str | None = None,
    default_height: float = 9.0,
    source_label: str = "GeoDataFrame",
    repair_geometry: bool = True,
    simplify_tolerance: float | None = None,
    resolve_overlaps: str | bool = False,
    overlap_ratio_threshold: float = 0.5,
    complement_raster: str | Path | None = None,
    complement_gdf: gpd.GeoDataFrame | None = None,
    height_strategy: HeightSourceStrategy | None = None,
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

    warn_if_areas_look_like_degrees(gdf)

    if repair_geometry:
        gdf, _ = repair_building_geometries(
            gdf, simplify_tolerance=simplify_tolerance
        )

    if resolve_overlaps:
        method = "fast" if resolve_overlaps is True else str(resolve_overlaps)
        gdf, _ = resolve_overlapping_footprints(
            gdf,
            method=method,
            overlap_ratio_threshold=overlap_ratio_threshold,
        )

    height_options = HeightAssignOptions(
        default_height=default_height,
        height_col=height_col,
        complement_raster=str(complement_raster) if complement_raster else None,
        complement_gdf=complement_gdf,
        overlap_ratio_threshold=overlap_ratio_threshold,
    )

    gdf, active_col = assign_building_heights(
        gdf,
        height_source=height_source,
        height_col=height_col,
        default_height=default_height,
        height_strategy=height_strategy,
        height_options=height_options,
        complement_raster=str(complement_raster) if complement_raster else None,
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
    repair_geometry: bool = True,
    resolve_overlaps: str | bool = False,
    complement_raster: str | Path | None = None,
    **prepare_kwargs,
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
        repair_geometry=repair_geometry,
        resolve_overlaps=resolve_overlaps,
        complement_raster=complement_raster,
        **prepare_kwargs,
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
