"""Resolve overlapping building footprints."""

from __future__ import annotations

import geopandas as gpd
from shapely.ops import unary_union


def _overlap_ratio(geom_a, geom_b) -> float:
    inter = geom_a.intersection(geom_b)
    if inter.is_empty:
        return 0.0
    a_area = geom_a.area
    b_area = geom_b.area
    if a_area <= 0 or b_area <= 0:
        return 0.0
    return float(inter.area) / min(a_area, b_area)


def resolve_overlapping_footprints(
    gdf: gpd.GeoDataFrame,
    *,
    method: str = "fast",
    overlap_ratio_threshold: float = 0.5,
    keep: str = "larger",
) -> tuple[gpd.GeoDataFrame, dict]:
    """
    Reduce duplicate/overlapping footprints.

    - ``fast``: spatial index; drop smaller polygon when overlap ratio exceeds threshold
    - ``precise``: sort by area; subtract union of larger polygons from smaller ones

    ``keep``: ``larger`` (fast only) retains the bigger footprint.
    """
    if gdf.empty:
        return gdf, {"removed": 0, "clipped": 0}

    method = method.lower().strip()
    out = gdf.copy().reset_index(drop=True)
    out["_area"] = out.geometry.area
    stats = {"removed": 0, "clipped": 0, "method": method}

    if method == "fast":
        sindex = out.sindex
        drop: set[int] = set()
        for i, row in out.iterrows():
            if i in drop:
                continue
            geom = row.geometry
            if geom is None or geom.is_empty:
                drop.add(i)
                continue
            for j in sindex.intersection(geom.bounds):
                if j <= i or j in drop:
                    continue
                other = out.geometry.iloc[j]
                if not geom.intersects(other):
                    continue
                ratio = _overlap_ratio(geom, other)
                if ratio < overlap_ratio_threshold:
                    continue
                area_i = out["_area"].iloc[i]
                area_j = out["_area"].iloc[j]
                if keep == "larger":
                    drop.add(i if area_i < area_j else j)
                else:
                    drop.add(j if area_i >= area_j else i)

        stats["removed"] = len(drop)
        if drop:
            print(f"Overlap filter ({method}): removed {len(drop)} duplicate footprints")
        out = out.drop(index=list(drop)).reset_index(drop=True)

    elif method == "precise":
        order = out.sort_values("_area", ascending=False).index.tolist()
        accumulated = None
        new_geoms = {}
        for i in order:
            geom = out.geometry.loc[i]
            if geom is None or geom.is_empty:
                continue
            if accumulated is None:
                new_geoms[i] = geom
                accumulated = geom
                continue
            diff = geom.difference(accumulated)
            if diff.is_empty or diff.area < 0.5:
                stats["removed"] += 1
                continue
            if diff.geom_type == "MultiPolygon":
                diff = max(diff.geoms, key=lambda p: p.area)
            if diff.area < geom.area * 0.95:
                stats["clipped"] += 1
            new_geoms[i] = diff
            accumulated = unary_union([accumulated, diff])

        if stats["removed"] or stats["clipped"]:
            print(
                f"Overlap resolve (precise): {stats['removed']} removed, "
                f"{stats['clipped']} clipped"
            )
        keep_idx = list(new_geoms.keys())
        out = out.loc[keep_idx].copy()
        out["geometry"] = [new_geoms[i] for i in keep_idx]
        out = out.reset_index(drop=True)
    else:
        raise ValueError(f"Unknown overlap method: {method!r}")

    out = out.drop(columns=["_area"], errors="ignore")
    return out, stats
