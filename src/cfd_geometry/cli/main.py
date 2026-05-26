"""CLI entry point: ``cfd-geometry <command> ...``."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _cmd_offset(args: argparse.Namespace) -> int:
    from cfd_geometry.geo.offsets import get_combined_offset

    ox, oy = get_combined_offset(args.shapefiles, args.epsg)
    print(f"offset_x={ox}")
    print(f"offset_y={oy}")
    return 0


def _cmd_buildings(args: argparse.Namespace) -> int:
    from cfd_geometry.buildings.extrude import extrude_buildings_to_stl
    from cfd_geometry.geo.offsets import get_combined_offset, target_epsg_for_shapefiles
    from cfd_geometry.geo.paths import filter_vector_inputs
    from cfd_geometry.mesh.stl_io import validate_stl

    offset = None
    shapefile_list = args.align_with or ([args.shapefile] if args.shapefile else None)
    if shapefile_list:
        shapefile_list = filter_vector_inputs(shapefile_list, label="--align-with")
    if shapefile_list:
        epsg = target_epsg_for_shapefiles(
            shapefile_list, target_epsg=args.epsg, auto_utm=args.auto_utm
        )
        offset = get_combined_offset(shapefile_list, epsg)

    height_source = args.height_source
    if args.no_estimate_heights and height_source == "osm":
        height_source = "column" if args.height_column else "none"

    target_crs = None if args.auto_utm else f"EPSG:{args.epsg}"

    blockmesh_out = None
    if args.blockmesh_output:
        blockmesh_out = args.blockmesh_output
    elif args.ground_buffer is not None and not args.openfoam:
        blockmesh_out = str(Path(args.output).parent / "blockMeshDict")

    stats = extrude_buildings_to_stl(
        args.shapefile,
        args.output,
        height_col=args.height_column,
        height_source=height_source,
        default_height=args.default_height,
        ground_level=args.ground_level,
        estimate_heights=None,
        combined_offset=offset,
        shapefile_list=shapefile_list,
        target_crs=target_crs,
        auto_utm=args.auto_utm,
        ground_buffer=args.ground_buffer,
        blockmesh_output=blockmesh_out,
        ground_stl_output=args.ground_stl,
        workers=max(1, args.workers),
        resolve_overlaps=args.resolve_overlaps or False,
        complement_raster=args.complement_raster,
        simplify_tolerance=args.simplify_tolerance,
    )
    if args.openfoam and stats.get("bounds"):
        from cfd_geometry.openfoam.export import export_openfoam_case

        export_openfoam_case(
            Path(args.output).parent,
            building_bounds=stats["bounds"],
            max_building_height=float(stats.get("max_building_height", 20.0)),
            ground_buffer_m=args.ground_buffer or 500.0,
            stl_files={"buildings": Path(args.output)},
            refinement_buffer_m=args.refinement_buffer_m,
            cell_size=args.openfoam_cell_size,
        )
    if args.validate:
        validate_stl(args.output)
    return 0


def _cmd_terrain(args: argparse.Namespace) -> int:
    from cfd_geometry.terrain.dem_to_stl import dem_to_stl_with_offset

    dem_to_stl_with_offset(
        args.input,
        args.output,
        args.offset_x,
        args.offset_y,
        smooth_sigma=args.smooth,
        max_resolution=args.max_res,
        add_base=not args.no_base,
        target_crs=f"EPSG:{args.epsg}",
        z_reference=args.z_reference,
    )
    return 0


def _cmd_trees(args: argparse.Namespace) -> int:
    from cfd_geometry.geo.offsets import get_combined_offset
    from cfd_geometry.trees.extrude import extrude_trees_to_stl

    offset = None
    if args.align_with:
        from cfd_geometry.geo.offsets import target_epsg_for_shapefiles

        epsg = target_epsg_for_shapefiles(
            args.align_with, target_epsg=args.epsg, auto_utm=args.auto_utm
        )
        offset = get_combined_offset(args.align_with, epsg)

    extrude_trees_to_stl(
        args.shapefile,
        args.output,
        combined_offset=offset,
        alignment_shapefiles=args.align_with,
        default_height=args.default_height,
        tree_model=args.tree_model,
        target_crs=f"EPSG:{args.epsg}",
    )
    return 0


def _cmd_buildings_dem(args: argparse.Namespace) -> int:
    from cfd_geometry.buildings.extrude_dem import extrude_buildings_to_stl_with_dem
    from cfd_geometry.geo.offsets import get_combined_offset

    from cfd_geometry.geo.offsets import target_epsg_for_shapefiles

    offset = None
    align = args.align_with or [args.shapefile]
    if align:
        epsg = target_epsg_for_shapefiles(
            align, target_epsg=args.epsg, auto_utm=args.auto_utm
        )
        offset = get_combined_offset(align, epsg)

    height_source = args.height_source
    if args.no_estimate_heights and height_source == "osm":
        height_source = "column" if getattr(args, "height_column", None) else "none"

    target_crs = None if args.auto_utm else f"EPSG:{args.epsg}"

    extrude_buildings_to_stl_with_dem(
        args.shapefile,
        args.dem,
        args.output,
        height_source=height_source,
        estimate_heights=None,
        combined_offset=offset,
        shapefile_list=align,
        elevation_offset=args.elevation_offset,
        target_crs=target_crs,
        auto_utm=args.auto_utm,
    )
    return 0


def _cmd_trees_dem(args: argparse.Namespace) -> int:
    from cfd_geometry.trees.extrude_dem import extrude_trees_to_stl_with_dem

    extrude_trees_to_stl_with_dem(
        args.shapefile,
        args.dem,
        args.output,
        alignment_shapefiles=args.align_with,
        default_height=args.default_height,
        target_crs=f"EPSG:{args.epsg}",
    )
    return 0


def _cmd_highways(args: argparse.Namespace) -> int:
    from cfd_geometry.geo.offsets import get_combined_offset
    from cfd_geometry.highways.extrude import extrude_highways_to_stl

    from cfd_geometry.geo.offsets import target_epsg_for_shapefiles

    align = args.align_with or [args.shapefile]
    epsg = target_epsg_for_shapefiles(align, target_epsg=args.epsg, auto_utm=args.auto_utm)
    offset = get_combined_offset(align, epsg)
    extrude_highways_to_stl(
        args.shapefile,
        args.output,
        offset_x=offset[0],
        offset_y=offset[1],
        alignment_shapefiles=args.align_with,
        highway_type_column=args.type_column,
        reference_shapefiles=args.clip_to,
        target_crs=f"EPSG:{args.epsg}",
    )
    return 0


def _cmd_domain(args: argparse.Namespace) -> int:
    from cfd_geometry.constants import DEFAULT_PLACE_BUFFER_M
    from cfd_geometry.domain.config import DomainConfig
    from cfd_geometry.domain.pipeline import build_domain
    from cfd_geometry.download.bbox import bbox_from_sequence

    bbox = None
    if args.bbox:
        bbox = bbox_from_sequence(tuple(args.bbox))

    dem_bbox = None
    if args.dem_bbox:
        dem_bbox = bbox_from_sequence(tuple(args.dem_bbox))

    layers = ["buildings"]
    if not args.no_trees:
        layers.append("trees")
    if args.highways:
        layers.append("highways")

    config = DomainConfig(
        output_dir=args.output_dir,
        place=args.place,
        bbox=bbox,
        run_download=not args.no_download,
        download_layers=tuple(layers),
        download_dem=args.dem,
        download_dsm=args.dsm and not args.no_download,
        download_dtm=args.dtm,
        use_dsm_heights=args.dsm,
        use_usgs10m=args.usgs10m,
        auto_usgs10m=args.auto_usgs10m,
        opentopography_dsm_product=args.dsm_product,
        opentopography_dtm_product=args.dtm_product,
        opentopography_demtype=args.dem_product,
        dsm_file=args.dsm_file,
        dtm_file=args.dtm_file,
        dem_file=args.dem_file,
        build_buildings_lidar=args.buildings_lidar,
        stepped_facades=args.stepped_facades,
        place_buffer_m=args.buffer_m or DEFAULT_PLACE_BUFFER_M,
        study_buffer_m=args.study_buffer_m,
        network_timeout=args.timeout,
        build_buildings=True,
        build_trees="trees" in layers and not args.no_trees,
        build_highways=args.highways,
        build_terrain=args.terrain,
        height_source=args.height_source,
        default_height=args.default_height,
        ground_buffer=None if args.no_ground_buffer else args.ground_buffer,
        auto_utm=args.auto_utm,
        target_crs=None if args.auto_utm else f"EPSG:{args.epsg}",
        dem_max_resolution=args.dem_max_res,
        dem_buffer_m=args.dem_buffer_m,
        dem_bbox=dem_bbox,
        workers=max(1, args.workers),
        resolve_overlaps=args.resolve_overlaps or False,
        complement_raster=args.complement_raster,
        simplify_tolerance=args.simplify_tolerance,
        tree_model=args.tree_model,
        canopy_raster=args.canopy_raster,
    )
    build_domain(config)
    return 0


def _cmd_download(args: argparse.Namespace) -> int:
    from cfd_geometry.constants import DEFAULT_PLACE_BUFFER_M
    from cfd_geometry.download.bbox import bbox_from_sequence
    from cfd_geometry.download.config import DownloadConfig
    from cfd_geometry.download.run import download_domain

    bbox = None
    if args.bbox:
        bbox = bbox_from_sequence(tuple(args.bbox))

    dem_bbox = None
    if args.dem_bbox:
        dem_bbox = bbox_from_sequence(tuple(args.dem_bbox))

    layers = tuple(args.layers)
    if args.dem and "dem" not in layers:
        layers = layers + ("dem",)

    config = DownloadConfig(
        output_dir=args.output_dir,
        place=args.place,
        bbox=bbox,
        layers=layers,
        download_dem=args.dem,
        download_dsm=getattr(args, "dsm", False),
        download_dtm=getattr(args, "dtm", False),
        use_usgs10m=getattr(args, "usgs10m", False),
        auto_usgs10m=getattr(args, "auto_usgs10m", False),
        opentopography_dsm_product=getattr(args, "dsm_product", "COP30"),
        opentopography_dtm_product=getattr(args, "dtm_product", "SRTMGL1"),
        opentopography_demtype=getattr(args, "dem_product", "SRTMGL1"),
        network_timeout=args.timeout,
        place_buffer_m=args.buffer_m or DEFAULT_PLACE_BUFFER_M,
        study_buffer_m=args.study_buffer_m,
        dem_buffer_m=args.dem_buffer_m,
        dem_bbox=dem_bbox,
    )
    download_domain(config)
    return 0


def _cmd_clip(args: argparse.Namespace) -> int:
    from cfd_geometry.clipper.clipper import clip_stl_to_bounds

    return clip_stl_to_bounds(
        args.input,
        args.output,
        args.bounds,
        ascii_output=args.ascii,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cfd-geometry",
        description="Convert GIS/DEM data to STL for urban wind CFD",
        epilog=(
            "OpenFOAM: use --openfoam on 'domain' or 'buildings'. "
            "Docs: https://omokayode.github.io/CFDGeometry/"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--epsg",
        type=int,
        default=32616,
        help="Target EPSG when --no-auto-utm (default: 32616)",
    )
    parser.add_argument(
        "--auto-utm",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Auto-select UTM zone for geographic (EPSG:4326) inputs (default: on)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_offset = sub.add_parser("offset", help="Compute combined shapefile offset")
    p_offset.add_argument("shapefiles", nargs="+", help="Shapefile paths")
    p_offset.set_defaults(func=_cmd_offset)

    p_b = sub.add_parser("buildings", help="Extrude building shapefile to STL")
    p_b.add_argument("shapefile", help="Input building .shp")
    p_b.add_argument("-o", "--output", required=True, help="Output STL path")
    p_b.add_argument(
        "--align-with",
        nargs="+",
        help="Shapefiles used to compute shared offset (include buildings + trees, etc.)",
    )
    p_b.add_argument("--height-column", default=None)
    p_b.add_argument(
        "--height-source",
        choices=["osm", "area", "column", "composite", "raster", "default", "none"],
        default="osm",
        help="Height strategy: osm, area, column, composite (recommended), raster, default",
    )
    p_b.add_argument(
        "--resolve-overlaps",
        choices=["fast", "precise"],
        default=None,
        help="Drop or clip overlapping footprints before extrusion",
    )
    p_b.add_argument(
        "--complement-raster",
        default=None,
        metavar="PATH",
        help="GeoTIFF to fill missing heights (used with composite/raster sources)",
    )
    p_b.add_argument(
        "--simplify-tolerance",
        type=float,
        default=None,
        metavar="M",
        help="Douglas-Peucker simplify tolerance in meters (optional)",
    )
    p_b.add_argument("--default-height", type=float, default=9.0)
    p_b.add_argument("--ground-level", type=float, default=0.0)
    p_b.add_argument(
        "--no-estimate-heights",
        action="store_true",
        help="Legacy: use --height-column or --default-height only (sets source to column/none)",
    )
    p_b.add_argument(
        "--ground-buffer",
        type=float,
        default=None,
        metavar="METERS",
        help="Padding around building bounds for blockMesh outer box",
    )
    p_b.add_argument(
        "--blockmesh-output",
        default=None,
        help="Write blockMeshDict to this path (default: blockMeshDict next to STL)",
    )
    p_b.add_argument(
        "--openfoam",
        action="store_true",
        help="Write blockMeshDict + snappyHexMeshDict",
    )
    p_b.add_argument("--refinement-buffer-m", type=float, default=10.0)
    p_b.add_argument("--openfoam-cell-size", type=float, default=5.0)
    p_b.add_argument(
        "--ground-stl",
        default=None,
        help="Optional flat ground plane STL path",
    )
    p_b.add_argument("--validate", action="store_true")
    p_b.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Parallel workers for extrusion (default: 1)",
    )
    p_b.set_defaults(func=_cmd_buildings)

    p_t = sub.add_parser("terrain", help="Convert DEM GeoTIFF to STL")
    p_t.add_argument("input", help="Input DEM .tif")
    p_t.add_argument("-o", "--output", required=True)
    p_t.add_argument("--offset-x", type=float, required=True)
    p_t.add_argument("--offset-y", type=float, required=True)
    p_t.add_argument("--smooth", type=float, default=0.0)
    p_t.add_argument("--max-res", type=int, default=None)
    p_t.add_argument("--no-base", action="store_true")
    p_t.add_argument(
        "--z-reference",
        choices=["center", "min", "none"],
        default="center",
        help="Subtract DEM elevation so terrain aligns with buildings at z=0 (default: center)",
    )
    p_t.set_defaults(func=_cmd_terrain)

    p_tr = sub.add_parser("trees", help="Convert tree point shapefile to STL")
    p_tr.add_argument("shapefile")
    p_tr.add_argument("-o", "--output", required=True)
    p_tr.add_argument("--align-with", nargs="+")
    p_tr.add_argument("--default-height", type=float, default=10.0)
    p_tr.add_argument(
        "--tree-model",
        choices=["canopy", "cylinder", "sphere", "skip"],
        default="canopy",
        help="Tree mesh shape (default: canopy)",
    )
    p_tr.set_defaults(func=_cmd_trees)

    p_bd = sub.add_parser("buildings-dem", help="Extrude buildings onto a DEM surface")
    p_bd.add_argument("shapefile")
    p_bd.add_argument("dem", help="Elevation GeoTIFF")
    p_bd.add_argument("-o", "--output", required=True)
    p_bd.add_argument("--align-with", nargs="+")
    p_bd.add_argument("--elevation-offset", type=float, default=0.0)
    p_bd.add_argument(
        "--height-source",
        choices=["osm", "area", "column", "none"],
        default="osm",
    )
    p_bd.add_argument("--no-estimate-heights", action="store_true")
    p_bd.set_defaults(func=_cmd_buildings_dem)

    p_td = sub.add_parser("trees-dem", help="Place trees on a DEM surface")
    p_td.add_argument("shapefile")
    p_td.add_argument("dem")
    p_td.add_argument("-o", "--output", required=True)
    p_td.add_argument("--align-with", nargs="+")
    p_td.add_argument("--default-height", type=float, default=10.0)
    p_td.set_defaults(func=_cmd_trees_dem)

    p_hw = sub.add_parser("highways", help="Extrude highway linework to STL")
    p_hw.add_argument("shapefile")
    p_hw.add_argument("-o", "--output", required=True)
    p_hw.add_argument("--align-with", nargs="+")
    p_hw.add_argument("--clip-to", nargs="+", help="Reference shapefiles for spatial clip")
    p_hw.add_argument("--type-column", default=None)
    p_hw.set_defaults(func=_cmd_highways)

    p_dom = sub.add_parser(
        "domain",
        help="Download OSM inputs and extrude aligned STLs (full pipeline)",
    )
    p_dom.add_argument(
        "-o",
        "--output-dir",
        required=True,
        help="Project folder (creates input/ and output/ subdirs)",
    )
    dom_place = p_dom.add_mutually_exclusive_group(required=True)
    dom_place.add_argument("--place", help="Geocoded area or street name")
    dom_place.add_argument(
        "--bbox",
        nargs=4,
        type=float,
        metavar=("WEST", "SOUTH", "EAST", "NORTH"),
    )
    p_dom.add_argument(
        "--no-download",
        action="store_true",
        help="Skip OSM download; use existing files in output-dir/input/",
    )
    p_dom.add_argument(
        "--no-trees",
        action="store_true",
        help="Skip tree download and trees.stl",
    )
    p_dom.add_argument(
        "--highways",
        action="store_true",
        help="Include highway linework download and highways.stl",
    )
    p_dom.add_argument(
        "--dem",
        action="store_true",
        help="Download DEM (OpenTopography API key) and buildings_on_dem.stl",
    )
    p_dom.add_argument(
        "--dsm",
        action="store_true",
        help="Download DSM via OpenTopography (COP30 default) and buildings_lidar.stl",
    )
    p_dom.add_argument(
        "--dtm",
        action="store_true",
        help="Also download DTM for CHM heights (pairs with --dsm; default SRTMGL1)",
    )
    p_dom.add_argument(
        "--usgs10m",
        action="store_true",
        help="Use USGS 3DEP 10 m for dem/dsm/dtm downloads (CONUS, OpenTopography)",
    )
    p_dom.add_argument(
        "--auto-usgs10m",
        action="store_true",
        help="Use USGS10m when study bbox is in CONUS, else COP30/SRTM (default products)",
    )
    p_dom.add_argument(
        "--dem-product",
        default="SRTMGL1",
        metavar="NAME",
        help="OpenTopography terrain DEM: SRTMGL1 (default), USGS10m, USGS30m, ...",
    )
    p_dom.add_argument(
        "--dsm-product",
        default="COP30",
        metavar="NAME",
        help="OpenTopography DSM: COP30 (default), USGS10m (CONUS), ...",
    )
    p_dom.add_argument(
        "--dtm-product",
        default="SRTMGL1",
        metavar="NAME",
        help="OpenTopography DTM for CHM: SRTMGL1 (default), USGS10m, ...",
    )
    p_dom.add_argument(
        "--dsm-file",
        default=None,
        metavar="PATH",
        help="Upload: copy GeoTIFF to input/dsm.tif (skip download if present)",
    )
    p_dom.add_argument(
        "--dtm-file",
        default=None,
        metavar="PATH",
        help="Upload: copy GeoTIFF to input/dtm.tif",
    )
    p_dom.add_argument(
        "--dem-file",
        default=None,
        metavar="PATH",
        help="Upload: copy GeoTIFF to input/dem.tif",
    )
    p_dom.add_argument(
        "--buildings-lidar",
        action="store_true",
        help="Build buildings_lidar.stl when dsm.tif exists (on by default with --dsm)",
    )
    p_dom.add_argument(
        "--stepped-facades",
        action="store_true",
        help="DEM-following base ring for LiDAR building extrusion",
    )
    p_dom.add_argument(
        "--terrain",
        action="store_true",
        help="Build terrain.stl from dem.tif (requires --dem or existing dem.tif)",
    )
    p_dom.add_argument(
        "--study-buffer-m",
        type=float,
        default=None,
        help="Set both OSM and DEM padding to the same value (overrides --buffer-m and --dem-buffer-m)",
    )
    p_dom.add_argument(
        "--buffer-m",
        type=float,
        default=None,
        help="Buffer for street/point geocoding in meters (~500x500 m at 250, default)",
    )
    p_dom.add_argument("--timeout", type=int, default=180)
    p_dom.add_argument(
        "--height-source",
        choices=["osm", "area", "column", "composite", "raster", "default", "none"],
        default="composite",
        help="Height strategy (composite = column + OSM + area + optional raster fill)",
    )
    p_dom.add_argument(
        "--resolve-overlaps",
        choices=["fast", "precise"],
        default=None,
        help="Resolve overlapping building footprints",
    )
    p_dom.add_argument("--complement-raster", default=None, metavar="PATH")
    p_dom.add_argument("--simplify-tolerance", type=float, default=None, metavar="M")
    p_dom.add_argument("--default-height", type=float, default=9.0)
    p_dom.add_argument(
        "--tree-model",
        choices=["canopy", "cylinder", "sphere", "skip"],
        default="canopy",
    )
    p_dom.add_argument(
        "--canopy-raster",
        default=None,
        metavar="PATH",
        help="Canopy height GeoTIFF (e.g. from VoxCity/ETH export); samples OSM tree points",
    )
    p_dom.add_argument(
        "--ground-buffer",
        type=float,
        default=500.0,
        help="OpenFOAM domain padding and blockMesh snippet (default: 500 m)",
    )
    p_dom.add_argument(
        "--no-ground-buffer",
        action="store_true",
        help="Disable ground buffer padding (still used for --openfoam outer box)",
    )
    p_dom.add_argument(
        "--openfoam",
        action="store_true",
        help="Write blockMeshDict and snappyHexMeshDict under output/",
    )
    p_dom.add_argument(
        "--refinement-buffer-m",
        type=float,
        default=10.0,
        help="snappyHexMesh refinementBox padding around buildings (default: 10 m)",
    )
    p_dom.add_argument(
        "--openfoam-cell-size",
        type=float,
        default=5.0,
        help="Target blockMesh cell size in metres (default: 5)",
    )
    p_dom.add_argument(
        "--dem-max-res",
        type=int,
        default=800,
        help="Max DEM raster dimension for terrain STL (default: 800)",
    )
    p_dom.add_argument(
        "--dem-buffer-m",
        type=float,
        default=200.0,
        help="DEM download padding on all sides in meters (default: 200)",
    )
    p_dom.add_argument(
        "--dem-bbox",
        nargs=4,
        type=float,
        metavar=("WEST", "SOUTH", "EAST", "NORTH"),
        help="Explicit WGS84 DEM bounds (overrides --dem-buffer-m)",
    )
    p_dom.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Parallel workers for building extrusion (default: 1)",
    )
    p_dom.set_defaults(func=_cmd_domain)

    p_dl = sub.add_parser(
        "download",
        help="Download OSM buildings/trees/highways (optional DEM) for a place or bbox",
    )
    p_dl.add_argument(
        "-o",
        "--output-dir",
        required=True,
        help="Directory for shapefiles and dem.tif (e.g. data/input)",
    )
    place = p_dl.add_mutually_exclusive_group(required=True)
    place.add_argument(
        "--place",
        help='Geocoded area name, e.g. "Milwaukee, Wisconsin, USA"',
    )
    place.add_argument(
        "--bbox",
        nargs=4,
        type=float,
        metavar=("WEST", "SOUTH", "EAST", "NORTH"),
        help="WGS84 bounds in degrees (west south east north)",
    )
    p_dl.add_argument(
        "--layers",
        nargs="+",
        choices=["buildings", "trees", "highways"],
        default=["buildings", "trees", "highways"],
        help="OSM vector layers to fetch (default: all three)",
    )
    p_dl.add_argument(
        "--dem",
        action="store_true",
        help="Also download SRTM DEM via OpenTopography (needs OPENTOPOGRAPHY_API_KEY)",
    )
    p_dl.add_argument(
        "--dsm",
        action="store_true",
        help="Download DSM (Copernicus COP30 by default) for LiDAR building heights",
    )
    p_dl.add_argument(
        "--dtm",
        action="store_true",
        help="Download DTM companion raster (default SRTMGL1) for CHM heights",
    )
    p_dl.add_argument(
        "--usgs10m",
        action="store_true",
        help="Use USGS 3DEP 10 m for dem/dsm/dtm (CONUS)",
    )
    p_dl.add_argument(
        "--auto-usgs10m",
        action="store_true",
        help="Pick USGS10m in CONUS, else global defaults",
    )
    p_dl.add_argument(
        "--dem-product",
        default="SRTMGL1",
        metavar="NAME",
        help="Terrain DEM product (default SRTMGL1)",
    )
    p_dl.add_argument(
        "--dsm-product",
        default="COP30",
        metavar="NAME",
        help="OpenTopography DSM product (default COP30)",
    )
    p_dl.add_argument(
        "--dtm-product",
        default="SRTMGL1",
        metavar="NAME",
        help="OpenTopography DTM product when using --dtm",
    )
    p_dl.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="OSM network timeout in seconds (default: 180)",
    )
    p_dl.add_argument(
        "--study-buffer-m",
        type=float,
        default=None,
        help="Set OSM and DEM padding to the same value (overrides --buffer-m and --dem-buffer-m)",
    )
    p_dl.add_argument(
        "--buffer-m",
        type=float,
        default=None,
        help="Street/point buffer in meters (~500 m box at 250; default: 250)",
    )
    p_dl.add_argument(
        "--dem-buffer-m",
        type=float,
        default=200.0,
        help="DEM padding around buildings in meters (default: 200)",
    )
    p_dl.add_argument(
        "--dem-bbox",
        nargs=4,
        type=float,
        metavar=("WEST", "SOUTH", "EAST", "NORTH"),
        help="Explicit WGS84 DEM bounds (overrides --dem-buffer-m)",
    )
    p_dl.set_defaults(func=_cmd_download)

    p_c = sub.add_parser("clip", help="Clip STL to a bounding box")
    p_c.add_argument("input")
    p_c.add_argument("-o", "--output", required=True)
    p_c.add_argument(
        "--bounds",
        nargs=6,
        type=float,
        required=True,
        metavar=("XMIN", "YMIN", "ZMIN", "XMAX", "YMAX", "ZMAX"),
    )
    p_c.add_argument("--ascii", action="store_true")
    p_c.set_defaults(func=_cmd_clip)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as e:
        import traceback

        print(f"Error: {e}", file=sys.stderr)
        if os.environ.get("CFD_GEOMETRY_DEBUG"):
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
