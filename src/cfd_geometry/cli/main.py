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
    from cfd_geometry.geo.offsets import get_combined_offset
    from cfd_geometry.mesh.stl_io import validate_stl

    offset = None
    shapefile_list = args.align_with or ([args.shapefile] if args.shapefile else None)
    if shapefile_list:
        offset = get_combined_offset(shapefile_list, args.epsg)

    extrude_buildings_to_stl(
        args.shapefile,
        args.output,
        height_col=args.height_column,
        default_height=args.default_height,
        ground_level=args.ground_level,
        estimate_heights=not args.no_estimate_heights,
        combined_offset=offset,
        shapefile_list=shapefile_list,
        target_crs=f"EPSG:{args.epsg}",
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
        offset = get_combined_offset(args.align_with, args.epsg)

    extrude_trees_to_stl(
        args.shapefile,
        args.output,
        combined_offset=offset,
        alignment_shapefiles=args.align_with,
        default_height=args.default_height,
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
        help="Target EPSG code (default: 32616)",
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
    p_b.add_argument("--default-height", type=float, default=12.0)
    p_b.add_argument("--ground-level", type=float, default=0.0)
    p_b.add_argument("--no-estimate-heights", action="store_true")
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
