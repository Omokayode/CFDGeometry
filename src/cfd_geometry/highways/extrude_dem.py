"""Extrude highways with road surface on a DEM."""

from __future__ import annotations

from pathlib import Path

from cfd_geometry.highways.extrude import _clip_to_reference_bounds, _resolve_highway_type
from cfd_geometry.highways.geometry import create_highway_geometry, default_highway_config
from cfd_geometry.mesh.normals import mesh_bounds
from cfd_geometry.mesh.stl_io import write_stl_binary
from cfd_geometry.raster.elevation import local_ground_z, resolve_dem_z_offset

import geopandas as gpd

from cfd_geometry.constants import DEFAULT_TARGET_CRS
from cfd_geometry.geo.crs import fix_shapefile_crs
from cfd_geometry.geo.offsets import get_combined_offset


def extrude_highways_to_stl_with_dem(
    shapefile_path: str | Path,
    dem_path: str | Path,
    output_path: str | Path,
    *,
    offset_x: float | None = None,
    offset_y: float | None = None,
    alignment_shapefiles: list[str] | None = None,
    highway_type_column: str | None = None,
    reference_shapefiles: list[str] | None = None,
    target_crs: str = DEFAULT_TARGET_CRS,
    z_reference: str = "center",
    z_offset: float | None = None,
    elevation_data: dict | None = None,
) -> dict:
    """Place highway prisms on the DEM (aligned with terrain.stl)."""
    shapefile_path = str(shapefile_path)
    output_path = str(output_path)

    gdf = gpd.read_file(shapefile_path)
    if gdf.crs is None:
        gdf = fix_shapefile_crs(shapefile_path, write_back=False)

    target_epsg = int(target_crs.split(":")[1])
    if gdf.crs.to_epsg() != target_epsg:
        gdf = gdf.to_crs(target_crs)

    line_gdf = gdf[gdf.geometry.geom_type.isin(["LineString", "MultiLineString"])].copy()
    if len(line_gdf) == 0:
        raise ValueError("No line geometries in shapefile")

    refs = reference_shapefiles or alignment_shapefiles
    if refs:
        line_gdf = _clip_to_reference_bounds(line_gdf, refs)

    if offset_x is None or offset_y is None:
        if alignment_shapefiles:
            offset_x, offset_y = get_combined_offset(alignment_shapefiles, target_epsg)
        else:
            offset_x, offset_y = 0.0, 0.0

    if z_offset is None:
        print("Highway vertical alignment:")
        z_offset = resolve_dem_z_offset(elevation_data, offset_x, offset_y, z_reference)

    config = default_highway_config()
    triangles: list = []
    segments = 0

    for _, row in line_gdf.iterrows():
        geom = row.geometry
        lines = list(geom.geoms) if geom.geom_type == "MultiLineString" else [geom]

        highway_type = "default"
        if highway_type_column and highway_type_column in row:
            highway_type = _resolve_highway_type(row[highway_type_column], config)

        params = config[highway_type]

        for line in lines:
            world_coords = list(line.coords)
            base_z = [
                local_ground_z(x, y, elevation_data, z_offset) for x, y in world_coords
            ]
            local_coords = [
                (x - offset_x, y - offset_y) for x, y in world_coords
            ]
            triangles.extend(
                create_highway_geometry(
                    local_coords,
                    params["width"],
                    params["height"],
                    params["padding"],
                    base_z=base_z,
                )
            )
            segments += 1

    if not triangles:
        raise RuntimeError("No highway triangles generated on DEM")

    write_stl_binary(output_path, triangles, header=b"Highway on DEM STL for OpenFOAM")
    bounds = mesh_bounds(triangles)
    print(f"Highways on DEM: {segments} segments -> {output_path}")

    return {
        "segments": segments,
        "triangles": len(triangles),
        "bounds": bounds,
        "offset": (offset_x, offset_y),
        "z_offset_applied": z_offset,
    }
