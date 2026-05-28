"""Tests for align-with path filtering."""

import pytest

from cfd_geometry.geo.paths import filter_vector_inputs


def test_filter_skips_stl():
    paths = filter_vector_inputs(
        ["buildings.shp", "output.stl", "trees.shp"],
        label="test",
    )
    assert paths == ["buildings.shp", "trees.shp"]


def test_filter_raises_when_only_stl():
    with pytest.raises(ValueError, match="No vector layers"):
        filter_vector_inputs(["out.stl"], label="test")
