"""Validate GIS input paths for offset / alignment."""

from __future__ import annotations

import os

# Extensions geopandas can reasonably read for footprint alignment
VECTOR_EXTENSIONS = {".shp", ".gpkg", ".geojson", ".json", ".fgb", ".zip"}

# Outputs and mesh formats that must not be passed to --align-with
NON_VECTOR_EXTENSIONS = {".stl", ".obj", ".ply", ".off", ".dae", ".tif", ".tiff"}


def filter_vector_inputs(
    paths: list[str],
    *,
    label: str = "align-with",
) -> list[str]:
    """
    Keep only vector layer paths suitable for ``gpd.read_file``.

    Skips STL and other non-GIS files with a warning.
    """
    kept: list[str] = []
    for path in paths:
        ext = os.path.splitext(path)[1].lower()
        if ext in NON_VECTOR_EXTENSIONS:
            print(
                f"Warning: skipping {path} for {label} "
                f"({ext} is not a vector layer; use .shp/.gpkg/.geojson only)"
            )
            continue
        if ext and ext not in VECTOR_EXTENSIONS:
            print(f"Warning: unusual extension for {label}: {path}")
        kept.append(path)

    if not kept:
        raise ValueError(
            f"No vector layers in {label} list. "
            "Pass shapefiles only (e.g. buildings.shp, trees.shp), not STL outputs."
        )
    return kept
