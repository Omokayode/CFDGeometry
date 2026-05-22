"""Tests for in-memory building GeoDataFrame extrusion."""

import geopandas as gpd
from shapely.geometry import Polygon

from cfd_geometry.buildings.extrude import extrude_buildings_gdf_to_stl
from cfd_geometry.buildings.load import prepare_buildings_gdf, resolve_height_column
from cfd_geometry.mesh.stl_io import validate_stl


def test_resolve_height_column_voxcity_style():
    gdf = gpd.GeoDataFrame(
        {"height": [12.0], "min_height": [100.0], "id": [1]},
        geometry=[Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])],
        crs="EPSG:32616",
    )
    assert resolve_height_column(gdf, None) == "height"


def test_extrude_buildings_gdf_to_stl(tmp_path):
    gdf = gpd.GeoDataFrame(
        {"height": [15.0], "id": [42]},
        geometry=[Polygon([(0, 0), (20, 0), (20, 20), (0, 20)])],
        crs="EPSG:32616",
    )
    prepared, crs, hcol = prepare_buildings_gdf(
        gdf, height_source="column", auto_utm=False, target_crs="EPSG:32616"
    )
    out = tmp_path / "b.stl"
    stats = extrude_buildings_gdf_to_stl(
        prepared,
        out,
        resolved_crs=crs,
        active_height_col=hcol,
        use_local_coords=True,
    )
    assert stats["buildings_processed"] == 1
    assert out.exists()
    validate_stl(str(out))
