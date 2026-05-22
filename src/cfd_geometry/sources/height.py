"""Height assignment strategies for building footprints."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from cfd_geometry.buildings.heights import _height_from_area
from cfd_geometry.buildings.heights_osm import apply_osm_heights_to_gdf
from cfd_geometry.buildings.columns import resolve_height_column
from cfd_geometry.sources.base import HeightAssignOptions, HeightSourceStrategy


@dataclass
class OsmHeightSource:
    """OSM attribute rules (height, levels, building type)."""

    default_height: float = 9.0
    name: str = "osm"

    def apply(self, gdf: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, str]:
        out = apply_osm_heights_to_gdf(gdf, default_height=self.default_height)
        return out, "estimated_height"


@dataclass
class AreaHeightSource:
    """Tiered heights from footprint area (m²)."""

    name: str = "area"

    def apply(self, gdf: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, str]:
        out = gdf.copy()
        out["area_sqm"] = out.geometry.area
        out["estimated_height"] = out["area_sqm"].apply(_height_from_area)
        out["height_source"] = "area"
        return out, "estimated_height"


@dataclass
class ColumnHeightSource:
    """Use an existing height column on the GeoDataFrame."""

    height_col: str | None = None
    default_height: float = 9.0
    name: str = "column"

    def apply(self, gdf: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, str]:
        col = resolve_height_column(gdf, self.height_col)
        if not col:
            raise ValueError(
                "column height source requires a height field "
                "(e.g. height, estimated_height)"
            )
        out = gdf.copy()
        if "height_source" not in out.columns:
            out["height_source"] = np.where(
                out[col].notna() & (out[col].astype(float) > 0),
                "column",
                "default",
            )
        return out, col


@dataclass
class DefaultHeightSource:
    """Constant height for all footprints."""

    default_height: float = 9.0
    name: str = "default"

    def apply(self, gdf: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, str]:
        out = gdf.copy()
        out["estimated_height"] = self.default_height
        out["height_source"] = "default"
        return out, "estimated_height"


@dataclass
class RasterHeightSource:
    """Sample building heights from a GeoTIFF (e.g. DSM/CHM)."""

    raster_path: str | Path
    band: int = 1
    name: str = "raster"

    def apply(self, gdf: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, str]:
        from cfd_geometry.buildings.heights_raster import sample_heights_from_raster

        out = sample_heights_from_raster(
            gdf,
            self.raster_path,
            height_column="estimated_height",
            source_column="height_source",
            band=self.band,
        )
        return out, "estimated_height"


@dataclass
class CompositeHeightSource:
    """
    Primary source then fill gaps from complement raster/GDF or fallbacks.

    Order: column (if present) → OSM → area tiers → default.
    Missing values can be filled from ``complement_raster`` or ``complement_gdf``.
    """

    options: HeightAssignOptions
    name: str = "composite"

    def apply(self, gdf: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, str]:
        from cfd_geometry.buildings.heights_composite import assign_heights_composite

        return assign_heights_composite(gdf, self.options)


def height_source_from_name(
    name: str,
    *,
    options: HeightAssignOptions | None = None,
    height_col: str | None = None,
    default_height: float = 9.0,
    raster_path: str | Path | None = None,
) -> HeightSourceStrategy:
    """
    Factory for height strategies (backward-compatible with CLI ``height_source``).

    Names: ``osm``, ``area``, ``column``, ``default``, ``raster``, ``composite``.
    """
    key = name.lower().strip()
    opts = options or HeightAssignOptions(
        default_height=default_height,
        height_col=height_col,
        complement_raster=str(raster_path) if raster_path else None,
    )

    if key == "osm":
        return OsmHeightSource(default_height=default_height)
    if key == "area":
        return AreaHeightSource()
    if key == "column":
        return ColumnHeightSource(height_col=height_col, default_height=default_height)
    if key == "default" or key == "none":
        return DefaultHeightSource(default_height=default_height)
    if key == "raster":
        if not raster_path:
            raise ValueError("raster height source requires raster_path=")
        return RasterHeightSource(raster_path=raster_path)
    if key == "composite":
        return CompositeHeightSource(options=opts)
    raise ValueError(f"Unknown height source: {name!r}")
