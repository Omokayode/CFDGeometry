"""OSM-style building height estimation from shapefile attributes."""

from __future__ import annotations

import re
from typing import Any

import geopandas as gpd
import pandas as pd

# Tag value -> height (meters). Keys match common shapefile column names (often truncated).
HEIGHT_RULES: dict[str, dict[str, float]] = {
    "building": {
        "stadium": 25.0,
        "cathedral": 30.0,
        "church": 15.0,
        "mosque": 20.0,
        "temple": 12.0,
        "commercial": 15.0,
        "retail": 12.0,
        "industrial": 10.0,
        "warehouse": 8.0,
        "residential": 9.0,
        "apartments": 12.0,
        "hotel": 20.0,
        "hospital": 15.0,
        "school": 12.0,
        "university": 15.0,
        "civic": 15.0,
        "public": 12.0,
        "house": 6.0,
        "detached": 8.0,
        "garage": 3.0,
        "shed": 3.0,
        "yes": 9.0,
    },
    "amenity": {
        "hospital": 20.0,
        "school": 12.0,
        "university": 15.0,
        "library": 12.0,
        "townhall": 15.0,
        "fire_station": 10.0,
        "police": 10.0,
        "post_office": 8.0,
        "bank": 12.0,
        "restaurant": 6.0,
        "cafe": 5.0,
        "fast_food": 5.0,
        "bar": 6.0,
        "pub": 6.0,
        "fuel": 6.0,
        "parking": 3.0,
    },
    "leisure": {
        "stadium": 25.0,
        "sports_centre": 15.0,
        "swimming_pool": 8.0,
        "fitness_centre": 10.0,
    },
    "shop": {
        "mall": 20.0,
        "supermarket": 8.0,
        "department_store": 15.0,
    },
    "tourism": {
        "hotel": 20.0,
        "museum": 12.0,
        "attraction": 15.0,
    },
}

# Shapefile / OSM column aliases (truncated names, colons as underscores, etc.)
_COLUMN_ALIASES: dict[str, list[str]] = {
    "height": ["height", "HEIGHT", "building_height"],
    "building:levels": [
        "building:levels",
        "building_levels",
        "building_l",
        "building_l1",
        "levels",
    ],
    "building": ["building", "BUILDING", "type"],
    "amenity": ["amenity", "AMENITY"],
    "leisure": ["leisure", "LEISURE"],
    "shop": ["shop", "SHOP"],
    "tourism": ["tourism", "TOURISM"],
}


def parse_height_string(height_str: Any) -> float | None:
    """Parse height from strings like '45 m', '132', '45m', or feet-like bare numbers."""
    if height_str is None or (isinstance(height_str, float) and pd.isna(height_str)):
        return None
    if isinstance(height_str, (int, float)):
        h = float(height_str)
        return h if h > 0 else None

    text = str(height_str).strip().lower()
    if not text:
        return None

    match = re.search(r"(\d+\.?\d*)", text)
    if not match:
        return None

    try:
        height = float(match.group(1))
    except ValueError:
        return None

    if height <= 0:
        return None

    # Bare large integers without units are often feet in US OSM exports (e.g. "150").
    if height >= 100 and "ft" not in text and "m" not in text:
        height *= 0.3048

    return height


def _field_value(row: pd.Series | dict, canonical: str) -> str:
    """Return stripped lowercase attribute value for a canonical OSM key."""
    if isinstance(row, pd.Series):
        columns = {c.lower(): c for c in row.index}
        data = row
    else:
        columns = {str(k).lower(): k for k in row}
        data = row

    for alias in _COLUMN_ALIASES.get(canonical, [canonical]):
        key = columns.get(alias.lower())
        if key is None:
            continue
        val = data[key] if isinstance(data, pd.Series) else data.get(key)
        if val is None or (isinstance(val, float) and pd.isna(val)):
            continue
        text = str(val).strip().lower()
        if text:
            return text
    return ""


def estimate_height_from_attributes(
    row: pd.Series | dict,
    *,
    default_height: float = 9.0,
) -> tuple[float, str]:
    """
    Estimate building height from OSM-like attributes.

    Returns (height_meters, source) where source is one of:
    explicit, levels, estimated, default.
    """
    raw_height = _field_value(row, "height")
    height = parse_height_string(raw_height) if raw_height else None
    if height:
        return height, "explicit"

    levels_str = _field_value(row, "building:levels")
    if levels_str:
        try:
            levels = float(levels_str)
            if levels > 0:
                meters_per_floor = 3.5
                amenity = _field_value(row, "amenity")
                building = _field_value(row, "building")
                if amenity == "parking":
                    meters_per_floor = 3.0
                elif building == "apartments":
                    meters_per_floor = 3.2
                elif building in ("commercial", "retail", "office"):
                    meters_per_floor = 4.0
                return levels * meters_per_floor, "levels"
        except ValueError:
            pass

    for category, type_heights in HEIGHT_RULES.items():
        value = _field_value(row, category)
        if value and value in type_heights:
            return type_heights[value], "estimated"

    return default_height, "default"


def apply_osm_heights_to_gdf(
    gdf: gpd.GeoDataFrame,
    *,
    default_height: float = 9.0,
    height_column: str = "estimated_height",
    source_column: str = "height_source",
) -> gpd.GeoDataFrame:
    """Add ``estimated_height`` and ``height_source`` columns using OSM-style rules."""
    heights: list[float] = []
    sources: list[str] = []

    for _, row in gdf.iterrows():
        h, src = estimate_height_from_attributes(row, default_height=default_height)
        heights.append(h)
        sources.append(src)

    out = gdf.copy()
    out[height_column] = heights
    out[source_column] = sources
    return out
