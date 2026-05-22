"""Coordinate offsets for aligned local STL coordinates."""

from __future__ import annotations

import geopandas as gpd
import pandas as pd

from cfd_geometry.constants import DEFAULT_EPSG
from cfd_geometry.geo.crs import fix_shapefile_crs


def get_combined_offset(
    shapefile_paths: list[str],
    target_epsg: int = DEFAULT_EPSG,
) -> tuple[float, float]:
    """
    Compute the center of the combined bounding box from multiple shapefiles.

    All inputs are reprojected to ``EPSG:{target_epsg}`` before merging.
    """
    all_geoms = []

    for path in shapefile_paths:
        gdf = gpd.read_file(path)
        if gdf.crs is None:
            gdf = fix_shapefile_crs(path, write_back=False)
        if gdf.crs.to_epsg() != target_epsg:
            print(f"Reprojecting {path} from {gdf.crs} to EPSG:{target_epsg}")
            gdf = gdf.to_crs(epsg=target_epsg)
        all_geoms.append(gdf[["geometry"]])

    combined = gpd.GeoDataFrame(
        pd.concat(all_geoms, ignore_index=True),
        crs=f"EPSG:{target_epsg}",
    )
    bounds = combined.total_bounds
    offset_x = (bounds[0] + bounds[2]) / 2
    offset_y = (bounds[1] + bounds[3]) / 2
    print(f"Combined offset: ({offset_x:.2f}, {offset_y:.2f})")
    return offset_x, offset_y


def get_local_transform(gdf: gpd.GeoDataFrame) -> tuple[float, float]:
    """Center of a single GeoDataFrame's bounds."""
    bounds = gdf.total_bounds
    return (bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2
