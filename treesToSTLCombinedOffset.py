"""Backward-compatible shim — use ``cfd-geometry trees`` or ``cfd_geometry.trees``."""

import warnings

warnings.warn(
    "Use cfd_geometry.trees.extrude_trees_to_stl or: cfd-geometry trees ...",
    DeprecationWarning,
    stacklevel=2,
)

from cfd_geometry.geo.crs import fix_shapefile_crs  # noqa: F401
from cfd_geometry.geo.offsets import get_combined_offset  # noqa: F401
from cfd_geometry.trees.extrude import (  # noqa: F401
    extrude_trees_to_stl,
    extrude_trees_to_stl as shapefile_points_to_trees_aligned,
)
from cfd_geometry.trees.geometry import create_tree_canopy, default_tree_config  # noqa: F401
from cfd_geometry.mesh.stl_io import write_stl_binary, validate_stl as validate_tree_stl  # noqa: F401
