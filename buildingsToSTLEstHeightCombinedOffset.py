"""Backward-compatible shim — use ``cfd-geometry buildings`` or ``cfd_geometry.buildings``."""

import warnings

warnings.warn(
    "Use cfd_geometry.buildings.extrude_buildings_to_stl or: cfd-geometry buildings ...",
    DeprecationWarning,
    stacklevel=2,
)

from cfd_geometry.buildings.extrude import (  # noqa: F401
    extrude_buildings_to_stl,
    extrude_buildings_to_stl as extrude_buildings_with_height_estimation,
    process_shapefiles_to_stl as process_multiple_shapefiles_with_combined_offset,
)
from cfd_geometry.buildings.heights import estimate_heights_from_footprint_area  # noqa: F401
from cfd_geometry.geo.crs import fix_shapefile_crs  # noqa: F401
from cfd_geometry.geo.offsets import get_combined_offset, get_local_transform  # noqa: F401
from cfd_geometry.mesh.extrusion import polygon_to_triangles, triangulate_2d  # noqa: F401
from cfd_geometry.mesh.stl_io import validate_stl, write_stl_binary  # noqa: F401
