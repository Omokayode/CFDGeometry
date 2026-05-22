"""Backward-compatible shim — use ``cfd_geometry.base.OptimizedRectangularBaseGenerator``."""

import warnings

warnings.warn(
    "Import OptimizedRectangularBaseGenerator from cfd_geometry.base",
    DeprecationWarning,
    stacklevel=2,
)

from cfd_geometry.base.terrain_base import OptimizedRectangularBaseGenerator  # noqa: F401
