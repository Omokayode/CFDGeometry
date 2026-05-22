"""Download vector layers from OpenStreetMap via OSMnx."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd

from cfd_geometry.download.bbox import Bbox

BUILDING_TAGS = {"building": True}
TREE_TAGS = {"natural": "tree"}
HIGHWAY_TAGS = {
    "highway": [
        "motorway",
        "trunk",
        "primary",
        "secondary",
        "tertiary",
        "residential",
        "unclassified",
        "service",
        "living_street",
    ]
}


def _import_osmnx():
    try:
        import osmnx as ox

        return ox
    except ImportError as exc:
        raise RuntimeError(
            "OSM download requires osmnx. Install with:\n"
            "  pip install -e '.[download]'"
        ) from exc


def resolve_bbox(
    *,
    place: str | None,
    bbox: Bbox | None,
    timeout: int,
) -> Bbox:
    """Resolve a place name to WGS84 bounds or validate a supplied bbox."""
    ox = _import_osmnx()
    ox.settings.timeout = timeout

    if bbox is not None:
        bbox.validate()
        return bbox

    assert place is not None
    print(f"Geocoding place: {place}")
    gdf = ox.geocode_to_gdf(place)
    bounds = gdf.total_bounds
    resolved = Bbox(
        west=float(bounds[0]),
        south=float(bounds[1]),
        east=float(bounds[2]),
        north=float(bounds[3]),
    )
    resolved.validate()
    print(
        f"Bounds (WGS84): west={resolved.west:.5f} south={resolved.south:.5f} "
        f"east={resolved.east:.5f} north={resolved.north:.5f}"
    )
    return resolved


def _features_for_bbox(bbox: Bbox, tags: dict, timeout: int) -> gpd.GeoDataFrame:
    ox = _import_osmnx()
    ox.settings.timeout = timeout
    print(f"Querying OSM: {tags}")
    gdf = ox.features_from_bbox(bbox=bbox.as_osmnx_tuple(), tags=tags)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    return gdf.to_crs("EPSG:4326")


def _filter_geom_types(gdf: gpd.GeoDataFrame, types: set[str]) -> gpd.GeoDataFrame:
    if gdf.empty:
        return gdf
    mask = gdf.geometry.geom_type.isin(types)
    return gdf.loc[mask].copy()


def _save_shapefile(gdf: gpd.GeoDataFrame, path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(path)
    return len(gdf)


def download_buildings(bbox: Bbox, path: Path, *, timeout: int) -> int:
    gdf = _features_for_bbox(bbox, BUILDING_TAGS, timeout)
    gdf = _filter_geom_types(gdf, {"Polygon", "MultiPolygon"})
    if gdf.empty:
        print(f"Warning: no building polygons; skipping {path}")
        return 0
    count = _save_shapefile(gdf, path)
    print(f"Wrote {count} buildings -> {path}")
    return count


def download_trees(bbox: Bbox, path: Path, *, timeout: int) -> int:
    gdf = _features_for_bbox(bbox, TREE_TAGS, timeout)
    gdf = _filter_geom_types(gdf, {"Point", "MultiPoint"})
    if not gdf.empty and "MultiPoint" in set(gdf.geometry.geom_type):
        gdf = gdf.explode(index_parts=False)
        gdf = _filter_geom_types(gdf, {"Point"})
    if gdf.empty:
        print(f"Warning: no tree points; skipping {path}")
        return 0
    count = _save_shapefile(gdf, path)
    print(f"Wrote {count} trees -> {path}")
    return count


def download_highways(bbox: Bbox, path: Path, *, timeout: int) -> int:
    gdf = _features_for_bbox(bbox, HIGHWAY_TAGS, timeout)
    gdf = _filter_geom_types(
        gdf, {"LineString", "MultiLineString", "Polygon", "MultiPolygon"}
    )
    if gdf.empty:
        print(f"Warning: no highways; skipping {path}")
        return 0
    count = _save_shapefile(gdf, path)
    print(f"Wrote {count} highway features -> {path}")
    return count
