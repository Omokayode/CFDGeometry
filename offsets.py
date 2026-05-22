"""Backward-compatible shim — use ``cfd_geometry`` or ``cfd-geometry offset``."""

import warnings

warnings.warn(
    "Import from cfd_geometry.geo.offsets or run: cfd-geometry offset ...",
    DeprecationWarning,
    stacklevel=2,
)

from cfd_geometry.geo.offsets import get_combined_offset  # noqa: F401

__all__ = ["get_combined_offset"]
