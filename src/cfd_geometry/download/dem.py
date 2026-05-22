"""Optional DEM download (OpenTopography API key)."""

from __future__ import annotations

import os
import zipfile
from pathlib import Path
from urllib.parse import urlencode

import requests

from cfd_geometry.download.bbox import Bbox


def download_dem_opentopography(
    bbox: Bbox,
    output_path: Path,
    *,
    demtype: str = "SRTMGL1",
    api_key: str | None = None,
) -> Path:
    """
    Download a GeoTIFF DEM from OpenTopography (requires free API key).

    Set environment variable ``OPENTOPOGRAPHY_API_KEY`` or pass ``api_key``.
    Register at https://portal.opentopography.org/requestService?service=api
    """
    key = api_key or os.environ.get("OPENTOPOGRAPHY_API_KEY")
    if not key:
        raise RuntimeError(
            "DEM download needs an OpenTopography API key.\n"
            "  1. Register: https://portal.opentopography.org/requestService?service=api\n"
            "  2. export OPENTOPOGRAPHY_API_KEY='your-key'\n"
            "  3. Re-run with --dem\n"
            "Or place your own dem.tif in the output folder and skip --dem."
        )

    params = {
        "demtype": demtype,
        "south": bbox.south,
        "north": bbox.north,
        "west": bbox.west,
        "east": bbox.east,
        "outputFormat": "GTiff",
        "API_Key": key,
    }
    url = "https://portal.opentopography.org/API/globaldem?" + urlencode(params)
    print(f"Requesting DEM ({demtype}) from OpenTopography...")
    response = requests.get(url, timeout=600)
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

    print(f"Wrote DEM -> {output_path}")
    return output_path
