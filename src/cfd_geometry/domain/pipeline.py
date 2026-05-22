"""Orchestrate download + STL extrusion for a CFD study domain."""

from __future__ import annotations

from pathlib import Path

from cfd_geometry.buildings.extents import dem_download_bbox_around_buildings
from cfd_geometry.domain.config import DomainConfig, DomainResult
from cfd_geometry.download.bbox import Bbox
from cfd_geometry.download.config import DownloadConfig
from cfd_geometry.download.dem import download_dem_opentopography
from cfd_geometry.download.osm import resolve_bbox
from cfd_geometry.download.run import download_domain
from cfd_geometry.geo.offsets import get_combined_offset, target_epsg_for_shapefiles
from cfd_geometry.geo.paths import filter_vector_inputs


def _existing_vector_inputs(config: DomainConfig) -> dict[str, Path]:
    """Map layer name to shapefile if it already exists on disk."""
    candidates = {
        "buildings": config.buildings_shp,
        "trees": config.trees_shp,
        "highways": config.highways_shp,
    }
    return {k: p for k, p in candidates.items() if p.exists()}


def _alignment_shapefiles(inputs: dict[str, Path], config: DomainConfig) -> list[str]:
    """Shapefiles used to compute a shared origin (buildings + trees by default)."""
    paths: list[Path] = []
    if "buildings" in inputs and config.build_buildings:
        paths.append(inputs["buildings"])
    if "trees" in inputs and config.build_trees:
        paths.append(inputs["trees"])
    if not paths:
        paths = list(inputs.values())
    return [str(p) for p in paths]


def _resolve_dem_bbox(
    config: DomainConfig,
    inputs: dict[str, Path],
    *,
    fallback_bbox: Bbox | None,
) -> Bbox:
    """WGS84 bounds for DEM download."""
    if config.dem_bbox is not None:
        print("DEM extent: user-specified bbox")
        return config.dem_bbox
    if "buildings" in inputs:
        return dem_download_bbox_around_buildings(
            inputs["buildings"],
            buffer_m=config.dem_buffer_m,
            fallback_bbox=fallback_bbox,
        )
    return resolve_bbox(
        place=config.place,
        bbox=config.bbox,
        timeout=config.network_timeout,
        place_buffer_m=config.dem_buffer_m,
    )


