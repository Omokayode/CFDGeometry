"""Optional DEM download (OpenTopography API key)."""

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


def download_dem_opentopography(
    bbox: Bbox,
    output_path: Path,
    *,
    demtype: str = "SRTMGL1",
    api_key: str | None = None,
    timeout: int = 600,
) -> Path:
    """
    Download a GeoTIFF DEM from OpenTopography (requires free API key).

    Set environment variable ``OPENTOPOGRAPHY_API_KEY`` or pass ``api_key``.
    Register at https://portal.opentopography.org/requestService?service=api
    """
    key = get_opentopography_api_key(api_key)
    demtype = demtype.strip()
    server = resolve_opentopography_server(demtype)
    check_bbox_area_limit(bbox, demtype, server=server)
    url = build_opentopography_url(server, bbox, product=demtype, api_key=key)
    return fetch_opentopography_geotiff(
        url,
        Path(output_path),
        label=f"DEM ({demtype})",
        timeout=timeout,
    )
