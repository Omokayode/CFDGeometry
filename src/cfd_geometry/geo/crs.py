"""Shapefile CRS detection, UTM selection, and repair."""

from __future__ import annotations

import geopandas as gpd

from cfd_geometry.constants import DEFAULT_TARGET_CRS


def utm_epsg_from_wgs84_bounds(
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
) -> int:
    """Pick the UTM EPSG code that best covers the WGS84 bounding box center."""
    center_lon = (min_lon + max_lon) / 2.0
    center_lat = (min_lat + max_lat) / 2.0
    utm_zone = int((center_lon + 180.0) / 6.0) + 1
    if center_lat >= 0:
        return 32600 + utm_zone
    return 32700 + utm_zone


def utm_crs_from_gdf(gdf: gpd.GeoDataFrame) -> str:
    """Return ``EPSG:XXXX`` for the UTM zone covering the GeoDataFrame bounds."""
    if gdf.crs is None:
        raise ValueError("GeoDataFrame has no CRS; cannot determine UTM zone")

    wgs = gdf.to_crs("EPSG:4326")
    bounds = wgs.total_bounds
    epsg = utm_epsg_from_wgs84_bounds(bounds[0], bounds[1], bounds[2], bounds[3])
    return f"EPSG:{epsg}"


def resolve_target_crs(
    gdf: gpd.GeoDataFrame,
    target_crs: str | None = None,
    *,
    auto_utm: bool = True,
) -> str:
    """
    Choose a metric target CRS.

    When ``auto_utm`` is True and input is geographic (EPSG:4326), use the
    appropriate UTM zone. Otherwise use ``target_crs`` or the package default.
    """
    if target_crs:
        return target_crs

    if auto_utm and gdf.crs is not None:
        epsg = gdf.crs.to_epsg()
        if epsg == 4326:
            chosen = utm_crs_from_gdf(gdf)
            print(f"Auto UTM CRS: {chosen}")
            return chosen

    return DEFAULT_TARGET_CRS


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
