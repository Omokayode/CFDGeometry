"""Shapefile CRS detection and repair."""

from __future__ import annotations

import geopandas as gpd

from cfd_geometry.constants import DEFAULT_TARGET_CRS


def fix_shapefile_crs(shapefile_path: str, *, write_back: bool = True) -> gpd.GeoDataFrame:
    """Fix missing CRS by reading from a sibling .prj file or assuming WGS84."""
    gdf = gpd.read_file(shapefile_path)

    if gdf.crs is not None:
        return gdf

    print("No CRS detected. Checking for .prj file...")
    prj_file = shapefile_path.replace(".shp", ".prj")
    try:
        with open(prj_file, "r", encoding="utf-8") as f:
            prj_content = f.read().strip()
        gdf = gdf.set_crs(prj_content)
        print(f"CRS set from .prj file: {gdf.crs}")
        if write_back:
            gdf.to_file(shapefile_path)
            print("Shapefile saved with CRS information")
    except FileNotFoundError:
        print(f"No .prj file found at {prj_file}; assuming EPSG:4326")
        gdf = gdf.set_crs("EPSG:4326")
    except OSError as e:
        print(f"Error reading .prj file: {e}; assuming EPSG:4326")
        gdf = gdf.set_crs("EPSG:4326")

    return gdf


def read_shapefile(
    shapefile_path: str,
    target_crs: str = DEFAULT_TARGET_CRS,
) -> gpd.GeoDataFrame:
    """Read a shapefile, fix CRS if needed, and reproject to the target CRS."""
    gdf = gpd.read_file(shapefile_path)
    if gdf.crs is None:
        gdf = fix_shapefile_crs(shapefile_path, write_back=False)

    target_epsg = int(target_crs.split(":")[1])
    if gdf.crs.to_epsg() != target_epsg:
        print(f"Reprojecting {shapefile_path} from {gdf.crs} to {target_crs}")
        gdf = gdf.to_crs(target_crs)

    return gdf
