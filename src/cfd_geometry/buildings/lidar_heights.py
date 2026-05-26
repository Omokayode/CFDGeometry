"""Building heights from LiDAR surface models (DSM / CHM)."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely.geometry import Point, Polygon

from cfd_geometry.constants import DEFAULT_DEM_MAX_RESOLUTION, DEFAULT_TARGET_CRS
from cfd_geometry.raster.elevation import (
    get_elevation_at_points,
    load_elevation_raster,
)


def _samples_inside_polygon(
    polygon: Polygon,
    *,
    max_samples: int = 64,
) -> list[tuple[float, float]]:
    """Grid + boundary samples inside a footprint (metric coordinates)."""
    minx, miny, maxx, maxy = polygon.bounds
    side = max(2, int(np.sqrt(max_samples)))
    xs = np.linspace(minx, maxx, side)
    ys = np.linspace(miny, maxy, side)
    points: list[tuple[float, float]] = []
    for x in xs:
        for y in ys:
            if polygon.contains(Point(x, y)):
                points.append((float(x), float(y)))
    if len(points) < 4:
        for x, y in polygon.exterior.coords[:-1]:
            points.append((float(x), float(y)))
    return points


def sample_surface_stats(
    polygon: Polygon,
    elevation_data: dict,
    *,
    max_samples: int = 64,
) -> dict[str, float]:
    """Aggregate DSM (or similar) elevations under a footprint."""
    points = _samples_inside_polygon(polygon, max_samples=max_samples)
    values = np.array(
        get_elevation_at_points(points, elevation_data),
        dtype=np.float64,
    )
    valid = values[np.isfinite(values) & (values > -1e4)]
    if valid.size == 0:
        return {}
    return {
        "min": float(np.min(valid)),
        "mean": float(np.mean(valid)),
        "max": float(np.max(valid)),
        "p95": float(np.percentile(valid, 95)),
    }


def building_height_from_lidar(
    polygon: Polygon,
    surface_data: dict,
    *,
    ground_data: dict | None = None,
    percentile: float = 95.0,
    default_height: float = 9.0,
    min_height: float = 1.0,
) -> float:
    """
    Estimate vertical extent (m) from LiDAR DSM samples inside the footprint.

    With ``ground_data`` (DTM/DEM), returns CHM-style height: surface p95 minus
    ground median. Without ground data, uses surface p95 minus surface minimum.
    """
    stats = sample_surface_stats(polygon, surface_data)
    if not stats:
        return default_height

    surface_z = stats["p95"] if percentile >= 90 else stats.get("mean", stats["p95"])

    if ground_data is not None:
        ground_stats = sample_surface_stats(polygon, ground_data)
        ground_ref = ground_stats.get("mean", ground_stats.get("min", 0.0)) if ground_stats else 0.0
    else:
        ground_ref = stats.get("min", 0.0)

    height = float(surface_z - ground_ref)
    if height < min_height:
        return default_height
    return height


def apply_lidar_heights_to_gdf(
    gdf: gpd.GeoDataFrame,
    dsm_path: str | Path,
    *,
    dtm_path: str | Path | None = None,
    height_column: str = "estimated_height",
    source_column: str = "height_source",
    percentile: float = 95.0,
    default_height: float = 9.0,
    target_crs: str | None = None,
    max_resolution: int | None = DEFAULT_DEM_MAX_RESOLUTION,
) -> gpd.GeoDataFrame:
    """Set footprint heights from LiDAR DSM (optional DTM for CHM)."""
    dsm_path = str(dsm_path)
    crs = target_crs or (str(gdf.crs) if gdf.crs else DEFAULT_TARGET_CRS)
    dsm_data = load_elevation_raster(
        dsm_path,
        crs,
        build_interpolator=True,
        max_resolution=max_resolution,
    )
    dtm_data = None
    if dtm_path:
        dtm_data = load_elevation_raster(
            str(dtm_path),
            crs,
            build_interpolator=True,
            max_resolution=max_resolution,
        )

    if gdf.crs and str(gdf.crs) != str(dsm_data.get("crs", gdf.crs)):
        work = gdf.to_crs(dsm_data["crs"])
    else:
        work = gdf

    heights: list[float] = []
    sources: list[str] = []
    for _, row in work.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            heights.append(default_height)
            sources.append("missing")
            continue
        if geom.geom_type == "MultiPolygon":
            geom = max(geom.geoms, key=lambda g: g.area)
        h = building_height_from_lidar(
            geom,
            dsm_data,
            ground_data=dtm_data,
            percentile=percentile,
            default_height=default_height,
        )
        heights.append(h)
        sources.append("lidar")

    out = gdf.copy()
    out[height_column] = heights
    out[source_column] = sources
    n = sum(s == "lidar" for s in sources)
    print(f"LiDAR heights from {dsm_path}: {n} footprints")
    return out
