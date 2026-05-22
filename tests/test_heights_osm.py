"""Tests for OSM-style height estimation."""

import pytest
import pandas as pd

from cfd_geometry.buildings.heights_osm import (
    estimate_height_from_attributes,
    parse_height_string,
)
from cfd_geometry.geo.crs import utm_epsg_from_wgs84_bounds


def test_parse_height_meters():
    assert parse_height_string("45 m") == 45.0
    assert parse_height_string("45m") == 45.0


def test_parse_height_feet_heuristic():
    assert parse_height_string("150") == pytest.approx(150 * 0.3048, rel=1e-3)


def test_parse_height_feet_suffix():
    assert parse_height_string("395 ft") == pytest.approx(395 * 0.3048, rel=1e-3)


def test_parse_height_numeric():
    assert parse_height_string(12) == 12.0


def test_estimate_explicit_height():
    row = pd.Series({"height": "30 m"})
    h, src = estimate_height_from_attributes(row)
    assert h == 30.0
    assert src == "explicit"


def test_estimate_levels():
    row = pd.Series({"building_l": "4", "building": "apartments"})
    h, src = estimate_height_from_attributes(row)
    assert src == "levels"
    assert h == pytest.approx(4 * 3.2)


def test_estimate_building_type():
    row = pd.Series({"building": "stadium"})
    h, src = estimate_height_from_attributes(row)
    assert h == 25.0
    assert src == "estimated"


def test_utm_oklahoma_city():
    epsg = utm_epsg_from_wgs84_bounds(-97.7, 35.3, -97.4, 35.6)
    assert epsg == 32614
