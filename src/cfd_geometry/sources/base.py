"""Pluggable source strategies for heights, ground, and tree geometry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point


@runtime_checkable
class HeightSourceStrategy(Protocol):
    """Assign building heights on a footprint GeoDataFrame."""

    name: str

    def apply(self, gdf: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, str]:
        """Return (gdf with heights, active_height_column)."""


@runtime_checkable
class GroundSourceStrategy(Protocol):
    """Resolve ground elevation (local Z) for a footprint or point."""

    name: str

    def ground_z(
        self,
        x: float,
        y: float,
        *,
        polygon=None,
    ) -> float:
        """Ground elevation in the same local CRS as extruded STLs."""


@runtime_checkable
class TreeModelStrategy(Protocol):
    """Build tree mesh triangles at a local point."""

    name: str

    def triangles_at(
        self,
        point: Point,
        *,
        height: float,
        cfg: dict,
    ) -> list:
        """Return STL triangles for one tree."""


@dataclass
class HeightAssignOptions:
    """Options for composite / raster height filling."""

    default_height: float = 9.0
    height_col: str | None = None
    complement_raster: str | None = None
    complement_gdf: gpd.GeoDataFrame | None = None
    complement_height_col: str = "height"
    overlap_ratio_threshold: float = 0.5
