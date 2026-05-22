"""Tests for DEM bbox sizing from buildings."""

from shapely.geometry import Polygon

import geopandas as gpd

from cfd_geometry.buildings.extents import dem_download_bbox_around_buildings


def test_dem_bbox_fixed_buffer(tmp_path):
    shp = tmp_path / "b.shp"
    gdf = gpd.GeoDataFrame(
        {"geometry": [Polygon([(0, 0), (100, 0), (100, 100), (0, 100)])]},
        crs="EPSG:32616",
    )
    gdf.to_file(shp)

    dem_bbox = dem_download_bbox_around_buildings(shp, buffer_m=1000.0)
    assert dem_bbox.east > dem_bbox.west
    assert dem_bbox.north > dem_bbox.south
