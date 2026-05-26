"""Tests for GeoTIFF clipping to DEM extent."""

import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import transform_bounds

from cfd_geometry.download.bbox import Bbox
from cfd_geometry.raster.clip import clip_geotiff_to_bbox, clip_geotiff_to_reference


def _write_tif(path, data, *, origin_x, origin_y, res, crs="EPSG:32616"):
    height, width = data.shape
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype="float32",
        crs=crs,
        transform=from_origin(origin_x, origin_y + height * res, res, res),
    ) as dst:
        dst.write(data.astype(np.float32), 1)


def test_clip_geotiff_to_reference(tmp_path):
    dem = tmp_path / "dem.tif"
    dsm = tmp_path / "dsm.tif"
    _write_tif(dem, np.ones((10, 10)), origin_x=100.0, origin_y=200.0, res=1.0)
    _write_tif(dsm, np.ones((30, 30)), origin_x=90.0, origin_y=190.0, res=1.0)

    clip_geotiff_to_reference(dsm, dem, inplace=True)

    with rasterio.open(dsm) as src, rasterio.open(dem) as ref:
        assert src.width == ref.width
        assert src.height == ref.height


def test_clip_geotiff_to_bbox_wgs84(tmp_path):
    big = tmp_path / "big.tif"
    _write_tif(
        big,
        np.ones((20, 20)),
        origin_x=100.0,
        origin_y=200.0,
        res=1.0,
        crs="EPSG:32616",
    )
    with rasterio.open(big) as src:
        b = src.bounds
    w, s, e, n = transform_bounds("EPSG:32616", "EPSG:4326", b.left, b.bottom, b.right, b.top)
    bbox = Bbox(
        west=float(w + (e - w) * 0.25),
        south=float(s + (n - s) * 0.25),
        east=float(w + (e - w) * 0.75),
        north=float(s + (n - s) * 0.75),
    )
    out = clip_geotiff_to_bbox(big, bbox, inplace=True)
    with rasterio.open(out) as src:
        assert src.width < 20
        assert src.height < 20
