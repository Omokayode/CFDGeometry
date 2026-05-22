"""Tests for notebook extent helpers (no widget runtime)."""

import pytest

from cfd_geometry.download.bbox import Bbox
from cfd_geometry.notebook.extent import bbox_from_draw_geojson


def test_bbox_from_rectangle_polygon():
    geo = {
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [-88.0, 43.0],
                    [-87.5, 43.0],
                    [-87.5, 43.5],
                    [-88.0, 43.5],
                    [-88.0, 43.0],
                ]
            ],
        }
    }
    box = bbox_from_draw_geojson(geo)
    assert box == Bbox(west=-88.0, south=43.0, east=-87.5, north=43.5)


def test_bbox_rejects_empty():
    with pytest.raises(ValueError, match="no coordinates"):
        bbox_from_draw_geojson({"geometry": {"type": "Polygon", "coordinates": []}})
