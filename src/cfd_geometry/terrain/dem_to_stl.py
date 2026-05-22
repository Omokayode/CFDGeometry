"""DEM GeoTIFF to terrain STL conversion."""

from __future__ import annotations

import numpy as np

from cfd_geometry.constants import DEFAULT_TARGET_CRS
from cfd_geometry.mesh.stl_io import write_stl_binary
from cfd_geometry.raster.elevation import load_elevation_raster, preprocess_elevation
from cfd_geometry.terrain.mesh import (
    add_base_and_sides,
    create_terrain_mesh_with_offset,
    create_triangular_mesh,
)


def dem_to_stl_with_offset(
    input_file: str,
    output_file: str,
    offset_x: float,
    offset_y: float,
    *,
    scale_factor: float = 1.0,
    vertical_scale: float = 1.0,
    smooth_sigma: float = 0,
    max_resolution: int | None = None,
    add_base: bool = True,
    target_crs: str = DEFAULT_TARGET_CRS,
) -> dict:
    """Convert a DEM TIFF to STL using a shared local origin offset."""
    print(f"Converting DEM to STL: {input_file} -> {output_file}")
    elevation_data = load_elevation_raster(input_file, target_crs, build_interpolator=False)
    elevation_data = preprocess_elevation(
        elevation_data,
        smooth_sigma=smooth_sigma,
        max_resolution=max_resolution,
        vertical_scale=vertical_scale,
    )

    X, Y, Z = create_terrain_mesh_with_offset(
        elevation_data, offset_x, offset_y, scale_factor
    )
    triangles = create_triangular_mesh(X, Y, Z)
    if add_base:
        triangles = add_base_and_sides(triangles)

    write_stl_binary(
        output_file,
        triangles,
        header=b"Terrain STL for OpenFOAM",
    )

    bounds = {}
    if triangles:
        pts = np.array([p for tri in triangles for p in tri])
        bounds = {
            "x_min": float(pts[:, 0].min()),
            "x_max": float(pts[:, 0].max()),
            "y_min": float(pts[:, 1].min()),
            "y_max": float(pts[:, 1].max()),
            "z_min": float(pts[:, 2].min()),
            "z_max": float(pts[:, 2].max()),
        }

    return {
        "triangles_generated": len(triangles),
        "bounds": bounds,
        "offset_used": (offset_x, offset_y),
        "elevation_range": {
            "min": float(np.min(Z)),
            "max": float(np.max(Z)),
            "range": float(np.max(Z) - np.min(Z)),
        },
    }
