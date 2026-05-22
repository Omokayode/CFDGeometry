"""Smoke tests for package imports."""

import pytest

pytest.importorskip("geopandas")


def test_public_api_imports():
    import cfd_geometry as cg

    assert cg.__version__
    assert cg.get_combined_offset
    assert cg.extrude_buildings_to_stl
    assert cg.dem_to_stl_with_offset
    assert cg.STLClipper
    assert cg.OptimizedRectangularBaseGenerator


def test_submodule_imports():
    from cfd_geometry.buildings.extrude_dem import extrude_buildings_to_stl_with_dem
    from cfd_geometry.highways.extrude import extrude_highways_to_stl
    from cfd_geometry.trees.extrude_dem import extrude_trees_to_stl_with_dem

    assert callable(extrude_buildings_to_stl_with_dem)
    assert callable(extrude_highways_to_stl)
    assert callable(extrude_trees_to_stl_with_dem)
