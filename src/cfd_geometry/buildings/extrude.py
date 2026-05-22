"""Extrude building footprints to STL."""

from __future__ import annotations

import os
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import transform

from cfd_geometry.buildings.heights import estimate_heights_from_footprint_area
from cfd_geometry.constants import DEFAULT_TARGET_CRS
from cfd_geometry.geo.crs import fix_shapefile_crs
from cfd_geometry.geo.offsets import get_combined_offset, get_local_transform
from cfd_geometry.mesh.extrusion import polygon_to_triangles
from cfd_geometry.mesh.normals import mesh_bounds
from cfd_geometry.mesh.stl_io import validate_stl, write_stl_binary


def extrude_buildings_to_stl(
    shapefile: str | Path,
    output_stl: str | Path,
    *,
    height_col: str | None = None,
    default_height: float = 10.0,
    ground_level: float = 0.0,
    use_local_coords: bool = True,
    target_crs: str = DEFAULT_TARGET_CRS,
    estimate_heights: bool = True,
    combined_offset: tuple[float, float] | None = None,
    shapefile_list: list[str] | None = None,
) -> dict:
    """
    Convert building footprints to an extruded binary STL for OpenFOAM.

    When ``estimate_heights`` is True, heights are derived from footprint area.
    """
    shapefile = str(shapefile)
    output_stl = str(output_stl)
    print(f"Reading shapefile: {shapefile}")

    if estimate_heights:
        gdf = estimate_heights_from_footprint_area(shapefile)
        height_col = "estimated_height"
    else:
        gdf = gpd.read_file(shapefile)
        if gdf.crs is None:
            gdf = fix_shapefile_crs(shapefile, write_back=False)

    target_epsg = int(target_crs.split(":")[1])
    if gdf.crs.to_epsg() != target_epsg:
        print(f"Reprojecting to {target_crs}")
        gdf = gdf.to_crs(target_crs)

    gdf = gdf[gdf.geometry.notna() & gdf.is_valid]
    print(f"Valid geometries: {len(gdf)}")

    offset_x, offset_y = 0.0, 0.0
    if use_local_coords:
        if combined_offset is not None:
            offset_x, offset_y = combined_offset
        elif shapefile_list:
            offset_x, offset_y = get_combined_offset(shapefile_list, target_epsg)
        else:
            offset_x, offset_y = get_local_transform(gdf)

    all_triangles: list = []
    height_stats: list[float] = []
    processed = 0

    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom.is_empty or not geom.is_valid:
            continue

        height = default_height
        if height_col and height_col in row and pd.notna(row[height_col]):
            try:
                height = float(row[height_col])
                if height <= 0:
                    height = default_height
            except (ValueError, TypeError):
                height = default_height

        height_stats.append(height)

        if use_local_coords:
            geom = transform(lambda x, y: (x - offset_x, y - offset_y), geom)

        if isinstance(geom, Polygon):
            all_triangles.extend(polygon_to_triangles(geom, height, ground_level))
            processed += 1
        elif isinstance(geom, MultiPolygon):
            for poly in geom.geoms:
                if poly.is_valid and not poly.is_empty:
                    all_triangles.extend(
                        polygon_to_triangles(poly, height, ground_level)
                    )
            processed += 1

    if not all_triangles:
        raise RuntimeError("No triangles generated from building footprints")

    write_stl_binary(output_stl, all_triangles, header=b"Building STL for OpenFOAM")
    bounds = mesh_bounds(all_triangles)

    print(f"Processed {processed} buildings, {len(all_triangles)} triangles")
    print(f"STL written to: {output_stl}")
    if height_stats:
        arr = np.array(height_stats)
        print(
            f"Heights (m): mean={arr.mean():.2f}, min={arr.min():.2f}, max={arr.max():.2f}"
        )
    if bounds:
        print(
            f"Bounds X[{bounds['x_min']:.2f}, {bounds['x_max']:.2f}] "
            f"Y[{bounds['y_min']:.2f}, {bounds['y_max']:.2f}] "
            f"Z[{bounds['z_min']:.2f}, {bounds['z_max']:.2f}]"
        )

    return {
        "buildings_processed": processed,
        "triangles": len(all_triangles),
        "bounds": bounds,
        "offset": (offset_x, offset_y),
    }


def process_shapefiles_to_stl(
    shapefile_list: list[str],
    output_dir: str,
    **kwargs,
) -> tuple[float, float]:
    """Process multiple building shapefiles with one shared combined offset."""
    target_crs = kwargs.get("target_crs", DEFAULT_TARGET_CRS)
    target_epsg = int(target_crs.split(":")[1])
    combined_offset = get_combined_offset(shapefile_list, target_epsg)

    for path in shapefile_list:
        base = os.path.splitext(os.path.basename(path))[0]
        out = os.path.join(output_dir, f"{base}.stl")
        extrude_buildings_to_stl(
            path,
            out,
            combined_offset=combined_offset,
            shapefile_list=shapefile_list,
            **kwargs,
        )
        validate_stl(out)

    return combined_offset
