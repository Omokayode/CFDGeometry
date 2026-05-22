"""Extrude building footprints to STL using trimesh."""

from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Union

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import transform

from cfd_geometry.buildings.load import (
    HeightSource,
    height_for_row,
    min_height_for_row,
    prepare_buildings_gdf,
    resolve_min_height_column,
)
from cfd_geometry.constants import DEFAULT_TARGET_CRS
from cfd_geometry.geo.offsets import (
    get_combined_offset,
    get_combined_offset_from_gdfs,
    get_local_transform,
)

BuildingsInput = Union[str, Path, gpd.GeoDataFrame]
from cfd_geometry.mesh.normals import mesh_bounds
from cfd_geometry.mesh.stl_io import validate_stl, write_stl_binary
from cfd_geometry.mesh.trimesh_extrude import (
    ensure_triangulation_backend,
    extrude_geometry_to_triangles,
)
from cfd_geometry.openfoam.blockmesh import write_blockmesh_dict, write_blockmesh_vertices


def _extrude_one_building(
    geom,
    height: float,
    ground_level: float,
    offset_x: float,
    offset_y: float,
    engine: str,
    use_local_coords: bool,
):
    """Worker-friendly single-footprint extrusion (returns triangles or None)."""
    if geom is None or geom.is_empty:
        return None
    if use_local_coords:
        geom = transform(lambda x, y: (x - offset_x, y - offset_y), geom)
    return extrude_geometry_to_triangles(
        geom, height, ground_level=ground_level, engine=engine
    )


def _print_height_source_stats(gdf: gpd.GeoDataFrame) -> None:
    if "height_source" not in gdf.columns:
        return
    counts = gdf["height_source"].value_counts()
    print("Height data sources:")
    for src, n in counts.items():
        print(f"  {src}: {n}")
    # ``column`` = shapefile/OSM height field (e.g. "395 ft"); same role as ``explicit``.
    reliable = ("explicit", "levels", "column")
    real = int(sum(counts.get(s, 0) for s in reliable))
    if len(gdf):
        print(
            f"  With height tag, column, or levels: {real} ({100 * real / len(gdf):.1f}%)"
        )


def extrude_buildings_to_stl(
    buildings: BuildingsInput,
    output_stl: str | Path,
    *,
    height_col: str | None = None,
    height_source: HeightSource = "osm",
    default_height: float = 9.0,
    ground_level: float = 0.0,
    min_height_col: str | None = None,
    use_local_coords: bool = True,
    target_crs: str | None = None,
    auto_utm: bool = True,
    estimate_heights: bool | None = None,
    combined_offset: tuple[float, float] | None = None,
    shapefile_list: list[str] | None = None,
    alignment_gdfs: list[gpd.GeoDataFrame] | None = None,
    ground_buffer: float | None = None,
    blockmesh_output: str | Path | None = None,
    ground_stl_output: str | Path | None = None,
    workers: int = 1,
    repair_geometry: bool = True,
    resolve_overlaps: str | bool = False,
    overlap_ratio_threshold: float = 0.5,
    complement_raster: str | Path | None = None,
    simplify_tolerance: float | None = None,
    height_strategy=None,
) -> dict:
    """
    Convert building footprints to a binary STL for OpenFOAM.

    ``buildings`` may be a shapefile path or an in-memory :class:`geopandas.GeoDataFrame`
    (e.g. after QGIS or notebook preprocessing). For VoxCity-style tables, use
    ``height_source='column'`` with columns ``height`` / ``min_height`` / ``id``.

    Uses trimesh polygon extrusion (handles non-convex footprints). Heights default
    to OSM-style attribute rules; use ``height_source='area'`` for footprint tiers.
    """
    output_stl = str(output_stl)

    if estimate_heights is not None:
        if estimate_heights:
            height_source = "area"
        elif height_col:
            height_source = "column"
        else:
            height_source = "none"

    prep_kw = dict(
        target_crs=target_crs,
        auto_utm=auto_utm,
        height_source=height_source,
        height_col=height_col,
        default_height=default_height,
        repair_geometry=repair_geometry,
        resolve_overlaps=resolve_overlaps,
        overlap_ratio_threshold=overlap_ratio_threshold,
        complement_raster=complement_raster,
        simplify_tolerance=simplify_tolerance,
        height_strategy=height_strategy,
    )

    if isinstance(buildings, gpd.GeoDataFrame):
        gdf, resolved_crs, active_height_col = prepare_buildings_gdf(
            buildings,
            **prep_kw,
        )
        source_label = "GeoDataFrame"
    else:
        source_label = str(buildings)
        gdf = gpd.read_file(str(buildings))
        from cfd_geometry.geo.crs import fix_shapefile_crs

        if gdf.crs is None:
            gdf = fix_shapefile_crs(str(buildings), write_back=False)
        gdf, resolved_crs, active_height_col = prepare_buildings_gdf(
            gdf,
            source_label=str(buildings),
            **prep_kw,
        )

    return extrude_buildings_gdf_to_stl(
        gdf,
        output_stl,
        resolved_crs=resolved_crs,
        active_height_col=active_height_col,
        default_height=default_height,
        ground_level=ground_level,
        min_height_col=min_height_col,
        use_local_coords=use_local_coords,
        combined_offset=combined_offset,
        shapefile_list=shapefile_list,
        alignment_gdfs=alignment_gdfs,
        ground_buffer=ground_buffer,
        blockmesh_output=blockmesh_output,
        ground_stl_output=ground_stl_output,
        workers=workers,
        source_label=source_label,
    )


