"""Tests for DEM dimension capping."""

from cfd_geometry.raster.elevation import _cap_raster_dimensions


def test_cap_raster_dimensions_huge():
    w, h = _cap_raster_dimensions(1_800_000, 1_800_000, max_resolution=800)
    assert max(w, h) <= 800
    assert w * h <= 25_000_000
