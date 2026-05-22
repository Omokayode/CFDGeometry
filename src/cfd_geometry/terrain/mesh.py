"""Terrain surface mesh generation from elevation grids."""

from __future__ import annotations

import numpy as np


def create_terrain_mesh_with_offset(
    elevation_data: dict,
    offset_x: float,
    offset_y: float,
    scale_factor: float = 1.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build X, Y, Z grids from raster data with a local coordinate offset."""
    elevation = elevation_data["elevation"]
    bounds = elevation_data["bounds"]
    rows, cols = elevation.shape

    x_coords = np.linspace(bounds[0] - offset_x, bounds[2] - offset_x, cols) * scale_factor
    y_coords = np.linspace(bounds[3] - offset_y, bounds[1] - offset_y, rows) * scale_factor
    X, Y = np.meshgrid(x_coords, y_coords)
    Z = elevation
    return X, Y, Z


def create_triangular_mesh(X: np.ndarray, Y: np.ndarray, Z: np.ndarray) -> list:
    """Triangulate a regular height grid (two triangles per cell)."""
    rows, cols = X.shape
    triangles = []
    for i in range(rows - 1):
        for j in range(cols - 1):
            v1 = [X[i, j], Y[i, j], Z[i, j]]
            v2 = [X[i, j + 1], Y[i, j + 1], Z[i, j + 1]]
            v3 = [X[i + 1, j], Y[i + 1, j], Z[i + 1, j]]
            v4 = [X[i + 1, j + 1], Y[i + 1, j + 1], Z[i + 1, j + 1]]
            triangles.append([v1, v3, v2])
            triangles.append([v2, v3, v4])
    return triangles


def add_base_and_sides(triangles: list, base_thickness: float = 1.0) -> list:
    """Add a flat bottom cap below the terrain minimum Z."""
    if not triangles:
        return triangles

    all_vertices = np.array([p for tri in triangles for p in tri])
    min_x, max_x = np.min(all_vertices[:, 0]), np.max(all_vertices[:, 0])
    min_y, max_y = np.min(all_vertices[:, 1]), np.max(all_vertices[:, 1])
    min_z = np.min(all_vertices[:, 2])
    base_z = min_z - base_thickness

    base_vertices = [
        [min_x, min_y, base_z],
        [max_x, min_y, base_z],
        [max_x, max_y, base_z],
        [min_x, max_y, base_z],
    ]
    triangles.extend(
        [
            [base_vertices[0], base_vertices[2], base_vertices[1]],
            [base_vertices[0], base_vertices[3], base_vertices[2]],
        ]
    )
    return triangles
