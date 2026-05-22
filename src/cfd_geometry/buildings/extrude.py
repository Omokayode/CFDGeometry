"""Extrude building footprints to STL using trimesh."""

from __future__ import annotations

import os
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import transform

from cfd_geometry.buildings.load import (
    HeightSource,
    height_for_row,
    load_buildings_gdf,
)
from cfd_geometry.constants import DEFAULT_TARGET_CRS
from cfd_geometry.geo.offsets import get_combined_offset, get_local_transform
from cfd_geometry.mesh.normals import mesh_bounds
from cfd_geometry.mesh.stl_io import validate_stl, write_stl_binary
from cfd_geometry.mesh.trimesh_extrude import extrude_geometry_to_triangles
from cfd_geometry.openfoam.blockmesh import write_blockmesh_vertices


def _print_height_source_stats(gdf: gpd.GeoDataFrame) -> None:
    if "height_source" not in gdf.columns:
        return
    counts = gdf["height_source"].value_counts()
    print("Height data sources:")
    for src, n in counts.items():
        print(f"  {src}: {n}")
    real = int(counts.get("explicit", 0) + counts.get("levels", 0))
    if len(gdf):
        print(f"  With explicit height or levels: {real} ({100 * real / len(gdf):.1f}%)")


def extrude_buildings_to_stl(
    shapefile: str | Path,
    output_stl: str | Path,
    *,
    height_col: str | None = None,
    height_source: HeightSource = "osm",
    default_height: float = 9.0,
    ground_level: float = 0.0,
    use_local_coords: bool = True,
    target_crs: str | None = None,
    auto_utm: bool = True,
    estimate_heights: bool | None = None,
    combined_offset: tuple[float, float] | None = None,
    shapefile_list: list[str] | None = None,
    ground_buffer: float | None = None,
    blockmesh_output: str | Path | None = None,
    ground_stl_output: str | Path | None = None,
) -> dict:
    """
    Convert building footprints to a binary STL for OpenFOAM.

    Uses trimesh polygon extrusion (handles non-convex footprints). Heights default
    to OSM-style attribute rules; use ``height_source='area'`` for footprint tiers.
    """
    shapefile = str(shapefile)
    output_stl = str(output_stl)

    if estimate_heights is not None:
        if estimate_heights:
            height_source = "area"
        elif height_col:
            height_source = "column"
        else:
            height_source = "none"

    gdf, resolved_crs, active_height_col = load_buildings_gdf(
        shapefile,
        target_crs=target_crs,
        auto_utm=auto_utm,
        height_source=height_source,
        height_col=height_col,
        default_height=default_height,
    )

    valid_mask = gdf.geometry.notna()
    gdf = gdf[valid_mask].copy()
    gdf["_geom_valid"] = gdf.geometry.apply(
        lambda g: g.is_valid if g is not None else False
    )
    invalid = (~gdf["_geom_valid"]).sum()
    if invalid:
        print(f"Attempting buffer(0) fix on {invalid} invalid geometries")
        gdf.loc[~gdf["_geom_valid"], "geometry"] = gdf.loc[
            ~gdf["_geom_valid"], "geometry"
        ].buffer(0)
        gdf["_geom_valid"] = gdf.geometry.apply(
            lambda g: g.is_valid and not g.is_empty if g is not None else False
        )

    gdf = gdf[gdf["_geom_valid"]].drop(columns=["_geom_valid"])
    print(f"Valid geometries: {len(gdf)}")
    _print_height_source_stats(gdf)

    target_epsg = int(resolved_crs.split(":")[1])
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
    stats = {"success": 0, "failed": 0, "skipped": 0}
    max_building_height = 0.0

    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            stats["skipped"] += 1
            continue

        height = height_for_row(
            row,
            height_col=active_height_col,
            default_height=default_height,
        )
        height_stats.append(height)
        max_building_height = max(max_building_height, height)

        if use_local_coords:
            geom = transform(lambda x, y: (x - offset_x, y - offset_y), geom)

        tris = extrude_geometry_to_triangles(
            geom, height, ground_level=ground_level
        )
        if tris:
            all_triangles.extend(tris)
            stats["success"] += 1
        else:
            stats["failed"] += 1

    if not all_triangles:
        raise RuntimeError("No triangles generated from building footprints")

    write_stl_binary(output_stl, all_triangles, header=b"Building STL for OpenFOAM")
    bounds = mesh_bounds(all_triangles)

    print(f"Processed {stats['success']} buildings ({stats['failed']} failed, {stats['skipped']} skipped)")
    print(f"Triangles: {len(all_triangles)}")
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

    result = {
        "buildings_processed": stats["success"],
        "buildings_failed": stats["failed"],
        "buildings_skipped": stats["skipped"],
        "triangles": len(all_triangles),
        "bounds": bounds,
        "offset": (offset_x, offset_y),
        "target_crs": resolved_crs,
        "max_building_height": max_building_height,
    }

    if bounds and (ground_buffer is not None or blockmesh_output):
        buf = ground_buffer or 0.0
        gx_min = bounds["x_min"] - buf
        gx_max = bounds["x_max"] + buf
        gy_min = bounds["y_min"] - buf
        gy_max = bounds["y_max"] + buf

        if ground_stl_output:
            ground_rect = Polygon(
                [
                    (gx_min, gy_min),
                    (gx_max, gy_min),
                    (gx_max, gy_max),
                    (gx_min, gy_max),
                    (gx_min, gy_min),
                ]
            )
            ground_tris = extrude_geometry_to_triangles(
                ground_rect, height=0.01, ground_level=ground_level
            )
            if ground_tris:
                write_stl_binary(
                    str(ground_stl_output),
                    ground_tris,
                    header=b"Ground plane STL",
                )
                print(f"Ground STL: {ground_stl_output}")

        domain_height = max(max_building_height * 6.0, 100.0)
        bm_path = blockmesh_output or str(
            Path(output_stl).parent / "blockMeshDict_vertices.txt"
        )
        bm_info = write_blockmesh_vertices(
            bm_path,
            x_min=gx_min,
            x_max=gx_max,
            y_min=gy_min,
            y_max=gy_max,
            z_max=domain_height,
            source_note=shapefile,
            offset_note=(
                f"Translation offset: ({offset_x:.2f}, {offset_y:.2f}) m; CRS {resolved_crs}"
            ),
        )
        print(f"blockMesh snippet: {bm_path}")
        print(
            f"Suggested domain Z: 0 to {domain_height:.2f} m "
            f"({bm_info['nx']} x {bm_info['ny']} x {bm_info['nz']} cells @ 5 m)"
        )
        result["blockmesh"] = bm_info

    return result


def process_shapefiles_to_stl(
    shapefile_list: list[str],
    output_dir: str,
    **kwargs,
) -> tuple[float, float]:
    """Process multiple building shapefiles with one shared combined offset."""
    auto_utm = kwargs.pop("auto_utm", True)
    target_crs = kwargs.get("target_crs")
    if target_crs is None and not auto_utm:
        target_crs = DEFAULT_TARGET_CRS
    elif target_crs is None:
        import geopandas as gpd

        from cfd_geometry.geo.crs import resolve_target_crs

        gdfs = []
        for path in shapefile_list:
            g = gpd.read_file(path)
            if g.crs is None:
                from cfd_geometry.geo.crs import fix_shapefile_crs

                g = fix_shapefile_crs(path, write_back=False)
            gdfs.append(g)
        merged = gpd.GeoDataFrame(
            pd.concat([g[["geometry"]] for g in gdfs], ignore_index=True),
            crs=gdfs[0].crs,
        )
        target_crs = resolve_target_crs(merged, None, auto_utm=auto_utm)
        kwargs["target_crs"] = target_crs

    target_epsg = int(str(kwargs.get("target_crs", DEFAULT_TARGET_CRS)).split(":")[1])
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
