"""Download DSM / DTM rasters from OpenTopography for LiDAR-style building heights."""

from __future__ import annotations

from pathlib import Path

from cfd_geometry.download.bbox import Bbox
from cfd_geometry.download.opentopography import (
    build_opentopography_url,
    check_bbox_area_limit,
    fetch_opentopography_geotiff,
    get_opentopography_api_key,
    resolve_opentopography_server,
)

# Surface models (include buildings / vegetation) via globaldem.
GLOBAL_DSM_PRODUCTS = frozenset(
    {
        "COP30",  # Copernicus Global DSM 30 m (default, worldwide)
        "COP90",
        "CA_MRDEM_DSM",
        "AW3D30",
    }
)

# Bare-earth / terrain models for CHM = DSM - DTM.
GLOBAL_DTM_PRODUCTS = frozenset(
    {
        "SRTMGL1",
        "SRTMGL3",
        "EU_DTM",
        "CA_MRDEM_DTM",
        "NASADEM",
    }
)

# USGS 3DEP (primarily bare-earth DEM; finer in CONUS).
USGS_DTM_PRODUCTS = frozenset({"USGS30M", "USGS10M", "USGS1M"})

DEFAULT_DSM_PRODUCT = "COP30"
DEFAULT_DTM_PRODUCT = "SRTMGL1"
USGS10M_PRODUCT = "USGS10m"

# Rough CONUS bounds for auto USGS 3DEP selection (WGS84).
CONUS_BBOX = Bbox(west=-125.0, south=24.0, east=-66.0, north=50.0)


def normalize_product(name: str) -> str:
    """Normalize CLI product names (e.g. usgs10m -> USGS10m)."""
    aliases = {"USGS30": "USGS30m", "USGS10": "USGS10m", "USGS1": "USGS1m"}
    key = name.strip().upper()
    if key in aliases:
        return aliases[key]
    if key.startswith("USGS"):
        rest = key[4:]
        if rest.endswith("M"):
            rest = rest[:-1] + "m"
        return "USGS" + rest
    return key


def validate_dsm_product(product: str) -> str:
    product = normalize_product(product)
    if product in GLOBAL_DSM_PRODUCTS or product in USGS_DTM_PRODUCTS:
        return product
    raise ValueError(
        f"Unknown DSM product {product!r}. "
        f"Global DSM: {', '.join(sorted(GLOBAL_DSM_PRODUCTS))}. "
        f"US (3DEP, coarser surface): {', '.join(sorted(USGS_DTM_PRODUCTS))}."
    )


def is_conus_bbox(bbox: Bbox) -> bool:
    """True if the bbox lies mostly inside the contiguous U.S."""
    return (
        bbox.west >= CONUS_BBOX.west
        and bbox.east <= CONUS_BBOX.east
        and bbox.south >= CONUS_BBOX.south
        and bbox.north <= CONUS_BBOX.north
    )


def resolve_raster_products(
    bbox: Bbox | None,
    *,
    dsm_product: str = DEFAULT_DSM_PRODUCT,
    dtm_product: str = DEFAULT_DTM_PRODUCT,
    dem_product: str = "SRTMGL1",
    use_usgs10m: bool = False,
    auto_usgs10m: bool = False,
) -> tuple[str, str, str]:
    """
    Pick OpenTopography products for DSM, DTM, and terrain DEM.

    ``use_usgs10m`` forces USGS 3DEP 10 m (CONUS, ≤ ~25 km² per request).
    ``auto_usgs10m`` uses USGS10m when ``bbox`` is inside CONUS, else global defaults.
    """
    if use_usgs10m or (auto_usgs10m and bbox is not None and is_conus_bbox(bbox)):
        print("Raster products: USGS 3DEP 10 m (CONUS)")
        return USGS10M_PRODUCT, USGS10M_PRODUCT, USGS10M_PRODUCT
    return (
        normalize_product(dsm_product),
        normalize_product(dtm_product),
        normalize_product(dem_product),
    )


def validate_dtm_product(product: str) -> str:
    product = normalize_product(product)
    if (
        product in GLOBAL_DTM_PRODUCTS
        or product in USGS_DTM_PRODUCTS
        or product in GLOBAL_DSM_PRODUCTS
    ):
        return product
    raise ValueError(
        f"Unknown DTM product {product!r}. "
        f"Examples: {DEFAULT_DTM_PRODUCT}, EU_DTM, CA_MRDEM_DTM, USGS10m."
    )


def download_dsm_opentopography(
    bbox: Bbox,
    output_path: Path,
    *,
    product: str = DEFAULT_DSM_PRODUCT,
    api_key: str | None = None,
    timeout: int = 600,
) -> Path:
    """
    Download a Digital Surface Model GeoTIFF from OpenTopography.

    Default ``COP30`` (Copernicus Global DSM, 30 m, worldwide). For U.S. studies
    you may use ``USGS10m`` (3DEP, 10 m) — primarily bare earth but finer than SRTM.

    Requires ``OPENTOPOGRAPHY_API_KEY`` (same key as ``--dem``).
    """
    product = validate_dsm_product(product)
    key = get_opentopography_api_key(api_key)
    server = resolve_opentopography_server(product)
    check_bbox_area_limit(bbox, product, server=server)
    url = build_opentopography_url(server, bbox, product=product, api_key=key)
    return fetch_opentopography_geotiff(
        url,
        Path(output_path),
        label=f"DSM ({product})",
        timeout=timeout,
    )


def download_dtm_opentopography(
    bbox: Bbox,
    output_path: Path,
    *,
    product: str = DEFAULT_DTM_PRODUCT,
    api_key: str | None = None,
    timeout: int = 600,
) -> Path:
    """
    Download a ground / DTM GeoTIFF for CHM height = DSM - DTM.

    Default ``SRTMGL1`` (30 m). Use ``USGS10m`` in CONUS for higher-quality ground.
    """
    product = validate_dtm_product(product)
    key = get_opentopography_api_key(api_key)
    server = resolve_opentopography_server(product)
    check_bbox_area_limit(bbox, product, server=server)
    url = build_opentopography_url(server, bbox, product=product, api_key=key)
    return fetch_opentopography_geotiff(
        url,
        Path(output_path),
        label=f"DTM ({product})",
        timeout=timeout,
    )


def download_lidar_rasters_opentopography(
    bbox: Bbox,
    output_dir: Path,
    *,
    dsm_filename: str = "dsm.tif",
    dtm_filename: str = "dtm.tif",
    dsm_product: str = DEFAULT_DSM_PRODUCT,
    dtm_product: str | None = DEFAULT_DTM_PRODUCT,
    api_key: str | None = None,
    timeout: int = 600,
) -> dict[str, Path]:
    """
    Download DSM and optional DTM into ``output_dir`` for LiDAR building workflows.

    Returns paths keyed ``dsm`` and optionally ``dtm``.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    files: dict[str, Path] = {}
    files["dsm"] = download_dsm_opentopography(
        bbox,
        output_dir / dsm_filename,
        product=dsm_product,
        api_key=api_key,
        timeout=timeout,
    )
    if dtm_product:
        files["dtm"] = download_dtm_opentopography(
            bbox,
            output_dir / dtm_filename,
            product=dtm_product,
            api_key=api_key,
            timeout=timeout,
        )
    return files
