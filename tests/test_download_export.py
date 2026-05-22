"""Tests for OSM shapefile export column slimming."""

import geopandas as gpd
from shapely.geometry import Point, Polygon

from cfd_geometry.download.export import prepare_buildings_gdf


def test_prepare_buildings_drops_noisy_osm_columns():
    gdf = gpd.GeoDataFrame(
        {
            "geometry": [Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])],
            "building": ["yes"],
            "building:levels": [3],
            "building:architect:1979": ["Someone"],
            "height": ["12 m"],
        },
        crs="EPSG:4326",
    )
    slim = prepare_buildings_gdf(gdf)
    assert "building:architect:1979" not in slim.columns
    assert "building" in slim.columns
    assert "building_l" in slim.columns
    assert "height" in slim.columns
