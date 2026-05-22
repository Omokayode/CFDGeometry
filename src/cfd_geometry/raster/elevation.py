"""DEM raster loading and elevation sampling."""

from __future__ import annotations

import math
import warnings

import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.warp import Resampling, calculate_default_transform, reproject

from cfd_geometry.constants import DEFAULT_DEM_MAX_RESOLUTION, DEFAULT_TARGET_CRS, MAX_DEM_PIXELS
from scipy.interpolate import RegularGridInterpolator
from scipy.ndimage import gaussian_filter

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


def _cap_raster_dimensions(
    width: int,
    height: int,
    *,
    max_resolution: int | None,
    max_pixels: int = MAX_DEM_PIXELS,
) -> tuple[int, int]:
    """Reduce width/height so raster fits in memory."""
    width = max(1, int(width))
    height = max(1, int(height))

    if max_resolution:
        scale = min(1.0, max_resolution / max(width, height))
        if scale < 1.0:
            width = max(1, int(width * scale))
            height = max(1, int(height * scale))

    pixels = width * height
    if pixels > max_pixels:
        scale = math.sqrt(max_pixels / pixels)
        width = max(1, int(width * scale))
        height = max(1, int(height * scale))

    return width, height


def load_elevation_raster(
    tif_path: str,
    target_crs: str = DEFAULT_TARGET_CRS,
    resample_factor: float = 1.0,
    *,
    build_interpolator: bool = True,
    max_resolution: int | None = DEFAULT_DEM_MAX_RESOLUTION,
    target_resolution_m: float | None = 5.0,
) -> dict:
    """Load a DEM GeoTIFF, reproject if needed, and optionally build an interpolator."""
    print(f"Loading elevation raster: {tif_path}")
    try:
        data = _load_with_rasterio(
            tif_path,
            target_crs,
            resample_factor,
            max_resolution=max_resolution,
            target_resolution_m=target_resolution_m,
        )
    except Exception as e:
        print(f"Rasterio failed: {e}")
        data = _load_dem_alternative(tif_path, target_crs, resample_factor)
        if max_resolution:
            data = preprocess_elevation(data, max_resolution=max_resolution)

    if build_interpolator:
        _attach_interpolator(data)
    return data


def _load_with_rasterio(
    tif_path: str,
    target_crs: str,
    resample_factor: float,
    *,
    max_resolution: int | None,
    target_resolution_m: float | None,
) -> dict:
    with rasterio.open(tif_path) as src:
        src_crs = src.crs
        if src_crs is None:
            print("Warning: DEM has no CRS metadata; assuming EPSG:4326")
            src_crs = "EPSG:4326"

        print(
            f"  Source DEM: {src.width} x {src.height} px, CRS={src_crs}, "
            f"res=({src.res[0]:.6g}, {src.res[1]:.6g})"
        )

        if src.width * src.height > MAX_DEM_PIXELS * 4:
            print(
                f"  Source is very large; downsampling during read "
                f"(max dim {max_resolution or DEFAULT_DEM_MAX_RESOLUTION})"
            )

        dst_crs = target_crs
        need_reproject = str(src_crs) != str(dst_crs)

        if need_reproject:
            res_m = None
            if target_resolution_m and resample_factor == 1.0:
                res_m = target_resolution_m
            dst_transform, dst_width, dst_height = calculate_default_transform(
                src_crs,
                dst_crs,
                src.width,
                src.height,
                *src.bounds,
                resolution=res_m,
            )
            dst_width, dst_height = _cap_raster_dimensions(
                dst_width, dst_height, max_resolution=max_resolution
            )
            dst_transform, dst_width, dst_height = calculate_default_transform(
                src_crs,
                dst_crs,
                src.width,
                src.height,
                *src.bounds,
                dst_width=dst_width,
                dst_height=dst_height,
            )
            print(f"  Reprojecting to {dst_crs} at {dst_width} x {dst_height} px")
            elevation = np.empty((dst_height, dst_width), dtype=np.float32)
            reproject(
                source=rasterio.band(src, 1),
                destination=elevation,
                src_transform=src.transform,
                src_crs=src_crs,
                dst_transform=dst_transform,
                dst_crs=dst_crs,
                resampling=Resampling.bilinear,
            )
            transform = dst_transform
            bounds = rasterio.transform.array_bounds(
                dst_height, dst_width, dst_transform
            )
        else:
            out_h, out_w = _cap_raster_dimensions(
                src.width, src.height, max_resolution=max_resolution
            )
            if (out_w, out_h) != (src.width, src.height):
                print(f"  Reading decimated {out_w} x {out_h} px")
                elevation = src.read(
                    1,
                    out_shape=(out_h, out_w),
                    resampling=Resampling.bilinear,
                )
                bounds = src.bounds
                transform = from_bounds(
                    bounds.left,
                    bounds.bottom,
                    bounds.right,
                    bounds.top,
                    out_w,
                    out_h,
                )
            else:
                elevation = src.read(1)
                transform = src.transform
            bounds = rasterio.transform.array_bounds(
                elevation.shape[0], elevation.shape[1], transform
            )

        if src.nodata is not None:
            elevation = np.where(elevation == src.nodata, np.nan, elevation)

        pixel_width = abs(transform.a) if transform.a else 1.0
        pixel_height = abs(transform.e) if transform.e else 1.0

        print(
            f"  Loaded DEM grid: {elevation.shape[1]} x {elevation.shape[0]} px, "
            f"cell ~{pixel_width:.2f} x {pixel_height:.2f} m"
        )

        return {
            "elevation": elevation,
            "bounds": bounds,
            "transform": transform,
            "pixel_width": pixel_width,
            "pixel_height": pixel_height,
            "width": elevation.shape[1],
            "height": elevation.shape[0],
            "crs": dst_crs,
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

    if elevation.shape[0] * elevation.shape[1] > MAX_DEM_PIXELS:
        raise ValueError(
            f"DEM array too large ({elevation.shape}); use a clipped GeoTIFF or "
            "re-download with a smaller bbox."
        )

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


def get_elevation_at_points(
    points: list[tuple[float, float]],
    elevation_data: dict,
) -> list[float]:
    """Sample elevation at multiple (x, y) points in raster CRS."""
    if not points:
        return []
    if "interpolator" not in elevation_data:
        _attach_interpolator(elevation_data)
    arr = np.array(points)
    values = elevation_data["interpolator"]((arr[:, 1], arr[:, 0]))
    return [float(v) if not np.isnan(v) else 0.0 for v in values]


def ground_elevation_for_polygon(
    polygon,
    elevation_data: dict,
    *,
    sample_points: int = 5,
) -> float:
    """Average ground elevation under a polygon footprint."""
    from shapely.geometry import Point

    minx, miny, maxx, maxy = polygon.bounds
    sample_x = np.linspace(minx, maxx, sample_points)
    sample_y = np.linspace(miny, maxy, sample_points)

    points_to_sample = []
    for x in sample_x:
        for y in sample_y:
            pt = Point(x, y)
            if polygon.contains(pt) or polygon.touches(pt):
                points_to_sample.append((x, y))

    if not points_to_sample:
        boundary = list(polygon.exterior.coords)
        points_to_sample = [(x, y) for x, y in boundary[:sample_points]]

    elevations = get_elevation_at_points(points_to_sample, elevation_data)
    valid = [e for e in elevations if not np.isnan(e) and e != 0]
    return float(np.mean(valid)) if valid else 0.0


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
