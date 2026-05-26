"""Orchestrate downloading all configured layers."""

from __future__ import annotations

from cfd_geometry.download.config import DownloadConfig, DownloadResult
from cfd_geometry.download.dem import download_dem_opentopography
from cfd_geometry.download.dsm import (
    download_dsm_opentopography,
    download_dtm_opentopography,
)
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
    # Bind at entry so a later local import cannot shadow the module-level name.
    _resolve_bbox = resolve_bbox

    config.output_dir.mkdir(parents=True, exist_ok=True)

    bbox = _resolve_bbox(
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

    need_raster_bbox = (
        config.download_dem
        or config.download_dsm
        or config.download_dtm
        or "dem" in config.layers
        or "dsm" in config.layers
        or "dtm" in config.layers
    )
    if need_raster_bbox:
        from cfd_geometry.buildings.extents import dem_download_bbox_around_buildings

        if config.dem_bbox is not None:
            raster_bbox = config.dem_bbox
            print("Raster extent: user-specified bbox")
        elif "buildings" in result.files:
            raster_bbox = dem_download_bbox_around_buildings(
                result.files["buildings"],
                buffer_m=config.dem_buffer_m,
                fallback_bbox=bbox,
            )
        else:
            raster_bbox = _resolve_bbox(
                place=config.place,
                bbox=config.bbox,
                timeout=config.network_timeout,
                place_buffer_m=config.dem_buffer_m,
            )

        from cfd_geometry.download.dsm import resolve_raster_products

        dsm_product, dtm_product, dem_product = resolve_raster_products(
            raster_bbox,
            dsm_product=config.opentopography_dsm_product,
            dtm_product=config.opentopography_dtm_product,
            dem_product=config.opentopography_demtype,
            use_usgs10m=config.use_usgs10m,
            auto_usgs10m=config.auto_usgs10m,
        )

        if config.download_dem or "dem" in config.layers:
            dem_path = config.output_dir / config.dem_filename
            if not dem_path.exists():
                download_dem_opentopography(
                    raster_bbox,
                    dem_path,
                    demtype=dem_product,
                )
            result.files["dem"] = dem_path
            result.feature_counts["dem"] = 1

        if config.download_dsm or "dsm" in config.layers:
            dsm_path = config.output_dir / config.dsm_filename
            if not dsm_path.exists():
                download_dsm_opentopography(
                    raster_bbox,
                    dsm_path,
                    product=dsm_product,
                )
            result.files["dsm"] = dsm_path
            result.feature_counts["dsm"] = 1

        if config.download_dtm or "dtm" in config.layers:
            dtm_path = config.output_dir / config.dtm_filename
            if not dtm_path.exists():
                download_dtm_opentopography(
                    raster_bbox,
                    dtm_path,
                    product=dtm_product,
                )
            result.files["dtm"] = dtm_path
            result.feature_counts["dtm"] = 1

        if config.clip_rasters_to_dem:
            from cfd_geometry.raster.clip import clip_rasters_to_dem

            dem_path = config.output_dir / config.dem_filename
            extras = [
                p
                for key in ("dsm", "dtm")
                if (p := result.files.get(key)) is not None
            ]
            if extras and (dem_path.exists() or raster_bbox is not None):
                print("Clipping DSM/DTM to DEM study extent:")
                clip_rasters_to_dem(dem_path, extras, bbox=raster_bbox)

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
