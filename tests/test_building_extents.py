"""Tests for DEM bbox sizing from buildings."""

from shapely.geometry import Polygon

import geopandas as gpd

from cfd_geometry.buildings.extents import dem_download_bbox_from_buildings
from cfd_geometry.download.bbox import Bbox


def test_dem_bbox_expands_beyond_footprint(tmp_path):
    shp = tmp_path / "b.shp"
    gdf = gpd.GeoDataFrame(
        {
            "geometry": [Polygon([(0, 0), (100, 0), (100, 100), (0, 100)])],
            "estimated_height": [10.0],
        },
        crs="EPSG:32616",
    )
    gdf.to_file(shp)

    dem_bbox, max_h, buf = dem_download_bbox_from_buildings(
        shp,
        height_source="column",
        height_col="estimated_height",
        buffer_height_factor=15.0,
        min_buffer_m=50.0,
    )
    assert max_h == 10.0
    assert buf == 150.0
    assert dem_bbox.west < 0 or dem_bbox.south < 0
