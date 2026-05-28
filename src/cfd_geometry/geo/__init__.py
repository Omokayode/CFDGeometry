from cfd_geometry.geo.crs import (
    fix_shapefile_crs,
    read_shapefile,
    resolve_target_crs,
    utm_crs_from_gdf,
    utm_epsg_from_wgs84_bounds,
)
from cfd_geometry.geo.offsets import (
    get_combined_offset,
    get_local_transform,
    target_epsg_for_shapefiles,
)

__all__ = [
    "fix_shapefile_crs",
    "get_combined_offset",
    "get_local_transform",
    "read_shapefile",
    "resolve_target_crs",
    "target_epsg_for_shapefiles",
    "utm_crs_from_gdf",
    "utm_epsg_from_wgs84_bounds",
]
