"""Clip GeoTIFF rasters to a WGS84 bbox or to match a reference DEM."""

from __future__ import annotations

from pathlib import Path

from cfd_geometry.download.bbox import Bbox


def clip_geotiff_to_bbox(
    input_path: str | Path,
    bbox: Bbox,
    output_path: str | Path | None = None,
    *,
    inplace: bool = False,
) -> Path:
    """
    Crop a raster to a WGS84 bounding box and write a new GeoTIFF.

    Reprojects the bbox into the source CRS before masking.
    """
    import rasterio
    from rasterio.mask import mask
    from rasterio.warp import transform_bounds
    from shapely.geometry import box, mapping

    input_path = Path(input_path)
    if output_path is None:
        output_path = input_path if inplace else input_path.with_name(
            f"{input_path.stem}_clipped{input_path.suffix}"
        )
    else:
        output_path = Path(output_path)

    bbox.validate()
    with rasterio.open(input_path) as src:
        if src.crs is None:
            raise ValueError(f"Raster has no CRS: {input_path}")
        w, s, e, n = transform_bounds("EPSG:4326", src.crs, bbox.west, bbox.south, bbox.east, bbox.north)
        geom = mapping(box(w, s, e, n))
        out_image, out_transform = mask(src, [geom], crop=True)
        out_meta = src.meta.copy()
        out_meta.update(
            {
                "height": out_image.shape[1],
                "width": out_image.shape[2],
                "transform": out_transform,
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(output_path, "w", **out_meta) as dst:
        dst.write(out_image)

    with rasterio.open(output_path) as clipped:
        print(
            f"  Clipped {input_path.name} -> {output_path.name} "
            f"({clipped.width} x {clipped.height} px)"
        )
    return output_path


def clip_geotiff_to_reference(
    source_path: str | Path,
    reference_path: str | Path,
    output_path: str | Path | None = None,
    *,
    inplace: bool = True,
) -> Path:
    """
    Crop ``source_path`` to the geographic extent of ``reference_path`` (e.g. dem.tif).

    Uses the reference raster bounds in its native CRS.
    """
    import rasterio
    from rasterio.mask import mask
    from rasterio.warp import transform_bounds
    from shapely.geometry import box, mapping

    source_path = Path(source_path)
    reference_path = Path(reference_path)
    if output_path is None:
        output_path = source_path if inplace else source_path.with_name(
            f"{source_path.stem}_clipped{source_path.suffix}"
        )
    else:
        output_path = Path(output_path)

    with rasterio.open(reference_path) as ref:
        ref_bounds = ref.bounds
        ref_crs = ref.crs

    with rasterio.open(source_path) as src:
        if src.crs is None:
            raise ValueError(f"Raster has no CRS: {source_path}")
        w, s, e, n = ref_bounds
        if ref_crs and src.crs != ref_crs:
            w, s, e, n = transform_bounds(ref_crs, src.crs, w, s, e, n)
        geom = mapping(box(w, s, e, n))
        out_image, out_transform = mask(src, [geom], crop=True)
        out_meta = src.meta.copy()
        out_meta.update(
            {
                "height": out_image.shape[1],
                "width": out_image.shape[2],
                "transform": out_transform,
            }
        )

    tmp = output_path
    if inplace and output_path == source_path:
        tmp = source_path.with_suffix(".clip_tmp.tif")

    with rasterio.open(tmp, "w", **out_meta) as dst:
        dst.write(out_image)

    if inplace and tmp != output_path:
        tmp.replace(output_path)

    with rasterio.open(output_path) as clipped:
        print(
            f"  Clipped {source_path.name} to {reference_path.name} extent "
            f"({clipped.width} x {clipped.height} px)"
        )
    return output_path


def clip_rasters_to_dem(
    dem_path: str | Path,
    raster_paths: list[str | Path],
    *,
    bbox: Bbox | None = None,
) -> None:
    """Clip each raster to ``dem_path`` extent (or ``bbox`` if DEM missing)."""
    dem_path = Path(dem_path)
    for path in raster_paths:
        path = Path(path)
        if not path.exists():
            continue
        if dem_path.exists():
            clip_geotiff_to_reference(path, dem_path, inplace=True)
        elif bbox is not None:
            clip_geotiff_to_bbox(path, bbox, inplace=True)
