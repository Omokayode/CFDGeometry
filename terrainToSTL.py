"""Backward-compatible shim — use ``cfd-geometry terrain`` or ``cfd_geometry.terrain``."""

import warnings

warnings.warn(
    "Use cfd_geometry.terrain.dem_to_stl_with_offset or: cfd-geometry terrain ...",
    DeprecationWarning,
    stacklevel=2,
)

from cfd_geometry.raster.elevation import load_elevation_raster, preprocess_elevation  # noqa: F401
from cfd_geometry.terrain.dem_to_stl import dem_to_stl_with_offset  # noqa: F401
from cfd_geometry.terrain.mesh import (  # noqa: F401
    add_base_and_sides,
    create_terrain_mesh_with_offset,
    create_triangular_mesh,
)

if __name__ == "__main__":
    from cfd_geometry.cli.main import main
    import sys

    sys.argv = ["cfd-geometry", "terrain", *sys.argv[1:]]
    raise SystemExit(main())
