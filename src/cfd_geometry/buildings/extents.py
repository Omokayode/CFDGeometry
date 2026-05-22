"""Building footprint bounds for DEM and domain sizing."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd

from cfd_geometry.buildings.load import HeightSource, assign_building_heights, height_for_row
from cfd_geometry.download.bbox import Bbox
from cfd_geometry.geo.crs import fix_shapefile_crs, utm_epsg_from_wgs84_bounds


def max_building_height_m(
    gdf: gpd.GeoDataFrame,
    *,
    height_col: str,
    default_height: float = 9.0,
) -> float:
    """Maximum extrusion height (m) across building rows."""
    if gdf.empty:
        return default_height

    heights = [
        height_for_row(row, height_col=height_col, default_height=default_height)
        for _, row in gdf.iterrows()
    ]
    return float(max(heights)) if heights else default_height


def _expand_metric_bounds(
    minx: float,
    miny: float,
    maxx: float,
    maxy: float,
    buffer_m: float,
    epsg: int,
) -> Bbox:
    """Buffer a metric bounding box and return WGS84 ``Bbox``."""
    from shapely.geometry import box

    geom = box(minx, miny, maxx, maxy).buffer(buffer_m)
    out = (
        gpd.GeoDataFrame(geometry=[geom], crs=f"EPSG:{epsg}")
        .to_crs("EPSG:4326")
        .total_bounds
    )
    bbox = Bbox(west=float(out[0]), south=float(out[1]), east=float(out[2]), north=float(out[3]))
    bbox.validate()
    return bbox


def dem_download_bbox_from_buildings(
    buildings_path: str | Path,
    *,
    height_source: HeightSource = "osm",
    default_height: float = 9.0,
    buffer_height_factor: float = 15.0,
    min_buffer_m: float = 50.0,
    fallback_bbox: Bbox | None = None,
) -> tuple[Bbox, float, float]:
    """
    DEM fetch extent: building footprints expanded by ``buffer_height_factor × max_height``.

    Returns (dem_bbox_wgs84, max_building_height_m, buffer_m_applied).
    """
    buildings_path = Path(buildings_path)
    gdf = gpd.read_file(buildings_path)
    if gdf.crs is None:
        gdf = fix_shapefile_crs(str(buildings_path), write_back=False)

    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    if gdf.empty:
        if fallback_bbox is None:
            raise ValueError("No building footprints to size DEM extent")
        return fallback_bbox, default_height, min_buffer_m

    gdf, height_col = assign_building_heights(
        gdf,
        height_source=height_source,
        default_height=default_height,
    )
    max_h = max_building_height_m(gdf, height_col=height_col, default_height=default_height)
    buffer_m = max(min_buffer_m, buffer_height_factor * max_h)

    wgs_bounds = gdf.to_crs("EPSG:4326").total_bounds
    epsg = utm_epsg_from_wgs84_bounds(
        float(wgs_bounds[0]),
        float(wgs_bounds[1]),
        float(wgs_bounds[2]),
        float(wgs_bounds[3]),
    )
    metric = gdf.to_crs(epsg)
    bounds = metric.total_bounds
    dem_bbox = _expand_metric_bounds(
        float(bounds[0]),
        float(bounds[1]),
        float(bounds[2]),
        float(bounds[3]),
        buffer_m,
        epsg,
    )

    print(
        f"DEM extent: max building {max_h:.1f} m → buffer {buffer_m:.1f} m "
        f"({buffer_height_factor:.0f}× height) on all sides"
    )
    print(
        f"  DEM WGS84 bounds: west={dem_bbox.west:.5f} south={dem_bbox.south:.5f} "
        f"east={dem_bbox.east:.5f} north={dem_bbox.north:.5f}"
    )
    return dem_bbox, max_h, buffer_m
