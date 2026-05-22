"""Extrude buildings with bases sampled from a DEM raster."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import transform

from cfd_geometry.buildings.heights import estimate_heights_from_footprint_area
from cfd_geometry.constants import DEFAULT_TARGET_CRS
from cfd_geometry.geo.crs import fix_shapefile_crs
from cfd_geometry.geo.offsets import get_combined_offset, get_local_transform
from cfd_geometry.mesh.extrusion import polygon_to_triangles_at_elevation
from cfd_geometry.mesh.normals import mesh_bounds
from cfd_geometry.mesh.stl_io import write_stl_binary
from cfd_geometry.raster.elevation import (
    ground_elevation_for_polygon,
    load_elevation_raster,
)


def extrude_buildings_to_stl_with_dem(
    shapefile: str | Path,
    dem_path: str | Path,
    output_stl: str | Path,
    *,
    height_col: str | None = None,
    default_height: float = 10.0,
    elevation_offset: float = 0.0,
    use_local_coords: bool = True,
    target_crs: str = DEFAULT_TARGET_CRS,
    estimate_heights: bool = True,
    combined_offset: tuple[float, float] | None = None,
    shapefile_list: list[str] | None = None,
) -> dict:
    """Extrude buildings with each footprint base placed on the DEM surface."""
    shapefile = str(shapefile)
    dem_path = str(dem_path)
    output_stl = str(output_stl)

    elevation_data = load_elevation_raster(dem_path, target_crs)

    if estimate_heights:
        gdf = estimate_heights_from_footprint_area(shapefile)
        height_col = "estimated_height"
    else:
        gdf = gpd.read_file(shapefile)
        if gdf.crs is None:
            gdf = fix_shapefile_crs(shapefile, write_back=False)

    target_epsg = int(target_crs.split(":")[1])
    if gdf.crs.to_epsg() != target_epsg:
        gdf = gdf.to_crs(target_crs)

    gdf = gdf[gdf.geometry.notna() & gdf.is_valid]

    offset_x, offset_y = 0.0, 0.0
    if use_local_coords:
        if combined_offset is not None:
            offset_x, offset_y = combined_offset
        elif shapefile_list:
            offset_x, offset_y = get_combined_offset(shapefile_list, target_epsg)
        else:
            offset_x, offset_y = get_local_transform(gdf)

    all_triangles: list = []
    processed = 0
    elevation_stats: list[float] = []

    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom.is_empty or not geom.is_valid:
            continue

        height = default_height
        if height_col and height_col in row and pd.notna(row[height_col]):
            try:
                height = float(row[height_col])
                if height <= 0:
                    height = default_height
            except (ValueError, TypeError):
                height = default_height

        if use_local_coords:
            geom = transform(lambda x, y: (x - offset_x, y - offset_y), geom)
            geom_world = transform(lambda x, y: (x + offset_x, y + offset_y), geom)
        else:
            geom_world = geom

        ground_z = (
            ground_elevation_for_polygon(geom_world, elevation_data) + elevation_offset
        )
        elevation_stats.append(ground_z)

        polys = [geom] if isinstance(geom, Polygon) else list(geom.geoms)
        for poly in polys:
            if poly.is_valid and not poly.is_empty:
                all_triangles.extend(
                    polygon_to_triangles_at_elevation(poly, height, ground_z)
                )
        processed += 1

    if not all_triangles:
        raise RuntimeError("No triangles generated")

    write_stl_binary(
        output_stl, all_triangles, header=b"Building STL with DEM for OpenFOAM"
    )
    bounds = mesh_bounds(all_triangles)
    print(f"DEM buildings: {processed} footprints -> {output_stl}")

    return {
        "buildings_processed": processed,
        "triangles": len(all_triangles),
        "bounds": bounds,
        "offset": (offset_x, offset_y),
        "mean_ground_elevation": float(np.mean(elevation_stats)) if elevation_stats else 0.0,
    }


# Flat-ground extrusion remains available as extrude_buildings_to_stl.
