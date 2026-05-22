"""CLI entry point: ``cfd-geometry <command> ...``."""

from __future__ import annotations

import argparse
import sys


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

    extrude_buildings_to_stl(
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
        blockmesh_output=args.blockmesh_output,
        ground_stl_output=args.ground_stl,
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
        choices=["osm", "area", "column", "none"],
        default="osm",
        help="Height assignment: OSM tags (default), footprint area, column, or fixed default",
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
        help="Padding around building bounds; also writes blockMeshDict snippet",
    )
    p_b.add_argument(
        "--blockmesh-output",
        default=None,
        help="Path for blockMeshDict_vertices.txt (default: next to STL)",
    )
    p_b.add_argument(
        "--ground-stl",
        default=None,
        help="Optional flat ground plane STL path",
    )
    p_b.add_argument("--validate", action="store_true")
    p_b.set_defaults(func=_cmd_buildings)

    p_t = sub.add_parser("terrain", help="Convert DEM GeoTIFF to STL")
    p_t.add_argument("input", help="Input DEM .tif")
    p_t.add_argument("-o", "--output", required=True)
    p_t.add_argument("--offset-x", type=float, required=True)
    p_t.add_argument("--offset-y", type=float, required=True)
    p_t.add_argument("--smooth", type=float, default=0.0)
    p_t.add_argument("--max-res", type=int, default=None)
    p_t.add_argument("--no-base", action="store_true")
    p_t.set_defaults(func=_cmd_terrain)

    p_tr = sub.add_parser("trees", help="Convert tree point shapefile to STL")
    p_tr.add_argument("shapefile")
    p_tr.add_argument("-o", "--output", required=True)
    p_tr.add_argument("--align-with", nargs="+")
    p_tr.add_argument("--default-height", type=float, default=10.0)
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
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
