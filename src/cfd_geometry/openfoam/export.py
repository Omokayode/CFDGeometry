"""Export blockMeshDict and snappyHexMeshDict snippets for OpenFOAM."""

from __future__ import annotations

from pathlib import Path

from cfd_geometry.openfoam.blockmesh import write_blockmesh_dict
from cfd_geometry.openfoam.bounds import (
    padded_xy_bounds,
    refinement_box_bounds,
    suggest_inside_point,
)
from cfd_geometry.openfoam.snappy import write_snappy_hex_mesh_dict


def export_openfoam_case(
    output_dir: str | Path,
    *,
    building_bounds: dict[str, float],
    max_building_height: float,
    ground_buffer_m: float,
    stl_files: dict[str, Path | str],
    refinement_buffer_m: float = 10.0,
    cell_size: float = 5.0,
    domain_z_factor: float = 6.0,
    domain_z_min_m: float = 100.0,
) -> dict:
    """
    Write ``blockMeshDict``, ``snappyHexMeshDict``, and a ``snappyHexMeshConfig`` CLI hint.

    ``ground_buffer_m`` sizes the background block mesh; ``refinement_buffer_m`` (default
    10 m) sizes the searchableBox around buildings.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    gx_min, gx_max, gy_min, gy_max = padded_xy_bounds(building_bounds, ground_buffer_m)
    z_max = max(max_building_height * domain_z_factor, domain_z_min_m)

    bm_info = write_blockmesh_dict(
        output_dir / "blockMeshDict",
        x_min=gx_min,
        x_max=gx_max,
        y_min=gy_min,
        y_max=gy_max,
        z_max=z_max,
        cell_size=cell_size,
    )

    outer = {
        "x_min": gx_min,
        "x_max": gx_max,
        "y_min": gy_min,
        "y_max": gy_max,
        "z_min": 0.0,
        "z_max": z_max,
    }
    ref = refinement_box_bounds(
        building_bounds,
        max_building_height=max_building_height,
        buffer_m=refinement_buffer_m,
    )
    inside = suggest_inside_point(outer, building_bounds=building_bounds)

    snappy_info = write_snappy_hex_mesh_dict(
        output_dir / "snappyHexMeshDict",
        stl_files=stl_files,
        outer_bounds=outer,
        refinement_box=ref,
        inside_point=inside,
        block_cells=(bm_info["nx"], bm_info["ny"], bm_info["nz"]),
    )

    paths = {
        "blockMeshDict": str(output_dir / "blockMeshDict"),
        "snappyHexMeshDict": str(output_dir / "snappyHexMeshDict"),
        "snappyHexMeshConfig_command": str(output_dir / "snappyHexMeshConfig.command"),
    }
    return {**bm_info, **snappy_info, "paths": paths, "inside_point": inside}
