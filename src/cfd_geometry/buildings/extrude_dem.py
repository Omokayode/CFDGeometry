"""Extrude buildings with bases sampled from a DEM raster."""

from __future__ import annotations

from pathlib import Path

from shapely.ops import transform

import numpy as np

from cfd_geometry.buildings.load import (
    HeightSource,
    height_for_row,
    load_buildings_gdf,
)
from cfd_geometry.geo.offsets import get_combined_offset, get_local_transform
from cfd_geometry.mesh.normals import mesh_bounds
from cfd_geometry.mesh.stl_io import write_stl_binary
from cfd_geometry.mesh.trimesh_extrude import extrude_geometry_to_triangles
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
    height_source: HeightSource = "osm",
    default_height: float = 9.0,
    elevation_offset: float = 0.0,
    use_local_coords: bool = True,
    target_crs: str | None = None,
    auto_utm: bool = True,
    estimate_heights: bool | None = None,
    combined_offset: tuple[float, float] | None = None,
    shapefile_list: list[str] | None = None,
) -> dict:
    """Extrude buildings with each footprint base placed on the DEM surface."""
    shapefile = str(shapefile)
    dem_path = str(dem_path)
    output_stl = str(output_stl)

    if estimate_heights is not None:
        if estimate_heights:
            height_source = "area"
        elif height_col:
            height_source = "column"
        else:
            height_source = "none"

    gdf, resolved_crs, active_height_col = load_buildings_gdf(
        shapefile,
        target_crs=target_crs,
        auto_utm=auto_utm,
        height_source=height_source,
        height_col=height_col,
        default_height=default_height,
    )

    elevation_data = load_elevation_raster(dem_path, resolved_crs)

    gdf = gdf[gdf.geometry.notna()].copy()
    invalid = ~gdf.geometry.apply(lambda g: g.is_valid and not g.is_empty)
    if invalid.any():
        gdf.loc[invalid, "geometry"] = gdf.loc[invalid, "geometry"].buffer(0)
    gdf = gdf[gdf.geometry.apply(lambda g: g.is_valid and not g.is_empty)]

    target_epsg = int(resolved_crs.split(":")[1])
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
    failed = 0
    elevation_stats: list[float] = []

    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue

        height = height_for_row(
            row,
            height_col=active_height_col,
            default_height=default_height,
        )

        if use_local_coords:
            geom = transform(lambda x, y: (x - offset_x, y - offset_y), geom)
            geom_world = transform(lambda x, y: (x + offset_x, y + offset_y), geom)
        else:
            geom_world = geom

        ground_z = (
            ground_elevation_for_polygon(geom_world, elevation_data) + elevation_offset
        )
        elevation_stats.append(ground_z)

        tris = extrude_geometry_to_triangles(geom, height, ground_level=ground_z)
        if tris:
            all_triangles.extend(tris)
            processed += 1
        else:
            failed += 1

    if not all_triangles:
        raise RuntimeError("No triangles generated")

    write_stl_binary(
        output_stl, all_triangles, header=b"Building STL with DEM for OpenFOAM"
    )
    bounds = mesh_bounds(all_triangles)
    print(f"DEM buildings: {processed} ok, {failed} failed -> {output_stl}")

    return {
        "buildings_processed": processed,
        "buildings_failed": failed,
        "triangles": len(all_triangles),
        "bounds": bounds,
        "offset": (offset_x, offset_y),
        "target_crs": resolved_crs,
        "mean_ground_elevation": float(np.mean(elevation_stats))
        if elevation_stats
        else 0.0,
    }
