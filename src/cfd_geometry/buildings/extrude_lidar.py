"""Extrude buildings with LiDAR heights and optional terrain-following facades."""

from __future__ import annotations

from pathlib import Path
from typing import Union

import geopandas as gpd
from shapely.ops import transform

from cfd_geometry.buildings.extrude_dem import extrude_buildings_to_stl_with_dem
from cfd_geometry.buildings.facade_mesh import extrude_geometry_stepped_facade
from cfd_geometry.buildings.lidar_heights import apply_lidar_heights_to_gdf
from cfd_geometry.buildings.load import (
    HeightSource,
    height_for_row,
    prepare_buildings_gdf,
    load_buildings_gdf,
)
from cfd_geometry.geo.offsets import (
    get_combined_offset,
    get_combined_offset_from_gdfs,
    get_local_transform,
)
from cfd_geometry.mesh.normals import mesh_bounds
from cfd_geometry.mesh.stl_io import write_stl_binary
from cfd_geometry.mesh.trimesh_extrude import ensure_triangulation_backend
from cfd_geometry.raster.elevation import load_elevation_raster, resolve_dem_z_offset

BuildingsInput = Union[str, Path, gpd.GeoDataFrame]


def extrude_buildings_to_stl_with_lidar(
    buildings: BuildingsInput,
    dem_path: str | Path,
    output_stl: str | Path,
    *,
    dsm_path: str | Path,
    dtm_path: str | Path | None = None,
    stepped_facades: bool = False,
    facade_samples_per_edge: int = 2,
    height_col: str | None = None,
    height_source: HeightSource = "osm",
    default_height: float = 9.0,
    elevation_offset: float = 0.0,
    use_local_coords: bool = True,
    target_crs: str | None = None,
    auto_utm: bool = True,
    combined_offset: tuple[float, float] | None = None,
    shapefile_list: list[str] | None = None,
    alignment_gdfs: list[gpd.GeoDataFrame] | None = None,
    z_reference: str = "center",
    z_offset: float | None = None,
    lidar_percentile: float = 95.0,
) -> dict:
    """
    Extrude buildings using a ground DEM and LiDAR DSM for heights.

    ``stepped_facades=True`` drapes the footprint base on the DEM so vertical
    walls follow local grade (useful when terrain slope is significant).
    """
    if not stepped_facades:
        gdf = _buildings_with_lidar_heights(
            buildings,
            dsm_path=dsm_path,
            dtm_path=dtm_path,
            target_crs=target_crs,
            auto_utm=auto_utm,
            height_source=height_source,
            height_col=height_col,
            default_height=default_height,
            lidar_percentile=lidar_percentile,
        )
        return extrude_buildings_to_stl_with_dem(
            gdf,
            dem_path,
            output_stl,
            height_col="estimated_height",
            height_source="column",
            default_height=default_height,
            elevation_offset=elevation_offset,
            use_local_coords=use_local_coords,
            target_crs=target_crs,
            auto_utm=auto_utm,
            combined_offset=combined_offset,
            shapefile_list=shapefile_list,
            alignment_gdfs=alignment_gdfs,
            z_reference=z_reference,
            z_offset=z_offset,
        )

    dem_path = str(dem_path)
    dsm_path = str(dsm_path)
    output_stl = str(output_stl)

    gdf = _buildings_with_lidar_heights(
        buildings,
        dsm_path=dsm_path,
        dtm_path=dtm_path,
        target_crs=target_crs,
        auto_utm=auto_utm,
        height_source=height_source,
        height_col=height_col,
        default_height=default_height,
        lidar_percentile=lidar_percentile,
    )

    elevation_data = load_elevation_raster(
        dem_path, str(gdf.crs), build_interpolator=True
    )
    engine = ensure_triangulation_backend()
    print(f"Triangulation engine: {engine}")
    print("Facade mode: stepped (DEM-following base)")

    target_epsg = int(str(gdf.crs).split(":")[1])
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

    if z_offset is None:
        print("Building vertical alignment:")
        z_offset = resolve_dem_z_offset(elevation_data, offset_x, offset_y, z_reference)

    all_triangles: list = []
    processed = 0
    failed = 0

    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue

        height = height_for_row(
            row,
            height_col="estimated_height",
            default_height=default_height,
        )

        if use_local_coords:
            geom = transform(lambda x, y: (x - offset_x, y - offset_y), geom)
            world_offset = (offset_x, offset_y)
        else:
            world_offset = (0.0, 0.0)

        tris = extrude_geometry_stepped_facade(
            geom,
            height,
            elevation_data,
            z_offset,
            samples_per_edge=facade_samples_per_edge,
            world_offset=world_offset,
        )
        if tris:
            if elevation_offset:
                tris = [
                    [
                        [v[0], v[1], v[2] + elevation_offset]
                        for v in tri
                    ]
                    for tri in tris
                ]
            all_triangles.extend(tris)
            processed += 1
        else:
            failed += 1

    if not all_triangles:
        raise RuntimeError("No triangles generated")

    write_stl_binary(
        output_stl,
        all_triangles,
        header=b"Building STL LiDAR stepped facades for OpenFOAM",
    )
    bounds = mesh_bounds(all_triangles)
    print(f"LiDAR stepped buildings: {processed} ok, {failed} failed -> {output_stl}")

    return {
        "buildings_processed": processed,
        "buildings_failed": failed,
        "triangles": len(all_triangles),
        "bounds": bounds,
        "offset": (offset_x, offset_y),
        "target_crs": str(gdf.crs),
        "z_offset_applied": z_offset,
        "stepped_facades": True,
    }


def _buildings_with_lidar_heights(
    buildings: BuildingsInput,
    *,
    dsm_path: str | Path,
    dtm_path: str | Path | None,
    target_crs: str | None,
    auto_utm: bool,
    height_source: HeightSource,
    height_col: str | None,
    default_height: float,
    lidar_percentile: float,
) -> gpd.GeoDataFrame:
    if isinstance(buildings, gpd.GeoDataFrame):
        gdf, _, _ = prepare_buildings_gdf(
            buildings,
            target_crs=target_crs,
            auto_utm=auto_utm,
            height_source=height_source,
            height_col=height_col,
            default_height=default_height,
        )
    else:
        gdf, _, _ = load_buildings_gdf(
            str(buildings),
            target_crs=target_crs,
            auto_utm=auto_utm,
            height_source=height_source,
            height_col=height_col,
            default_height=default_height,
        )

    return apply_lidar_heights_to_gdf(
        gdf,
        dsm_path,
        dtm_path=dtm_path,
        percentile=lidar_percentile,
        default_height=default_height,
    )
