"""Tests for highway mesh geometry."""

from cfd_geometry.highways.geometry import create_highway_geometry


def test_highway_geometry_with_base_z():
    coords = [(0.0, 0.0), (10.0, 0.0)]
    tris = create_highway_geometry(
        coords, width=4.0, height=0.2, padding=0.0, base_z=[5.0, 6.0]
    )
    assert len(tris) > 0
    zs = [p[2] for tri in tris for p in tri]
    assert min(zs) >= 5.0
    assert max(zs) <= 6.2 + 0.01
