"""Backward-compatible shim — use ``cfd-geometry highways``."""

import warnings

warnings.warn(
    "Use cfd_geometry.highways.extrude_highways_to_stl or: cfd-geometry highways ...",
    DeprecationWarning,
    stacklevel=2,
)

from cfd_geometry.highways.extrude import extrude_highways_to_stl  # noqa: F401
from cfd_geometry.highways.geometry import create_highway_geometry, default_highway_config  # noqa: F401
