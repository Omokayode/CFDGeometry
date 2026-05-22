"""Tests for download bbox parsing (no network)."""

import pytest

from cfd_geometry.download.bbox import Bbox, bbox_from_sequence
from cfd_geometry.download.config import DownloadConfig


def test_bbox_from_sequence():
    box = bbox_from_sequence((-88.0, 43.0, -87.5, 43.5))
    assert box.west == -88.0
    assert box.north == 43.5


def test_bbox_invalid():
    with pytest.raises(ValueError):
        bbox_from_sequence((0.0, 1.0, -1.0, 2.0))


def test_download_config_requires_place_or_bbox(tmp_path):
    with pytest.raises(ValueError):
        DownloadConfig(output_dir=tmp_path)


def test_download_config_with_place(tmp_path):
    cfg = DownloadConfig(output_dir=tmp_path, place="Milwaukee, WI")
    assert cfg.place == "Milwaukee, WI"
