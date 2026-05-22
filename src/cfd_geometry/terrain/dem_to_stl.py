"""DEM GeoTIFF to terrain STL conversion."""

from __future__ import annotations

import numpy as np

from cfd_geometry.constants import DEFAULT_TARGET_CRS
from cfd_geometry.mesh.stl_io import write_stl_binary
from cfd_geometry.raster.elevation import (
    get_elevation_at_point,
    load_elevation_raster,
    preprocess_elevation,
)
from cfd_geometry.terrain.mesh import (
    add_base_and_sides,
    create_terrain_mesh_with_offset,
    create_triangular_mesh,
)


def _resolve_z_offset(
    elevation_data: dict,
    offset_x: float,
    offset_y: float,
    z_reference: str,
) -> float:
    """Elevation (m) to subtract so terrain aligns with flat buildings at z=0."""
    elev = elevation_data["elevation"]
    if z_reference == "none":
        return 0.0
    if z_reference == "min":
        ref = float(np.nanmin(elev))
        print(f"Terrain Z reference: min elevation = {ref:.2f} m")
        return ref
    if z_reference == "center":
        ref = get_elevation_at_point(offset_x, offset_y, elevation_data)
        if ref == 0.0 and np.nanmin(elev) != 0:
            ref = float(np.nanmin(elev))
            print(f"Terrain Z reference: center sample failed; using min = {ref:.2f} m")
        else:
            print(
                f"Terrain Z reference: center ({offset_x:.1f}, {offset_y:.1f}) = {ref:.2f} m"
            )
        return ref
    raise ValueError(f"Unknown z_reference: {z_reference!r}")


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
) -> dict:
    """
    Convert a DEM TIFF to STL using a shared local origin offset.

    ``z_reference``:
    - ``center``: subtract elevation at (offset_x, offset_y) — aligns with buildings at z=0
    - ``min``: subtract minimum DEM elevation in the tile
    - ``none``: keep absolute elevations (meters above sea level)
    """
    print(f"Converting DEM to STL: {input_file} -> {output_file}")
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

    z_offset = _resolve_z_offset(elevation_data, offset_x, offset_y, z_reference)

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
            "min": float(np.min(Z)),
            "max": float(np.max(Z)),
            "range": float(np.max(Z) - np.min(Z)),
        },
    }
