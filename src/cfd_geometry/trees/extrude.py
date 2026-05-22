"""Point shapefile to tree STL."""

from __future__ import annotations

import numpy as np
from shapely.geometry import Point

from cfd_geometry.constants import DEFAULT_TARGET_CRS
from cfd_geometry.geo.crs import fix_shapefile_crs
from cfd_geometry.geo.offsets import get_combined_offset
from cfd_geometry.mesh.normals import mesh_bounds
from cfd_geometry.mesh.stl_io import write_stl_binary
from cfd_geometry.sources.trees import tree_model_from_name
from cfd_geometry.trees.geometry import default_tree_config

import geopandas as gpd


def extrude_trees_to_stl(
    shapefile_path: str,
    output_path: str,
    *,
    combined_offset: tuple[float, float] | None = None,
    alignment_shapefiles: list[str] | None = None,
    height_column: str | None = None,
    default_height: float = 5.0,
    tree_config: dict | None = None,
    tree_model: str = "canopy",
    use_local_coords: bool = True,
    target_crs: str = DEFAULT_TARGET_CRS,
) -> dict:
    """Convert a point shapefile to tree STL aligned with other layers."""
    cfg = tree_config or default_tree_config()
    model = tree_model_from_name(tree_model)
    gdf = gpd.read_file(shapefile_path)
    if gdf.crs is None:
        gdf = fix_shapefile_crs(shapefile_path, write_back=False)

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

    triangles: list = []
    height_stats: list[float] = []
    created = 0

    for idx, row in point_gdf.iterrows():
        geom = row.geometry
        pt = (
            Point(geom.x - ox, geom.y - oy)
            if use_local_coords
            else Point(geom.x, geom.y)
        )

        if height_column and height_column in row and row[height_column] is not None:
            try:
                height = float(row[height_column])
                height = max(
                    cfg["min_tree_height"],
                    min(cfg["max_tree_height"], height),
                )
            except (ValueError, TypeError):
                height = default_height
        else:
            height = default_height

        height_stats.append(height)

        try:
            tris = model.triangles_at(pt, height=height, cfg=cfg)
            if tris:
                triangles.extend(tris)
                created += 1
        except Exception as e:
            print(f"Tree at index {idx} failed: {e}")

    if not triangles:
        raise RuntimeError("No tree triangles generated")

    write_stl_binary(output_path, triangles, header=b"Tree STL for OpenFOAM")
    bounds = mesh_bounds(triangles)
    print(f"Created {created} trees, {len(triangles)} triangles -> {output_path}")

    return {
        "trees_created": created,
        "triangles_generated": len(triangles),
        "bounds": bounds,
        "combined_offset": (ox, oy),
    }