def extrude_buildings_gdf_to_stl(
    gdf: gpd.GeoDataFrame,
    output_stl: str | Path,
    *,
    resolved_crs: str,
    active_height_col: str,
    default_height: float = 9.0,
    ground_level: float = 0.0,
    min_height_col: str | None = None,
    use_local_coords: bool = True,
    combined_offset: tuple[float, float] | None = None,
    shapefile_list: list[str] | None = None,
    alignment_gdfs: list[gpd.GeoDataFrame] | None = None,
    ground_buffer: float | None = None,
    blockmesh_output: str | Path | None = None,
    ground_stl_output: str | Path | None = None,
    workers: int = 1,
    source_label: str = "GeoDataFrame",
) -> dict:
    """Extrude an already-prepared building GeoDataFrame to STL."""
    output_stl = str(output_stl)

    engine = ensure_triangulation_backend()
    print(f"Triangulation engine: {engine}")

    active_min_col = resolve_min_height_column(gdf, min_height_col)
    if active_min_col:
        print(f"Using per-building base column: {active_min_col}")

    print(f"Valid geometries: {len(gdf)}")
    _print_height_source_stats(gdf)

    target_epsg = int(resolved_crs.split(":")[1])
    offset_x, offset_y = 0.0, 0.0
    if use_local_coords:
        if combined_offset is not None:
            offset_x, offset_y = combined_offset
        elif alignment_gdfs:
            offset_x, offset_y = get_combined_offset_from_gdfs(
                alignment_gdfs, target_epsg
            )
        elif shapefile_list:
            offset_x, offset_y = get_combined_offset(shapefile_list, target_epsg)
        else:
            offset_x, offset_y = get_local_transform(gdf)

    all_triangles: list = []
    height_stats: list[float] = []
    stats = {"success": 0, "failed": 0, "skipped": 0}
    max_building_height = 0.0

    jobs: list[tuple] = []
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
        base_z = min_height_for_row(
            row,
            min_height_col=active_min_col,
            default_ground=ground_level,
        )
        height_stats.append(height)
        max_building_height = max(max_building_height, height)
        jobs.append((geom, height, base_z))

    if workers > 1 and len(jobs) > 1:
        print(f"Extruding {len(jobs)} buildings with {workers} workers")
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = [
                pool.submit(
                    _extrude_one_building,
                    geom,
                    height,
                    base_z,
                    offset_x,
                    offset_y,
                    engine,
                    use_local_coords,
                )
                for geom, height, base_z in jobs
            ]
            for fut in as_completed(futures):
                tris = fut.result()
                if tris:
                    all_triangles.extend(tris)
                    stats["success"] += 1
                else:
                    stats["failed"] += 1
    else:
        for geom, height, base_z in jobs:
            tris = _extrude_one_building(
                geom,
                height,
                base_z,
                offset_x,
                offset_y,
                engine,
                use_local_coords,
            )
            if tris:
                all_triangles.extend(tris)
                stats["success"] += 1
            else:
                stats["failed"] += 1

    if not all_triangles:
        raise RuntimeError(
            f"No triangles generated from building footprints "
            f"({stats['failed']} failed, {stats['skipped']} skipped). "
            "Check geometries and ensure mapbox-earcut is installed: pip install mapbox-earcut"
        )

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
            source_note=source_label,
            offset_note=(
                f"Translation offset: ({offset_x:.2f}, {offset_y:.2f}) m; CRS {resolved_crs}"
            ),
        )
        bm_dict_path = Path(bm_path).parent / "blockMeshDict"
        bm_info = write_blockmesh_dict(
            bm_dict_path,
            x_min=gx_min,
            x_max=gx_max,
            y_min=gy_min,
            y_max=gy_max,
            z_max=domain_height,
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
