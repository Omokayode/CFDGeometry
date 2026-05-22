"""DEM raster loading and elevation sampling."""

from __future__ import annotations

import warnings

import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.warp import Resampling, reproject, transform_bounds
from scipy.interpolate import RegularGridInterpolator
from scipy.ndimage import gaussian_filter

from cfd_geometry.constants import DEFAULT_TARGET_CRS

warnings.filterwarnings("ignore")

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import tifffile

    TIFFFILE_AVAILABLE = True
except ImportError:
    TIFFFILE_AVAILABLE = False

try:
    from osgeo import gdal

    GDAL_AVAILABLE = True
except ImportError:
    GDAL_AVAILABLE = False


def load_elevation_raster(
    tif_path: str,
    target_crs: str = DEFAULT_TARGET_CRS,
    resample_factor: float = 1.0,
    *,
    build_interpolator: bool = True,
) -> dict:
    """Load a DEM GeoTIFF, reproject if needed, and optionally build an interpolator."""
    print(f"Loading elevation raster: {tif_path}")
    try:
        data = _load_with_rasterio(tif_path, target_crs, resample_factor)
    except Exception as e:
        print(f"Rasterio failed: {e}")
        data = _load_dem_alternative(tif_path, target_crs, resample_factor)

    if build_interpolator:
        _attach_interpolator(data)
    return data


def _load_with_rasterio(tif_path: str, target_crs: str, resample_factor: float) -> dict:
    with rasterio.open(tif_path) as src:
        elevation = src.read(1)
        original_transform = src.transform
        original_crs = src.crs

        if src.nodata is not None:
            elevation = np.where(elevation == src.nodata, np.nan, elevation)

        if str(original_crs) != target_crs:
            new_bounds = transform_bounds(original_crs, target_crs, *src.bounds)
            width_m = new_bounds[2] - new_bounds[0]
            height_m = new_bounds[3] - new_bounds[1]
            orig_res_x, orig_res_y = src.res
            new_width = int(width_m / (orig_res_x * resample_factor))
            new_height = int(height_m / (orig_res_y * resample_factor))
            new_transform = from_bounds(*new_bounds, new_width, new_height)
            elevation_reproj = np.empty((new_height, new_width), dtype=elevation.dtype)
            reproject(
                source=elevation,
                destination=elevation_reproj,
                src_transform=original_transform,
                src_crs=original_crs,
                dst_transform=new_transform,
                dst_crs=target_crs,
                resampling=Resampling.bilinear,
            )
            elevation = elevation_reproj
            transform = new_transform
            bounds = new_bounds
        elif resample_factor != 1.0:
            new_width = int(src.width * resample_factor)
            new_height = int(src.height * resample_factor)
            bounds = src.bounds
            transform = from_bounds(*bounds, new_width, new_height)
            elevation_resampled = np.empty((new_height, new_width), dtype=elevation.dtype)
            reproject(
                source=elevation,
                destination=elevation_resampled,
                src_transform=original_transform,
                src_crs=original_crs,
                dst_transform=transform,
                dst_crs=target_crs,
                resampling=Resampling.bilinear,
            )
            elevation = elevation_resampled
        else:
            transform = original_transform
            bounds = src.bounds

        pixel_width = abs(transform.a) if transform.a != 0 else 1.0
        pixel_height = abs(transform.e) if transform.e != 0 else 1.0

        return {
            "elevation": elevation,
            "bounds": bounds,
            "transform": transform,
            "pixel_width": pixel_width,
            "pixel_height": pixel_height,
            "width": elevation.shape[1],
            "height": elevation.shape[0],
            "crs": target_crs,
            "shape": elevation.shape,
        }


def _load_dem_alternative(tif_path: str, target_crs: str, resample_factor: float) -> dict:
    elevation = None
    if TIFFFILE_AVAILABLE:
        try:
            elevation = tifffile.imread(tif_path)
            if elevation.ndim == 3:
                elevation = elevation[0] if elevation.shape[0] == 1 else elevation[:, :, 0]
        except Exception:
            elevation = None

    if elevation is None and PIL_AVAILABLE:
        try:
            with Image.open(tif_path) as img:
                elevation = np.array(img)
                if elevation.ndim == 3:
                    elevation = elevation[:, :, 0]
        except Exception:
            elevation = None

    if elevation is None and GDAL_AVAILABLE:
        dataset = gdal.Open(tif_path)
        if dataset is not None:
            elevation = dataset.GetRasterBand(1).ReadAsArray()
            dataset = None

    if elevation is None:
        raise ValueError(f"Could not read DEM: {tif_path}")

    pixel_width = 1.0
    pixel_height = 1.0
    bounds = (0, 0, elevation.shape[1] * pixel_width, elevation.shape[0] * pixel_height)
    return {
        "elevation": elevation,
        "bounds": bounds,
        "transform": None,
        "pixel_width": pixel_width,
        "pixel_height": pixel_height,
        "width": elevation.shape[1],
        "height": elevation.shape[0],
        "crs": target_crs,
        "shape": elevation.shape,
    }


def _attach_interpolator(elevation_data: dict) -> None:
    bounds = elevation_data["bounds"]
    elevation = elevation_data["elevation"]
    rows, cols = elevation.shape
    x_coords = np.linspace(bounds[0], bounds[2], cols)
    y_coords = np.linspace(bounds[3], bounds[1], rows)
    elevation_data["x_coords"] = x_coords
    elevation_data["y_coords"] = y_coords
    elevation_data["interpolator"] = RegularGridInterpolator(
        (y_coords, x_coords),
        elevation,
        bounds_error=False,
        fill_value=np.nanmean(elevation),
    )


def preprocess_elevation(
    elevation_data: dict,
    smooth_sigma: float = 0,
    max_resolution: int | None = None,
    vertical_scale: float = 1.0,
) -> dict:
    """Smooth, downsample, and scale elevation values in place."""
    elevation = elevation_data["elevation"].copy()

    if np.any(np.isnan(elevation)):
        mean_elevation = np.nanmean(elevation)
        elevation = np.where(np.isnan(elevation), mean_elevation, elevation)

    if max_resolution and max(elevation.shape) > max_resolution:
        factor = max(elevation.shape) // max_resolution
        elevation = elevation[::factor, ::factor]
        elevation_data["elevation"] = elevation
        elevation_data["shape"] = elevation.shape
        elevation_data["height"] = elevation.shape[0]
        elevation_data["width"] = elevation.shape[1]
        elevation_data["pixel_width"] *= factor
        elevation_data["pixel_height"] *= factor

    if smooth_sigma > 0:
        elevation = gaussian_filter(elevation, sigma=smooth_sigma)

    if vertical_scale != 1.0:
        elevation = elevation * vertical_scale

    elevation_data["elevation"] = elevation
    if "interpolator" in elevation_data:
        _attach_interpolator(elevation_data)
    return elevation_data


def get_elevation_at_point(x: float, y: float, elevation_data: dict) -> float:
    """Sample ground elevation at (x, y) in the raster CRS."""
    if "interpolator" not in elevation_data:
        _attach_interpolator(elevation_data)
    try:
        value = elevation_data["interpolator"]((y, x))
        return float(value) if not np.isnan(value) else 0.0
    except Exception as e:
        print(f"Warning: elevation at ({x:.2f}, {y:.2f}): {e}")
        return 0.0
