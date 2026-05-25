"""Tests for LiDAR height sampling and stepped facade meshes."""

import numpy as np
import pytest
from shapely.geometry import Polygon

from cfd_geometry.buildings.facade_mesh import polygon_to_triangles_stepped_facade
from cfd_geometry.buildings.lidar_heights import building_height_from_lidar
from cfd_geometry.mesh.normals import mesh_bounds
from cfd_geometry.raster.elevation import _attach_interpolator


def _flat_elevation_data(z: float = 0.0, size: int = 5) -> dict:
    elev = np.full((size, size), z, dtype=np.float32)
    data = {
        "elevation": elev,
        "bounds": (0.0, 0.0, float(size), float(size)),
        "width": size,
        "height": size,
        "crs": "EPSG:32616",
    }
    _attach_interpolator(data)
    return data


def test_building_height_from_lidar_chm():
    ground = _flat_elevation_data(10.0)
    surface = _flat_elevation_data(25.0)
    poly = Polygon([(1, 1), (3, 1), (3, 3), (1, 3)])
    h = building_height_from_lidar(
        poly, surface, ground_data=ground, default_height=9.0
    )
    assert h == pytest.approx(15.0, rel=0.05)


def test_stepped_facade_follows_sloped_ground():
    size = 6
    elev = np.zeros((size, size), dtype=np.float32)
    for row in range(size):
        elev[row, :] = float(row)
    data = {
        "elevation": elev,
        "bounds": (0.0, 0.0, float(size), float(size)),
        "width": size,
        "height": size,
        "crs": "EPSG:32616",
    }
    _attach_interpolator(data)

    poly = Polygon([(1, 1), (4, 1), (4, 4), (1, 4)])
    tris = polygon_to_triangles_stepped_facade(
        poly, height=5.0, elevation_data=data, z_offset=0.0, samples_per_edge=2
    )
    assert len(tris) > 0
    bounds = mesh_bounds(tris)
    assert bounds["z_min"] < bounds["z_max"]
    assert bounds["z_max"] - bounds["z_min"] >= 4.0
