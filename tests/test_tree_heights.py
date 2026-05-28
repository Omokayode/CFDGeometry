"""Tests for tree height assignment."""

import pytest
import geopandas as gpd
import numpy as np
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import Point

from cfd_geometry.trees.heights import assign_tree_heights


def test_assign_tree_heights_osm_column(tmp_path):
    gdf = gpd.GeoDataFrame(
        {"height": ["12 m", None], "geometry": [Point(0, 0), Point(10, 10)]},
        crs="EPSG:32616",
    )
    out = assign_tree_heights(gdf, default_height=5.0)
    assert out.loc[0, "tree_height_m"] == 12.0
    assert out.loc[0, "tree_height_source"] == "osm"
    assert out.loc[1, "tree_height_m"] == 5.0
    assert out.loc[1, "tree_height_source"] == "default"


def test_assign_tree_heights_raster(tmp_path):
    path = tmp_path / "chm.tif"
    data = np.full((10, 10), 15.0, dtype=np.float32)
    transform = from_origin(0, 100, 10, 10)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=10,
        width=10,
        count=1,
        dtype="float32",
        crs="EPSG:32616",
        transform=transform,
    ) as dst:
        dst.write(data, 1)

    gdf = gpd.GeoDataFrame({"geometry": [Point(25, 25)]}, crs="EPSG:32616")
    out = assign_tree_heights(gdf, canopy_raster=path, default_height=5.0)
    assert out.loc[0, "tree_height_source"] == "raster"
    assert out.loc[0, "tree_height_m"] == pytest.approx(15.0)
