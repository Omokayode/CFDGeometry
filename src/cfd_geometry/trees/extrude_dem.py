"""Extrude trees with bases on a DEM surface."""

from __future__ import annotations

from pathlib import Path

from shapely.geometry import Point

import geopandas as gpd

from cfd_geometry.constants import DEFAULT_TARGET_CRS
from cfd_geometry.geo.crs import fix_shapefile_crs
from cfd_geometry.geo.offsets import get_combined_offset
from cfd_geometry.mesh.stl_io import write_stl_binary
from cfd_geometry.raster.elevation import (
    load_elevation_raster,
    local_ground_z,
    resolve_dem_z_offset,
)
from cfd_geometry.trees.geometry import create_tree_canopy, default_tree_config
from cfd_geometry.trees.heights import assign_tree_heights


def extrude_trees_to_stl_with_dem(
    shapefile_path: str | Path,
    dem_path: str | Path,
    output_path: str | Path,
    *,
    combined_offset: tuple[float, float] | None = None,
    alignment_shapefiles: list[str] | None = None,
    default_height: float = 10.0,
    tree_config: dict | None = None,
    target_crs: str = DEFAULT_TARGET_CRS,
    z_reference: str = "center",
    z_offset: float | None = None,
    elevation_data: dict | None = None,
) -> dict:
    """
    Place each tree on the DEM in local coordinates (aligned with terrain.stl).

    Uses the same ``z_reference`` as terrain (default: subtract elevation at domain center).
    """
    cfg = tree_config or default_tree_config()
    dem_path = str(dem_path)

    if elevation_data is None:
        elevation_data = load_elevation_raster(dem_path, target_crs, build_interpolator=True)

    gdf = gpd.read_file(str(shapefile_path))
    if gdf.crs is None:
        gdf = fix_shapefile_crs(str(shapefile_path), write_back=False)
    if gdf.crs.to_epsg() == 4326:
        gdf = gdf.to_crs(target_crs)

    point_gdf = gdf[gdf.geometry.geom_type == "Point"].copy()
    if len(point_gdf) == 0:
        raise ValueError("No point geometries in shapefile")

    if combined_offset is None and alignment_shapefiles:
        combined_offset = get_combined_offset(
            alignment_shapefiles, int(target_crs.split(":")[1])
        )
    ox, oy = combined_offset or (0.0, 0.0)

    if z_offset is None:
        print("Tree vertical alignment:")
        z_offset = resolve_dem_z_offset(elevation_data, ox, oy, z_reference)

    triangles: list = []
    created = 0

    for _, row in point_gdf.iterrows():
        geom = row.geometry
        world_x, world_y = geom.x, geom.y
        ground_z = local_ground_z(world_x, world_y, elevation_data, z_offset)
        local_pt = Point(world_x - ox, world_y - oy)

        try:
            height = float(row["tree_height_m"])
            height = max(cfg["min_tree_height"], min(cfg["max_tree_height"], height))
        except (ValueError, TypeError, KeyError):
            height = default_height
        trunk_h = height * cfg["trunk_height_ratio"]
        canopy_h = height - trunk_h
        canopy_r = height * cfg["canopy_radius_ratio"]

        tree_tris = create_tree_canopy(
            local_pt,
            canopy_r,
            trunk_h,
            canopy_h,
            cfg["trunk_radius"],
            canopy_shape=cfg["canopy_shape"],
            sides=cfg["detail_level"],
        )
        for tri in tree_tris:
            triangles.append([[v[0], v[1], v[2] + ground_z] for v in tri])
        created += 1

    if not triangles:
        raise RuntimeError("No tree triangles generated on DEM")

    write_stl_binary(output_path, triangles, header=b"Tree STL with DEM for OpenFOAM")
    print(f"DEM trees: {created} -> {output_path}")
    return {
        "trees_created": created,
        "triangles": len(triangles),
        "offset": (ox, oy),
        "z_offset_applied": z_offset,
    }
