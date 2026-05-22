"""Tests for DEM nodata handling and terrain Z sanity."""

import numpy as np

from cfd_geometry.raster.elevation import (
    _crop_elevation_to_valid_data,
    _fill_invalid_elevation,
    preprocess_elevation,
)
from cfd_geometry.terrain.mesh import create_terrain_mesh_with_offset


def test_fill_invalid_elevation_replaces_nan():
    elev = np.array([[np.nan, 100.0], [100.0, np.nan]], dtype=np.float32)
    out = _fill_invalid_elevation(elev)
    assert np.all(np.isfinite(out))
    assert float(out[0, 0]) == 100.0


def test_crop_elevation_to_valid_data():
    elev = np.full((8, 8), np.nan, dtype=np.float32)
    elev[2:6, 2:6] = 50.0
    data = {
        "elevation": elev,
        "bounds": (0.0, 0.0, 80.0, 80.0),
        "width": 8,
        "height": 8,
    }
    cropped = _crop_elevation_to_valid_data(data)
    assert cropped["elevation"].shape == (4, 4)
    assert np.all(np.isfinite(cropped["elevation"]))


def test_preprocess_marks_preprocessed():
    elev = np.ones((4, 4), dtype=np.float32) * 120.0
    data = {"elevation": elev, "bounds": (0, 0, 40, 40), "width": 4, "height": 4}
    out = preprocess_elevation(data, crop_to_valid=False)
    assert out.get("_preprocessed") is True


def test_terrain_mesh_z_all_finite():
    elev = np.linspace(100, 110, 16).reshape(4, 4).astype(np.float32)
    data = {
        "elevation": elev,
        "bounds": (0.0, 0.0, 100.0, 100.0),
    }
    _, _, z = create_terrain_mesh_with_offset(data, 50.0, 50.0, z_offset=105.0)
    assert np.all(np.isfinite(z))
