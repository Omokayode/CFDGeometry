"""Backward-compatible shim — use ``cfd-geometry clip`` or ``cfd_geometry.clipper``."""

import warnings

warnings.warn(
    "Use cfd_geometry.clipper or: cfd-geometry clip ...",
    DeprecationWarning,
    stacklevel=2,
)

from cfd_geometry.clipper.clipper import STLClipper, clip_stl_to_bounds  # noqa: F401
