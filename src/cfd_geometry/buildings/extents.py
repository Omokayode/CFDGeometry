"""Building footprint bounds for DEM download sizing."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
from shapely.geometry import box

from cfd_geometry.constants import DEFAULT_DEM_BUFFER_M
from cfd_geometry.download.bbox import Bbox
from cfd_geometry.geo.crs import fix_shapefile_crs, utm_epsg_from_wgs84_bounds


def _expand_metric_bounds(
    minx: float,
    miny: float,
    maxx: float,
    maxy: float,
    buffer_m: float,
    epsg: int,
) -> Bbox:
    """Buffer a metric bounding box and return WGS84 ``Bbox``."""
    geom = box(minx, miny, maxx, maxy).buffer(buffer_m)
    out = (
        gpd.GeoDataFrame(geometry=[geom], crs=f"EPSG:{epsg}")
        .to_crs("EPSG:4326")
        .total_bounds
    )
    bbox = Bbox(
        west=float(out[0]),
        south=float(out[1]),
        east=float(out[2]),
        north=float(out[3]),
    )
    bbox.validate()
    return bbox


def dem_download_bbox_around_buildings(
    buildings_path: str | Path,
    *,
    buffer_m: float = DEFAULT_DEM_BUFFER_M,
    fallback_bbox: Bbox | None = None,
) -> Bbox:
    """
    WGS84 DEM extent: building footprint bounds + ``buffer_m`` on all sides (meters).

    Default ``buffer_m`` is 200 m on each side beyond the building footprints.
    """
    buildings_path = Path(buildings_path)
    gdf = gpd.read_file(buildings_path)
    if gdf.crs is None:
        gdf = fix_shapefile_crs(str(buildings_path), write_back=False)

    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    if gdf.empty:
        if fallback_bbox is None:
            raise ValueError("No building footprints to size DEM extent")
        return fallback_bbox

    wgs_bounds = gdf.to_crs("EPSG:4326").total_bounds
    epsg = utm_epsg_from_wgs84_bounds(
        float(wgs_bounds[0]),
        float(wgs_bounds[1]),
        float(wgs_bounds[2]),
        float(wgs_bounds[3]),
    )
    metric_bounds = gdf.to_crs(epsg).total_bounds
    dem_bbox = _expand_metric_bounds(
        float(metric_bounds[0]),
        float(metric_bounds[1]),
        float(metric_bounds[2]),
        float(metric_bounds[3]),
        buffer_m,
        epsg,
    )

    width_m = (metric_bounds[2] - metric_bounds[0]) + 2 * buffer_m
    length_m = (metric_bounds[3] - metric_bounds[1]) + 2 * buffer_m
    print(
        f"DEM extent: {buffer_m:.0f} m padding on all sides "
        f"(~{width_m:.0f} m × {length_m:.0f} m in UTM)"
    )
    print(
        f"  DEM WGS84 bounds: west={dem_bbox.west:.5f} south={dem_bbox.south:.5f} "
        f"east={dem_bbox.east:.5f} north={dem_bbox.north:.5f}"
    )
    return dem_bbox
