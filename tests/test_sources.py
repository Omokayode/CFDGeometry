"""Tests for pluggable height/ground/tree strategies."""

import geopandas as gpd
from shapely.geometry import Polygon

from cfd_geometry.buildings.geometry_prep import repair_building_geometries
from cfd_geometry.buildings.overlaps import resolve_overlapping_footprints
from cfd_geometry.sources.height import (
    AreaHeightSource,
    ColumnHeightSource,
    OsmHeightSource,
    height_source_from_name,
)
from cfd_geometry.sources.trees import (
    CylinderTreeModel,
    SkipTreeModel,
    tree_model_from_name,
)


def test_height_source_osm():
    gdf = gpd.GeoDataFrame(
        {"building": ["residential"], "geometry": [Polygon([(0, 0), (20, 0), (20, 20), (0, 20)])]},
        crs="EPSG:32616",
    )
    out, col = OsmHeightSource().apply(gdf)
    assert col == "estimated_height"
    assert float(out[col].iloc[0]) > 0


def test_height_source_column_auto():
    gdf = gpd.GeoDataFrame(
        {"height": [22.0], "geometry": [Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])]},
        crs="EPSG:32616",
    )
    out, col = ColumnHeightSource().apply(gdf)
    assert col == "height"
    assert out["height"].iloc[0] == 22.0


def test_height_source_factory_composite():
    s = height_source_from_name("composite", default_height=8.0)
    assert s.name == "composite"


def test_repair_invalid_geometry():
    bad = Polygon([(0, 0), (1, 1), (1, 0), (0, 1)])  # bowtie
    gdf = gpd.GeoDataFrame({"geometry": [bad]}, crs="EPSG:32616")
    out, stats = repair_building_geometries(gdf)
    assert stats["output"] >= 1
    assert out.geometry.iloc[0].is_valid


def test_resolve_overlaps_fast():
    a = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    b = Polygon([(5, 5), (15, 5), (15, 15), (5, 15)])
    gdf = gpd.GeoDataFrame({"geometry": [a, b]}, crs="EPSG:32616")
    # 5×5 m overlap on 10×10 m footprints → ratio 0.25
    out, stats = resolve_overlapping_footprints(gdf, method="fast", overlap_ratio_threshold=0.2)
    assert len(out) == 1
    assert stats["removed"] == 1


def test_tree_models():
    from shapely.geometry import Point

    pt = Point(0, 0)
    cfg = {"trunk_height_ratio": 0.3, "canopy_radius_ratio": 0.4, "trunk_radius": 0.1, "detail_level": 6}
    assert len(CylinderTreeModel().triangles_at(pt, height=10.0, cfg=cfg)) > 0
    assert len(SkipTreeModel().triangles_at(pt, height=10.0, cfg=cfg)) == 0
    assert tree_model_from_name("sphere").name == "sphere"
