"""Triangle normal and bounds helpers."""

from __future__ import annotations

import numpy as np


def calculate_normal(tri: list) -> np.ndarray:
    """Unit normal for a triangle (three vertices)."""
    a, b, c = np.array(tri[0]), np.array(tri[1]), np.array(tri[2])
    normal = np.cross(b - a, c - a)
    norm = np.linalg.norm(normal)
    return normal / norm if norm > 1e-10 else np.array([0.0, 0.0, 1.0])


def mesh_bounds(triangles: list) -> dict[str, float]:
    """Axis-aligned bounds for a list of triangles."""
    if not triangles:
        return {}
    points = np.array([p for tri in triangles for p in tri])
    return {
        "x_min": float(points[:, 0].min()),
        "x_max": float(points[:, 0].max()),
        "y_min": float(points[:, 1].min()),
        "y_max": float(points[:, 1].max()),
        "z_min": float(points[:, 2].min()),
        "z_max": float(points[:, 2].max()),
    }
