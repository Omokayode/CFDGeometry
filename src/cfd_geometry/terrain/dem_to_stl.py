"""DEM GeoTIFF to terrain STL conversion."""

from __future__ import annotations

import numpy as np

from cfd_geometry.constants import DEFAULT_TARGET_CRS
from cfd_geometry.mesh.stl_io import write_stl_binary
from cfd_geometry.raster.elevation import (
    load_elevation_raster,
    preprocess_elevation,
    resolve_dem_z_offset,
)
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
    smooth_sigma: float = 0.0,
    max_resolution: int | None = None,
    add_base: bool = True,
    target_crs: str = DEFAULT_TARGET_CRS,
    z_reference: str = "center",
    elevation_data: dict | None = None,
    z_offset: float | None = None,
) -> dict:
    """
    Convert a DEM TIFF to STL using a shared local origin offset.

    ``z_reference``:
    - ``center``: subtract elevation at (offset_x, offset_y) — aligns with buildings at z=0
    - ``min``: subtract minimum DEM elevation in the tile
    - ``none``: keep absolute elevations (meters above sea level)
    """
    print(f"Converting DEM to STL: {input_file} -> {output_file}")
    if elevation_data is None:
        elevation_data = load_elevation_raster(
            input_file,
            target_crs,
            build_interpolator=True,
            max_resolution=max_resolution,
        )
        elevation_data = preprocess_elevation(
            elevation_data,
            smooth_sigma=smooth_sigma,
            max_resolution=max_resolution,
            vertical_scale=vertical_scale,
        )

    if z_offset is None:
        print("Terrain vertical alignment:")
        z_offset = resolve_dem_z_offset(elevation_data, offset_x, offset_y, z_reference)

    if not np.isfinite(z_offset):
        elev = elevation_data["elevation"]
        z_offset = float(np.nanmedian(elev[np.isfinite(elev)]))
        print(f"Warning: non-finite z_offset; using median elevation {z_offset:.2f} m")

    X, Y, Z = create_terrain_mesh_with_offset(
        elevation_data,
        offset_x,
        offset_y,
        scale_factor,
        z_offset=z_offset,
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
        "z_offset_applied": z_offset,
        "z_reference": z_reference,
        "elevation_range": {
            "min": float(np.nanmin(Z)),
            "max": float(np.nanmax(Z)),
            "range": float(np.nanmax(Z) - np.nanmin(Z)),
        },
    }
