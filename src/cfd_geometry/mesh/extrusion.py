"""Extrude 2D polygons into watertight triangle meshes."""

from __future__ import annotations

from shapely.geometry import Polygon

from cfd_geometry.mesh.normals import calculate_normal  # noqa: F401 — re-export usage


def triangulate_2d(coords: list, z: float = 0.0, invert: bool = False) -> list:
    """Fan triangulation for a simple polygon ring."""
    triangles = []
    if len(coords) < 3:
        return triangles

    center_x = sum(p[0] for p in coords) / len(coords)
    center_y = sum(p[1] for p in coords) / len(coords)
    center = [center_x, center_y, z]

    for i in range(len(coords)):
        p1 = [coords[i][0], coords[i][1], z]
        p2 = [
            coords[(i + 1) % len(coords)][0],
            coords[(i + 1) % len(coords)][1],
            z,
        ]
        if invert:
            triangles.append([center, p1, p2])
        else:
            triangles.append([center, p2, p1])

    return triangles


def polygon_to_triangles(
    polygon: Polygon,
    height: float,
    ground_level: float = 0.0,
) -> list:
    """Extrude a footprint polygon into roof, floor, and side triangles."""
    triangles = []
    exterior = list(polygon.exterior.coords)

    if len(exterior) < 4:
        return triangles

    if exterior[0] == exterior[-1]:
        exterior = exterior[:-1]

    if len(exterior) < 3:
        return triangles

    base_tri = triangulate_2d(exterior, z=ground_level, invert=True)
    roof_tri = triangulate_2d(exterior, z=ground_level + height, invert=False)
    triangles.extend(base_tri + roof_tri)

    for i in range(len(exterior)):
        p1 = exterior[i]
        p2 = exterior[(i + 1) % len(exterior)]
        a = [p1[0], p1[1], ground_level]
        b = [p2[0], p2[1], ground_level]
        c = [p1[0], p1[1], ground_level + height]
        d = [p2[0], p2[1], ground_level + height]
        triangles.append([a, c, b])
        triangles.append([b, c, d])

    return triangles
