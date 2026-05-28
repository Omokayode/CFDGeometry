"""Sample building heights from raster datasets."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np

from cfd_geometry.raster.elevation import get_elevation_at_point, load_elevation_raster


def sample_heights_from_raster(
    gdf: gpd.GeoDataFrame,
    raster_path: str | Path,
    *,
    height_column: str = "estimated_height",
    source_column: str = "height_source",
    band: int = 1,
    default_height: float | None = None,
) -> gpd.GeoDataFrame:
    """Assign each footprint height from raster value at centroid (metric CRS)."""
    raster_path = str(raster_path)
    elev_data = load_elevation_raster(raster_path, build_interpolator=True)

    if gdf.crs and str(gdf.crs) != str(elev_data.get("crs", gdf.crs)):
        work = gdf.to_crs(elev_data["crs"])
    else:
        work = gdf

    heights: list[float] = []
    sources: list[str] = []
    for _, row in work.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            heights.append(default_height or 0.0)
            sources.append("missing")
            continue
        c = geom.centroid
        z = get_elevation_at_point(c.x, c.y, elev_data)
        if z > 0:
            heights.append(z)
            sources.append("raster")
        else:
            heights.append(default_height or 9.0)
            sources.append("default")

    out = gdf.copy()
    out[height_column] = heights
    out[source_column] = sources
    print(f"Raster heights from {raster_path}: {sum(s == 'raster' for s in sources)} sampled")
    return out


def fill_missing_heights_from_raster(
    gdf: gpd.GeoDataFrame,
    raster_path: str | Path,
    *,
    height_column: str = "estimated_height",
    source_column: str = "height_source",
    missing_sources: tuple[str, ...] = ("default", "area", "missing", ""),
) -> gpd.GeoDataFrame:
    """Only update rows whose height_source indicates a gap."""
    sampled = sample_heights_from_raster(
        gdf,
        raster_path,
        height_column="_raster_fill",
        source_column="_raster_src",
    )
    out = gdf.copy()
    if height_column not in out.columns:
        out[height_column] = np.nan
    if source_column not in out.columns:
        out[source_column] = "default"

    mask = out[source_column].astype(str).isin(missing_sources) | out[height_column].isna()
    n = int(mask.sum())
    if n:
        out.loc[mask, height_column] = sampled.loc[mask, "_raster_fill"]
        out.loc[mask, source_column] = "raster_complement"
        print(f"Complement: filled {n} building heights from raster")
    return out
