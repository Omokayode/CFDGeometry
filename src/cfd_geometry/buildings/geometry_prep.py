"""Repair and validate building footprint geometries."""

from __future__ import annotations

import warnings

import geopandas as gpd


def warn_if_areas_look_like_degrees(gdf: gpd.GeoDataFrame) -> None:
    """
    Warn when footprint areas are tiny in a metric CRS (often WGS84 left unchanged).

    VoxCity-style pipelines expect meters; areas < 1 m² for most buildings suggest
    geographic coordinates or wrong meshsize units.
    """
    if gdf.crs is None:
        return
    try:
        if gdf.crs.is_geographic:
            warnings.warn(
                "Building CRS is geographic (degrees). Reproject to a metric CRS "
                "before extrusion for meaningful heights and mesh units.",
                stacklevel=2,
            )
            return
    except Exception:
        pass

    areas = gdf.geometry.area
    if len(areas) == 0:
        return
    median = float(areas.median())
    if median < 1.0:
        warnings.warn(
            f"Median footprint area is {median:.4f} m² — unusually small. "
            "Check CRS (should be UTM/metric) and meshsize/cell units.",
            stacklevel=2,
        )


def repair_building_geometries(
    gdf: gpd.GeoDataFrame,
    *,
    buffer_zero: bool = True,
    simplify_tolerance: float | None = None,
) -> tuple[gpd.GeoDataFrame, dict]:
    """
    Drop empty geometries, optionally buffer(0) invalid polygons, simplify.

    Returns (cleaned_gdf, stats).
    """
    out = gdf[gdf.geometry.notna()].copy()
    stats = {"input": len(gdf), "empty_dropped": len(gdf) - len(out), "invalid": 0, "repaired": 0}

    out["_valid"] = out.geometry.apply(
        lambda g: g.is_valid and not g.is_empty if g is not None else False
    )
    stats["invalid"] = int((~out["_valid"]).sum())

    if buffer_zero and stats["invalid"]:
        out.loc[~out["_valid"], "geometry"] = out.loc[~out["_valid"], "geometry"].buffer(0)
        out["_valid"] = out.geometry.apply(
            lambda g: g.is_valid and not g.is_empty if g is not None else False
        )
        stats["repaired"] = stats["invalid"] - int((~out["_valid"]).sum())

    out = out[out["_valid"]].drop(columns=["_valid"])

    if simplify_tolerance and simplify_tolerance > 0:
        out["geometry"] = out.geometry.simplify(simplify_tolerance, preserve_topology=True)

    stats["output"] = len(out)
    if stats["invalid"]:
        print(
            f"Geometry repair: {stats['invalid']} invalid, "
            f"{stats['repaired']} fixed with buffer(0), {stats['output']} kept"
        )
    return out, stats
