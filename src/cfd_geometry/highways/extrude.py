"""Highway line shapefiles to STL."""

from __future__ import annotations

import os
from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely.geometry import box

from cfd_geometry.constants import DEFAULT_TARGET_CRS
from cfd_geometry.geo.crs import fix_shapefile_crs
from cfd_geometry.geo.offsets import get_combined_offset
from cfd_geometry.highways.geometry import create_highway_geometry, default_highway_config
from cfd_geometry.mesh.normals import mesh_bounds
from cfd_geometry.mesh.stl_io import write_stl_binary


def _clip_to_reference_bounds(
    highway_gdf: gpd.GeoDataFrame,
    reference_shapefiles: list[str],
    buffer_meters: float = 200,
) -> gpd.GeoDataFrame:
    all_bounds = []
    for path in reference_shapefiles:
        if not os.path.exists(path):
            continue
        ref = gpd.read_file(path)
        if ref.crs is None:
            ref = fix_shapefile_crs(path, write_back=False)
        if ref.crs.to_epsg() != highway_gdf.crs.to_epsg():
            ref = ref.to_crs(highway_gdf.crs)
        all_bounds.append(ref.total_bounds)

    if not all_bounds:
        return highway_gdf

    arr = np.array(all_bounds)
    clip_poly = box(
        arr[:, 0].min() - buffer_meters,
        arr[:, 1].min() - buffer_meters,
        arr[:, 2].max() + buffer_meters,
        arr[:, 3].max() + buffer_meters,
    )
    clipped = highway_gdf.copy()
    clipped["geometry"] = clipped.geometry.intersection(clip_poly)
    return clipped[~clipped.geometry.is_empty]


def _resolve_highway_type(value: str, config: dict) -> str:
    key = str(value).lower()
    if key in config:
        return key
    for name in config:
        if name in key:
            return name
    return "default"


def extrude_highways_to_stl(
    shapefile_path: str | Path,
    output_path: str | Path,
    *,
    offset_x: float | None = None,
    offset_y: float | None = None,
    alignment_shapefiles: list[str] | None = None,
    highway_type_column: str | None = None,
    reference_shapefiles: list[str] | None = None,
    use_local_coords: bool = True,
    target_crs: str = DEFAULT_TARGET_CRS,
) -> dict:
    """Convert highway linework to STL aligned with a shared offset."""
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
            coords = list(line.coords)
            if use_local_coords:
                coords = [(x - offset_x, y - offset_y) for x, y in coords]
            triangles.extend(
                create_highway_geometry(
                    coords,
                    params["width"],
                    params["height"],
                    params["padding"],
                )
            )
            segments += 1

    if not triangles:
        raise RuntimeError("No highway triangles generated")

    write_stl_binary(output_path, triangles, header=b"Highway STL for OpenFOAM")
    bounds = mesh_bounds(triangles)
    print(f"Highways: {segments} segments -> {output_path}")

    return {
        "segments": segments,
        "triangles": len(triangles),
        "bounds": bounds,
        "offset": (offset_x, offset_y),
    }
