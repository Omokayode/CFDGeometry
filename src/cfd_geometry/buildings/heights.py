"""Building height estimation from footprint area."""

from __future__ import annotations

import geopandas as gpd

from cfd_geometry.constants import DEFAULT_TARGET_CRS
from cfd_geometry.geo.crs import fix_shapefile_crs


def _height_from_area(area: float) -> float:
    if area < 100:
        return 6.0
    if area < 300:
        return 9.0
    if area < 800:
        return 15.0
    if area < 2000:
        return 25.0
    return 40.0


def estimate_heights_from_footprint_area(
    shapefile_path: str,
    output_path: str | None = None,
    metric_crs: str = DEFAULT_TARGET_CRS,
) -> gpd.GeoDataFrame:
    """Estimate building heights from footprint area using tiered urban rules."""
    print("Estimating heights from building footprint areas...")
    buildings = gpd.read_file(shapefile_path)
    if buildings.crs is None:
        buildings = fix_shapefile_crs(shapefile_path, write_back=False)

    if buildings.crs.to_epsg() == 4326:
        buildings_metric = buildings.to_crs(metric_crs)
        buildings["area_sqm"] = buildings_metric.geometry.area
    else:
        buildings["area_sqm"] = buildings.geometry.area

    buildings["estimated_height"] = buildings["area_sqm"].apply(_height_from_area)

    if output_path:
        buildings.to_file(output_path)

    print(f"Estimated heights for {len(buildings)} buildings")
    return buildings
