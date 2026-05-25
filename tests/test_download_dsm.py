"""Tests for OpenTopography DSM/DTM download helpers."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cfd_geometry.download.bbox import Bbox
from cfd_geometry.download.dsm import (
    download_dsm_opentopography,
    normalize_product,
    validate_dsm_product,
)
from cfd_geometry.download.opentopography import build_opentopography_url
from cfd_geometry.download.opentopography import bbox_area_km2, resolve_opentopography_server


def test_normalize_usgs_product():
    assert normalize_product("usgs10m") == "USGS10m"
    assert normalize_product("USGS10") == "USGS10m"


def test_validate_cop30_dsm():
    assert validate_dsm_product("cop30") == "COP30"


def test_usgs_uses_usgsdem_server():
    assert resolve_opentopography_server("USGS10m") == "usgsdem"
    assert resolve_opentopography_server("COP30") == "globaldem"


def test_build_dsm_url_contains_bbox():
    bbox = Bbox(west=-88.0, south=43.0, east=-87.5, north=43.5)
    url = build_opentopography_url(
        "globaldem", bbox, product="COP30", api_key="test-key"
    )
    assert "globaldem" in url
    assert "COP30" in url
    assert "west=-88.0" in url
    assert "API_Key=test-key" in url


def test_bbox_area_limit_raises():
    from cfd_geometry.download.opentopography import check_bbox_area_limit

    huge = Bbox(west=-90.0, south=25.0, east=-80.0, north=35.0)
    with pytest.raises(RuntimeError, match="exceeds"):
        check_bbox_area_limit(huge, "USGS1m", server="usgsdem")


@patch("requests.get")
def test_download_dsm_writes_geotiff(mock_get, tmp_path):
    try:
        import rasterio
        from rasterio.transform import from_origin
    except ImportError:
        pytest.skip("rasterio required")

    bbox = Bbox(west=-88.0, south=43.0, east=-87.9, north=43.1)
    out = tmp_path / "dsm.tif"

    import numpy as np

    tif_path = tmp_path / "src.tif"
    data = np.array([[10.0, 12.0], [11.0, 13.0]], dtype=np.float32)
    with rasterio.open(
        tif_path,
        "w",
        driver="GTiff",
        height=2,
        width=2,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=from_origin(-88.0, 43.1, 0.05, 0.05),
    ) as dst:
        dst.write(data, 1)

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.headers = {"Content-Type": "image/tiff"}
    mock_resp.content = tif_path.read_bytes()
    mock_get.return_value = mock_resp

    with patch.dict("os.environ", {"OPENTOPOGRAPHY_API_KEY": "test"}):
        path = download_dsm_opentopography(bbox, out, product="COP30")

    assert path == out
    assert out.exists()
    assert bbox_area_km2(bbox) < 450_000
