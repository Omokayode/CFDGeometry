"""Prepare OSM GeoDataFrames for shapefile export (10-char fields, no invalid names)."""

from __future__ import annotations

import re

import geopandas as gpd
import pandas as pd

# Target column -> OSM / OSMnx source name patterns (matched case-insensitively)
BUILDING_FIELDS: dict[str, list[str]] = {
    "height": ["height", "building:height", "building_height"],
    "building": ["building"],
    "building_l": ["building:levels", "building_levels", "building_l", "levels"],
    "amenity": ["amenity"],
    "leisure": ["leisure"],
    "shop": ["shop"],
    "tourism": ["tourism"],
    "name": ["name"],
}

TREE_FIELDS: dict[str, list[str]] = {
    "natural": ["natural"],
    "name": ["name"],
    "height": ["height", "tree:height"],
    "circumf": ["circumference", "circum"],
    "dcrown": ["diameter_crown", "diameter:crown", "crown_diameter"],
}

HIGHWAY_FIELDS: dict[str, list[str]] = {
    "highway": ["highway"],
    "name": ["name"],
    "ref": ["ref"],
}


def _flatten_columns(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Convert OSMnx MultiIndex columns to simple string names."""
    if not isinstance(gdf.columns, pd.MultiIndex):
        return gdf

    new_names: list[str] = []
    for col in gdf.columns:
        if col == "geometry" or (isinstance(col, tuple) and col[-1] == "geometry"):
            new_names.append("geometry")
            continue
        if isinstance(col, tuple):
            parts = [str(p).strip() for p in col if p is not None and str(p) != ""]
            new_names.append(":".join(parts) if len(parts) > 1 else parts[0])
        else:
            new_names.append(str(col))

    out = gdf.copy()
    out.columns = new_names
    return out


def _normalize_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def _find_source_column(gdf: gpd.GeoDataFrame, patterns: list[str]) -> str | None:
    norm_map = {_normalize_key(c): c for c in gdf.columns if c != "geometry"}
    for pattern in patterns:
        key = _normalize_key(pattern)
        if key in norm_map:
            return norm_map[key]
    for col in gdf.columns:
        if col == "geometry":
            continue
        ncol = _normalize_key(col)
        for pattern in patterns:
            if ncol == _normalize_key(pattern) or ncol.endswith(_normalize_key(pattern)):
                return col
    return None


def slim_for_shapefile(
    gdf: gpd.GeoDataFrame,
    field_map: dict[str, list[str]],
) -> gpd.GeoDataFrame:
    """
    Keep only shapefile-safe columns needed downstream.

    OSM feature tables have hundreds of tagged columns with ``:`` and long names
    that break the Shapefile driver. This copies a small attribute subset.
    """
    gdf = _flatten_columns(gdf)
    out = gpd.GeoDataFrame(geometry=gdf.geometry.copy(), crs=gdf.crs)

    for dest, sources in field_map.items():
        src = _find_source_column(gdf, sources)
        if src is not None:
            out[dest] = gdf[src]

    return out


def prepare_buildings_gdf(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    return slim_for_shapefile(gdf, BUILDING_FIELDS)


def prepare_trees_gdf(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    return slim_for_shapefile(gdf, TREE_FIELDS)


def prepare_highways_gdf(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    return slim_for_shapefile(gdf, HIGHWAY_FIELDS)
