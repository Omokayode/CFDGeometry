"""Tests for CONUS USGS10m product selection."""

from cfd_geometry.download.bbox import Bbox
from cfd_geometry.download.dsm import (
    USGS10M_PRODUCT,
    is_conus_bbox,
    resolve_raster_products,
)


def test_milwaukee_is_conus():
    bbox = Bbox(west=-88.1, south=42.9, east=-87.8, north=43.2)
    assert is_conus_bbox(bbox)


def test_resolve_usgs10m_flag():
    bbox = Bbox(west=-88.1, south=42.9, east=-87.8, north=43.2)
    dsm, dtm, dem = resolve_raster_products(bbox, use_usgs10m=True)
    assert dsm == USGS10M_PRODUCT
    assert dem == USGS10M_PRODUCT


def test_auto_usgs10m_outside_conus():
    bbox = Bbox(west=8.0, south=47.0, east=8.5, north=47.5)
    dsm, dtm, dem = resolve_raster_products(bbox, auto_usgs10m=True)
    assert dsm == "COP30"
    assert dem == "SRTMGL1"
