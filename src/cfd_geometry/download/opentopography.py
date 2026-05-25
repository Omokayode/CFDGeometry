"""Shared OpenTopography API helpers (DEM, DSM, DTM rasters)."""

from __future__ import annotations

import math
import os
import zipfile
from pathlib import Path
from urllib.parse import urlencode

from cfd_geometry.download.bbox import Bbox

OPENTOPOGRAPHY_BASE = "https://portal.opentopography.org/API"
REGISTER_URL = "https://portal.opentopography.org/requestService?service=api"

# Area limits (km²) from OpenTopography API docs (approximate enforcement).
GLOBAL_PRODUCT_MAX_KM2: dict[str, float] = {
    "COP30": 450_000,
    "COP90": 450_000,
    "CA_MRDEM_DSM": 450_000,
    "CA_MRDEM_DTM": 450_000,
    "AW3D30": 450_000,
    "SRTMGL1": 450_000,
    "SRTMGL3": 4_050_000,
}
USGS_PRODUCT_MAX_KM2: dict[str, float] = {
    "USGS30M": 225_000,
    "USGS10M": 25_000,
    "USGS1M": 250,
}


def get_opentopography_api_key(api_key: str | None = None) -> str:
    """Return API key from argument or ``OPENTOPOGRAPHY_API_KEY``."""
    key = api_key or os.environ.get("OPENTOPOGRAPHY_API_KEY")
    if not key:
        raise RuntimeError(
            "OpenTopography download needs an API key.\n"
            f"  1. Register: {REGISTER_URL}\n"
            "  2. export OPENTOPOGRAPHY_API_KEY='your-key'\n"
            "  3. Re-run with --dem or --dsm\n"
            "Or place your own GeoTIFF in the output folder."
        )
    return key


def bbox_area_km2(bbox: Bbox) -> float:
    """Approximate WGS84 bbox area in km²."""
    lat_mid = (bbox.south + bbox.north) / 2.0
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * math.cos(math.radians(lat_mid))
    width_m = (bbox.east - bbox.west) * m_per_deg_lon
    height_m = (bbox.north - bbox.south) * m_per_deg_lat
    return max(0.0, width_m * height_m) / 1e6


def check_bbox_area_limit(bbox: Bbox, product: str, *, server: str) -> None:
    """Raise if bbox exceeds OpenTopography area limits for the product."""
    area = bbox_area_km2(bbox)
    key = product.upper()
    if server == "usgsdem":
        limit = USGS_PRODUCT_MAX_KM2.get(key)
    else:
        limit = GLOBAL_PRODUCT_MAX_KM2.get(key)
    if limit is None:
        return
    if area > limit:
        raise RuntimeError(
            f"Requested area {area:,.0f} km² exceeds OpenTopography limit "
            f"({limit:,.0f} km²) for {product}. "
            "Use a smaller --bbox/--dem-buffer-m or --dsm-bbox."
        )


def build_opentopography_url(
    server: str,
    bbox: Bbox,
    *,
    product: str,
    api_key: str,
    output_format: str = "GTiff",
) -> str:
    """Build a globaldem or usgsdem request URL."""
    product = product.strip()
    if server == "globaldem":
        params = {
            "demtype": product,
            "south": bbox.south,
            "north": bbox.north,
            "west": bbox.west,
            "east": bbox.east,
            "outputFormat": output_format,
            "API_Key": api_key,
        }
    elif server == "usgsdem":
        params = {
            "datasetName": product,
            "south": bbox.south,
            "north": bbox.north,
            "west": bbox.west,
            "east": bbox.east,
            "outputFormat": output_format,
            "API_Key": api_key,
        }
    else:
        raise ValueError(f"Unknown OpenTopography server: {server!r}")

    return f"{OPENTOPOGRAPHY_BASE}/{server}?" + urlencode(params)


def resolve_opentopography_server(product: str) -> str:
    """Return ``globaldem`` or ``usgsdem`` for a product name."""
    if product.upper().startswith("USGS"):
        return "usgsdem"
    return "globaldem"


def fetch_opentopography_geotiff(
    url: str,
    output_path: Path,
    *,
    label: str,
    timeout: int = 600,
) -> Path:
    """GET an OpenTopography raster URL and write a GeoTIFF."""
    try:
        import requests
    except ImportError as e:
        raise ImportError(
            "OpenTopography download requires the 'requests' package. "
            "Install with: pip install -e '.[download]'"
        ) from e

    print(f"Requesting {label} from OpenTopography...")
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    content_type = response.headers.get("Content-Type", "")
    if "zip" in content_type or response.content[:2] == b"PK":
        zip_path = output_path.with_suffix(".zip")
        zip_path.write_bytes(response.content)
        with zipfile.ZipFile(zip_path) as zf:
            tif_names = [n for n in zf.namelist() if n.lower().endswith((".tif", ".tiff"))]
            if not tif_names:
                raise RuntimeError("OpenTopography ZIP contained no GeoTIFF")
            with zf.open(tif_names[0]) as src, open(output_path, "wb") as dst:
                dst.write(src.read())
        zip_path.unlink(missing_ok=True)
    else:
        output_path.write_bytes(response.content)

    validate_geotiff(output_path)
    print(f"Wrote {label} -> {output_path}")
    return output_path


def validate_geotiff(path: Path, *, max_pixels: int = 100_000_000) -> None:
    """Ensure downloaded raster is readable and not unreasonably large."""
    try:
        import rasterio
    except ImportError:
        return

    with rasterio.open(path) as src:
        pixels = src.width * src.height
        print(
            f"  Raster: {src.width} x {src.height} ({pixels:,} pixels), CRS={src.crs}"
        )
        if pixels > max_pixels:
            raise RuntimeError(
                f"Raster is too large ({src.width}x{src.height}). "
                "Use a smaller study bbox or clip the GeoTIFF."
            )
        if src.width < 2 or src.height < 2:
            raise RuntimeError(
                f"Raster appears invalid or empty ({src.width}x{src.height})"
            )
