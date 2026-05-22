"""Orchestrate downloading all configured layers."""

from __future__ import annotations

from cfd_geometry.download.config import DownloadConfig, DownloadResult
from cfd_geometry.download.dem import download_dem_opentopography
from cfd_geometry.download.osm import (
    download_buildings,
    download_highways,
    download_trees,
    resolve_bbox,
)


def download_domain(config: DownloadConfig) -> DownloadResult:
    """
    Download OSM vector layers (and optional DEM) into ``config.output_dir``.

    Returns paths and feature counts for each layer written.
    """
    config.output_dir.mkdir(parents=True, exist_ok=True)

    bbox = resolve_bbox(
        place=config.place,
        bbox=config.bbox,
        timeout=config.network_timeout,
        place_buffer_m=config.place_buffer_m,
    )

    result = DownloadResult(output_dir=config.output_dir, bbox=bbox)

    if "buildings" in config.layers:
        path = config.output_dir / config.buildings_filename
        result.feature_counts["buildings"] = download_buildings(
            bbox, path, timeout=config.network_timeout
        )
        if result.feature_counts["buildings"] > 0:
            result.files["buildings"] = path

    if "trees" in config.layers:
        path = config.output_dir / config.trees_filename
        result.feature_counts["trees"] = download_trees(
            bbox, path, timeout=config.network_timeout
        )
        if result.feature_counts["trees"] > 0:
            result.files["trees"] = path

    if "highways" in config.layers:
        path = config.output_dir / config.highways_filename
        result.feature_counts["highways"] = download_highways(
            bbox, path, timeout=config.network_timeout
        )
        if result.feature_counts["highways"] > 0:
            result.files["highways"] = path

    if config.download_dem or "dem" in config.layers:
        from cfd_geometry.buildings.extents import dem_download_bbox_around_buildings

        if config.dem_bbox is not None:
            dem_bbox = config.dem_bbox
            print("DEM extent: user-specified bbox")
        elif "buildings" in result.files:
            dem_bbox = dem_download_bbox_around_buildings(
                result.files["buildings"],
                buffer_m=config.dem_buffer_m,
                fallback_bbox=bbox,
            )
        else:
            dem_bbox = resolve_bbox(
                place=config.place,
                bbox=config.bbox,
                timeout=config.network_timeout,
                place_buffer_m=config.dem_buffer_m,
            )
        dem_path = config.output_dir / config.dem_filename
        download_dem_opentopography(
            dem_bbox,
            dem_path,
            demtype=config.opentopography_demtype,
        )
        result.files["dem"] = dem_path
        result.feature_counts["dem"] = 1

    print("\nDownload summary:")
    for name, path in result.files.items():
        count = result.feature_counts.get(name, 0)
        print(f"  {name}: {path} ({count} features)" if name != "dem" else f"  dem: {path}")

    if "buildings" in result.files:
        align = [str(p) for k in ("buildings", "trees") if (p := result.files.get(k))]
        print("\nExample extrusion:")
        print(
            f"  cfd-geometry buildings {result.files['buildings']} "
            f"-o {config.output_dir / 'buildings.stl'} "
            f"--align-with {' '.join(align)}"
        )

    return result