def build_domain(config: DomainConfig) -> DomainResult:
    """
    Download OSM inputs (optional) and extrude aligned STL layers.

    Writes under ``config.output_dir/input`` and ``config.output_dir/output``.
    """
    config.input_dir.mkdir(parents=True, exist_ok=True)
    config.stl_dir.mkdir(parents=True, exist_ok=True)

    result = DomainResult(config=config)
    inputs: dict[str, Path] = {}

    if config.run_download:
        print("=" * 70)
        print("DOWNLOAD")
        print("=" * 70)
        dl_config = DownloadConfig(
            output_dir=config.input_dir,
            place=config.place,
            bbox=config.bbox,
            layers=config.download_layers,
            download_dem=False,
            place_buffer_m=config.place_buffer_m,
            network_timeout=config.network_timeout,
        )
        dl_result = download_domain(dl_config)
        result.bbox = dl_result.bbox
        inputs.update(dl_result.files)

        if config.download_dem:
            dem_bbox = _resolve_dem_bbox(
                config, inputs, fallback_bbox=dl_result.bbox
            )
            dem_path = config.dem_tif
            download_dem_opentopography(dem_bbox, dem_path)
            inputs["dem"] = dem_path
    else:
        inputs = _existing_vector_inputs(config)
        if not inputs:
            raise FileNotFoundError(
                f"No shapefiles in {config.input_dir}. Run with download enabled "
                "or place buildings.shp / trees.shp there."
            )
        print(f"Using existing inputs in {config.input_dir}")

        if config.download_dem and config.buildings_shp.exists():
            inputs_with_b = {**inputs, "buildings": config.buildings_shp}
            dem_bbox = _resolve_dem_bbox(
                config, inputs_with_b, fallback_bbox=None
            )
            dem_path = config.dem_tif
            download_dem_opentopography(dem_bbox, dem_path)
            inputs["dem"] = dem_path

    result.input_files = dict(inputs)

    align_paths = filter_vector_inputs(
        _alignment_shapefiles(inputs, config),
        label="domain alignment",
    )
    if not align_paths:
        raise RuntimeError("No vector layers available for alignment offset")

    target_epsg = target_epsg_for_shapefiles(
        align_paths,
        target_epsg=int(config.target_crs.split(":")[1])
        if config.target_crs
        else 32616,
        auto_utm=config.auto_utm,
    )
    result.target_crs = f"EPSG:{target_epsg}"
    offset = get_combined_offset(align_paths, target_epsg)
    result.offset = offset

    resolved_crs = None if config.auto_utm else config.target_crs

    print("\n" + "=" * 70)
    print("EXTRUDE STL")
    print("=" * 70)
    print(f"Target CRS: {result.target_crs}")
    print(f"Combined offset: ({offset[0]:.2f}, {offset[1]:.2f})")

    if config.build_buildings and "buildings" in inputs:
        from cfd_geometry.buildings.extrude import extrude_buildings_to_stl

        out = config.stl_dir / "buildings.stl"
        stats = extrude_buildings_to_stl(
            inputs["buildings"],
            out,
            height_source=config.height_source,
            default_height=config.default_height,
            combined_offset=offset,
            shapefile_list=align_paths,
            target_crs=resolved_crs,
            auto_utm=config.auto_utm,
            ground_buffer=config.ground_buffer,
            blockmesh_output=config.stl_dir / "blockMeshDict_vertices.txt",
            workers=config.workers,
        )
        result.stl_files["buildings"] = out
        result.extrude_stats["buildings"] = stats

    if config.build_trees and "trees" in inputs:
        from cfd_geometry.trees.extrude import extrude_trees_to_stl

        out = config.stl_dir / "trees.stl"
        stats = extrude_trees_to_stl(
            str(inputs["trees"]),
            str(out),
            combined_offset=offset,
            alignment_shapefiles=align_paths,
            default_height=config.tree_default_height,
            target_crs=result.target_crs,
        )
        result.stl_files["trees"] = out
        result.extrude_stats["trees"] = stats

    if config.build_highways and "highways" in inputs:
        from cfd_geometry.highways.extrude import extrude_highways_to_stl

        out = config.stl_dir / "highways.stl"
        stats = extrude_highways_to_stl(
            str(inputs["highways"]),
            str(out),
            offset_x=offset[0],
            offset_y=offset[1],
            alignment_shapefiles=align_paths,
            reference_shapefiles=align_paths,
            target_crs=result.target_crs,
        )
        result.stl_files["highways"] = out
        result.extrude_stats["highways"] = stats

    dem_path = inputs.get("dem") or (config.dem_tif if config.dem_tif.exists() else None)
    z_offset: float | None = None
    elevation_data = None

    if dem_path and (
        config.build_terrain
        or (config.build_buildings and "buildings" in inputs)
        or (config.build_trees and "trees" in inputs)
        or (config.build_highways and "highways" in inputs)
    ):
        from cfd_geometry.raster.elevation import (
            ensure_preprocessed_elevation,
            load_elevation_raster,
            resolve_dem_z_offset,
        )

        elevation_data = load_elevation_raster(
            str(dem_path),
            result.target_crs or "EPSG:32616",
            build_interpolator=True,
            max_resolution=config.dem_max_resolution,
        )
        elevation_data = ensure_preprocessed_elevation(
            elevation_data,
            max_resolution=config.dem_max_resolution,
        )
        z_offset = resolve_dem_z_offset(
            elevation_data,
            offset[0],
            offset[1],
            config.terrain_z_reference,
        )

    if config.build_terrain:
        if not dem_path:
            print("Warning: --terrain requested but no dem.tif; skipping terrain STL")
        else:
            from cfd_geometry.terrain.dem_to_stl import dem_to_stl_with_offset

            out = config.stl_dir / "terrain.stl"
            terrain_stats = dem_to_stl_with_offset(
                str(dem_path),
                str(out),
                offset[0],
                offset[1],
                target_crs=result.target_crs,
                max_resolution=config.dem_max_resolution,
                z_reference=config.terrain_z_reference,
                elevation_data=elevation_data,
                z_offset=z_offset,
            )
            result.stl_files["terrain"] = out
            result.extrude_stats["terrain"] = terrain_stats
    if config.build_trees and "trees" in inputs and dem_path:
        from cfd_geometry.trees.extrude_dem import extrude_trees_to_stl_with_dem

        out = config.stl_dir / "trees_on_dem.stl"
        stats = extrude_trees_to_stl_with_dem(
            str(inputs["trees"]),
            dem_path,
            str(out),
            combined_offset=offset,
            alignment_shapefiles=align_paths,
            default_height=config.tree_default_height,
            target_crs=result.target_crs,
            z_reference=config.terrain_z_reference,
            z_offset=z_offset,
            elevation_data=elevation_data,
        )
        result.stl_files["trees_on_dem"] = out
        result.extrude_stats["trees_on_dem"] = stats

    if config.build_buildings and "buildings" in inputs and dem_path:
        from cfd_geometry.buildings.extrude_dem import (
            extrude_buildings_to_stl_with_dem,
        )

        out = config.stl_dir / "buildings_on_dem.stl"
        stats = extrude_buildings_to_stl_with_dem(
            inputs["buildings"],
            dem_path,
            out,
            height_source=config.height_source,
            default_height=config.default_height,
            combined_offset=offset,
            shapefile_list=align_paths,
            target_crs=resolved_crs,
            auto_utm=config.auto_utm,
            z_reference=config.terrain_z_reference,
            z_offset=z_offset,
            elevation_data=elevation_data,
        )
        result.stl_files["buildings_on_dem"] = out
        result.extrude_stats["buildings_on_dem"] = stats

    if config.build_highways and "highways" in inputs and dem_path:
        from cfd_geometry.highways.extrude_dem import extrude_highways_to_stl_with_dem

        out = config.stl_dir / "highways_on_dem.stl"
        stats = extrude_highways_to_stl_with_dem(
            str(inputs["highways"]),
            dem_path,
            str(out),
            offset_x=offset[0],
            offset_y=offset[1],
            alignment_shapefiles=align_paths,
            reference_shapefiles=align_paths,
            target_crs=result.target_crs,
            z_reference=config.terrain_z_reference,
            z_offset=z_offset,
            elevation_data=elevation_data,
        )
        result.stl_files["highways_on_dem"] = out
        result.extrude_stats["highways_on_dem"] = stats

    print("\n" + "=" * 70)
    print("DOMAIN BUILD COMPLETE")
    print("=" * 70)
    for name, path in result.stl_files.items():
        print(f"  {name}: {path}")
    bm = config.stl_dir / "blockMeshDict"
    if bm.exists():
        print(f"  blockMesh: {bm}")
    elif (config.stl_dir / "blockMeshDict_vertices.txt").exists():
        print(f"  blockMesh: {config.stl_dir / 'blockMeshDict_vertices.txt'}")

    from cfd_geometry.domain.summary import write_domain_summary
    from cfd_geometry.mesh.quality import validate_domain_stls

    validate_domain_stls(result.stl_files)
    write_domain_summary(result)

    return result
