"""Tests for domain configuration (no network)."""

import pytest

from cfd_geometry.domain.config import DomainConfig


def test_domain_paths(tmp_path):
    cfg = DomainConfig(output_dir=tmp_path, place="Milwaukee, WI")
    assert cfg.input_dir == tmp_path / "input"
    assert cfg.stl_dir == tmp_path / "output"
    assert cfg.buildings_shp == tmp_path / "input" / "buildings.shp"


def test_domain_requires_extent(tmp_path):
    with pytest.raises(ValueError):
        DomainConfig(output_dir=tmp_path)


def test_study_buffer_syncs_osm_and_dem(tmp_path):
    cfg = DomainConfig(output_dir=tmp_path, place="Test", study_buffer_m=400.0)
    assert cfg.place_buffer_m == 400.0
    assert cfg.dem_buffer_m == 400.0
