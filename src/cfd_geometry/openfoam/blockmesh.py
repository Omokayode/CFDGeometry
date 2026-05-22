"""Generate blockMeshDict vertex snippets for OpenFOAM."""

from __future__ import annotations

from pathlib import Path


def write_blockmesh_vertices(
    output_path: str | Path,
    *,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
    z_max: float,
    cell_size: float = 5.0,
    source_note: str = "",
    offset_note: str = "",
) -> dict:
    """
    Write a blockMeshDict vertices/blocks snippet centered on the given XY bounds.

    Z runs from 0 to ``z_max``. Returns suggested cell counts and domain stats.
    """
    output_path = Path(output_path)
    width = x_max - x_min
    length = y_max - y_min
    nx = max(1, int(width / cell_size))
    ny = max(1, int(length / cell_size))
    nz = max(1, int(z_max / cell_size))

    lines = [
        "// blockMeshDict vertices for OpenFOAM",
    ]
    if source_note:
        lines.append(f"// Generated from: {source_note}")
    if offset_note:
        lines.append(f"// {offset_note}")
    lines.extend(
        [
            "",
            "vertices",
            "(",
            f"    ({x_min:.2f} {y_min:.2f} 0.00)  // 0: xmin ymin zmin",
            f"    ({x_max:.2f} {y_min:.2f} 0.00)  // 1: xmax ymin zmin",
            f"    ({x_max:.2f} {y_max:.2f} 0.00)  // 2: xmax ymax zmin",
            f"    ({x_min:.2f} {y_max:.2f} 0.00)  // 3: xmin ymax zmin",
            f"    ({x_min:.2f} {y_min:.2f} {z_max:.2f})  // 4: xmin ymin zmax",
            f"    ({x_max:.2f} {y_min:.2f} {z_max:.2f})  // 5: xmax ymin zmax",
            f"    ({x_max:.2f} {y_max:.2f} {z_max:.2f})  // 6: xmax ymax zmax",
            f"    ({x_min:.2f} {y_max:.2f} {z_max:.2f})  // 7: xmin ymax zmax",
            ");",
            "",
            "blocks",
            "(",
            f"    hex (0 1 2 3 4 5 6 7) ({nx} {ny} {nz}) simpleGrading (1 1 1)",
            ");",
            "",
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "nx": nx,
        "ny": ny,
        "nz": nz,
        "total_cells": nx * ny * nz,
        "domain_width": width,
        "domain_length": length,
        "domain_height": z_max,
    }
