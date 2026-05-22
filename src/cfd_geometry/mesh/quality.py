"""STL mesh quality checks."""

from __future__ import annotations

import struct
from pathlib import Path


def count_non_finite_stl_vertices(stl_path: str | Path) -> int:
    """Return how many triangle vertices in a binary STL are non-finite."""
    stl_path = Path(stl_path)
    bad = 0
    with stl_path.open("rb") as f:
        f.read(80)
        n_tri = struct.unpack("<I", f.read(4))[0]
        for _ in range(n_tri):
            f.read(12)  # normal
            for _ in range(3):
                x, y, z = struct.unpack("<fff", f.read(12))
                if not all(map(_finite, (x, y, z))):
                    bad += 1
            f.read(2)
    return bad


def _finite(value: float) -> bool:
    return value == value and abs(value) < 1e30


def verify_stl_finite_vertices(stl_path: str | Path, *, label: str = "STL") -> None:
    """Raise if any STL vertex coordinates are NaN or infinite."""
    bad = count_non_finite_stl_vertices(stl_path)
    if bad:
        raise ValueError(
            f"{label} {stl_path} has {bad} triangle vertex/vertices with non-finite "
            "coordinates (NaN/inf). Rebuild DEM/terrain or check inputs."
        )
    print(f"  Verified {label}: all vertices finite ({stl_path})")
