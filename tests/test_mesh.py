"""Unit tests for mesh helpers (no GIS files required)."""

from shapely.geometry import Polygon

from cfd_geometry.mesh.extrusion import (
    polygon_to_triangles,
    polygon_to_triangles_at_elevation,
    triangulate_2d,
)
from cfd_geometry.mesh.normals import calculate_normal, mesh_bounds


def test_triangulate_square():
    coords = [(0, 0), (1, 0), (1, 1), (0, 1)]
    tris = triangulate_2d(coords, z=0.0)
    assert len(tris) == 4


def test_extrude_unit_square():
    poly = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    tris = polygon_to_triangles(poly, height=5.0, ground_level=0.0)
    assert len(tris) > 0
    bounds = mesh_bounds(tris)
    assert bounds["z_max"] == 5.0
    assert bounds["z_min"] == 0.0


def test_extrude_at_elevation():
    poly = Polygon([(0, 0), (2, 0), (2, 2), (0, 2)])
    tris = polygon_to_triangles_at_elevation(poly, height=3.0, ground_elevation=100.0)
    bounds = mesh_bounds(tris)
    assert bounds["z_min"] == 100.0
    assert bounds["z_max"] == 103.0


def test_normal_is_unit_length():
    tri = [[0, 0, 0], [1, 0, 0], [0, 1, 0]]
    n = calculate_normal(tri)
    assert abs((n[0] ** 2 + n[1] ** 2 + n[2] ** 2) ** 0.5 - 1.0) < 1e-6
