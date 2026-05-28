"""Tests for trimesh building extrusion."""

import pytest
from shapely.geometry import Polygon

from cfd_geometry.mesh.extrusion import polygon_to_triangles
from cfd_geometry.mesh.normals import mesh_bounds
from cfd_geometry.mesh.trimesh_extrude import extrude_geometry_to_triangles


def test_extrude_l_shape():
    """Non-convex footprint should still produce a valid mesh."""
    poly = Polygon([(0, 0), (10, 0), (10, 5), (5, 5), (5, 10), (0, 10), (0, 0)])
    tris = extrude_geometry_to_triangles(poly, height=8.0, ground_level=0.0)
    assert len(tris) > 0
    bounds = mesh_bounds(tris)
    assert bounds["z_max"] == pytest.approx(8.0)
    assert bounds["z_min"] == pytest.approx(0.0)


def test_l_shape_trimesh_matches_fan_extent():
    """Non-convex L footprint: trimesh extrusion is valid and reaches the same height."""
    poly = Polygon([(0, 0), (10, 0), (10, 5), (5, 5), (5, 10), (0, 10), (0, 0)])
    fan = polygon_to_triangles(poly, height=5.0)
    tris = extrude_geometry_to_triangles(poly, height=5.0)
    assert len(tris) > 0
    assert mesh_bounds(tris)["z_max"] == pytest.approx(5.0)
    assert mesh_bounds(fan)["z_max"] == pytest.approx(5.0)
