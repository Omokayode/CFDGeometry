"""Composite height assignment (column → OSM → area → complements)."""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd

from cfd_geometry.buildings.heights import _height_from_area
from cfd_geometry.buildings.heights_osm import estimate_height_from_attributes
from cfd_geometry.buildings.heights_raster import fill_missing_heights_from_raster
from cfd_geometry.buildings.columns import resolve_height_column
from cfd_geometry.sources.base import HeightAssignOptions
from cfd_geometry.sources.height import OsmHeightSource


def assign_heights_composite(
    gdf: gpd.GeoDataFrame,
    options: HeightAssignOptions,
) -> tuple[gpd.GeoDataFrame, str]:
    """
    Multi-stage height assignment with optional second-dataset / raster complement.

    1. Use explicit column when present and valid
    2. OSM rules for remaining rows
    3. Area tiers for still-missing
    4. Complement raster or GeoDataFrame for gaps
    5. default_height fallback
    """
    out = gdf.copy()
    col = resolve_height_column(out, options.height_col)
    height_col = "estimated_height"
    source_col = "height_source"

    heights: list[float] = []
    sources: list[str] = []

    for _, row in out.iterrows():
        h: float | None = None
        src = "default"

        if col and col in row.index and pd.notna(row[col]):
            try:
                v = float(row[col])
                if v > 0:
                    h, src = v, "column"
            except (ValueError, TypeError):
                pass

        if h is None:
            h, src = estimate_height_from_attributes(row, default_height=options.default_height)

        if src in ("default",) and h == options.default_height:
            area = row.geometry.area if row.geometry is not None else 0.0
            if area > 0:
                h = _height_from_area(area)
                src = "area"

        heights.append(h)
        sources.append(src)

    out[height_col] = heights
    out[source_col] = sources

    if options.complement_gdf is not None:
        out = _complement_from_gdf(out, options.complement_gdf, options.complement_height_col)

    if options.complement_raster:
        out = fill_missing_heights_from_raster(
            out,
            options.complement_raster,
            height_column=height_col,
            source_column=source_col,
        )

    still = out[source_col].astype(str).isin(("default", "area")) & (
        out[height_col] == options.default_height
    )
    if still.any():
        out.loc[still, height_col] = options.default_height
        out.loc[still, source_col] = "default"

    active = col if col and (out[col].notna() & (out[col].astype(float) > 0)).any() else height_col
    return out, active


def _complement_from_gdf(
    gdf: gpd.GeoDataFrame,
    complement: gpd.GeoDataFrame,
    height_col: str,
) -> gpd.GeoDataFrame:
    """Spatial join: fill missing heights from a second building layer."""
    if complement.crs != gdf.crs:
        complement = complement.to_crs(gdf.crs)

    if height_col not in complement.columns:
        comp = OsmHeightSource().apply(complement)[0]
    else:
        comp = complement

    comp_sub = comp[[height_col, "geometry"]].rename(columns={height_col: "_comp_h"})
    joined = gpd.sjoin(gdf, comp_sub, how="left", predicate="intersects")
    joined = joined.loc[~joined.index.duplicated(keep="first")]

    mask = joined["height_source"].astype(str).isin(("default", "area", "missing")) | joined[
        "estimated_height"
    ].isna()
    fill = mask & joined["_comp_h"].notna()
    n = int(fill.sum())
    if n:
        joined.loc[fill, "estimated_height"] = joined.loc[fill, "_comp_h"].astype(float)
        joined.loc[fill, "height_source"] = "gdf_complement"
        print(f"Complement: filled {n} heights from second GeoDataFrame")

    drop_cols = [c for c in joined.columns if c.startswith("index_") or c == "_comp_h"]
    return joined.drop(columns=drop_cols, errors="ignore")
