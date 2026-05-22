"""Extrude footprints with trimesh (proper polygon triangulation)."""

from __future__ import annotations

import trimesh
from shapely.geometry import MultiPolygon, Polygon


def _fix_polygon(polygon: Polygon) -> Polygon | None:
    if polygon.is_empty:
        return None
    if not polygon.is_valid:
        fixed = polygon.buffer(0)
        if isinstance(fixed, Polygon) and not fixed.is_empty:
            polygon = fixed
        else:
            return None
    if polygon.area <= 0:
        return None
    return polygon


def extrude_polygon_to_mesh(
    polygon: Polygon,
    height: float,
    *,
    ground_level: float = 0.0,
) -> trimesh.Trimesh | None:
    """Extrude a single footprint to a watertight mesh."""
    if height <= 0:
        return None

    polygon = _fix_polygon(polygon)
    if polygon is None:
        return None

    try:
        mesh = trimesh.creation.extrude_polygon(polygon, height)
    except Exception:
        return None

    if mesh is None or len(mesh.faces) == 0:
        return None

    if ground_level != 0.0:
        mesh.apply_translation((0.0, 0.0, ground_level))

    return mesh


def mesh_to_triangle_list(mesh: trimesh.Trimesh) -> list[list[list[float]]]:
    """Convert a trimesh to the triangle list format used by ``write_stl_binary``."""
    triangles: list[list[list[float]]] = []
    verts = mesh.vertices
    for face in mesh.faces:
        triangles.append(
            [
                verts[face[0]].tolist(),
                verts[face[1]].tolist(),
                verts[face[2]].tolist(),
            ]
        )
    return triangles


def extrude_geometry_to_triangles(
    geom: Polygon | MultiPolygon,
    height: float,
    *,
    ground_level: float = 0.0,
) -> list[list[list[float]]]:
    """Extrude a Polygon or MultiPolygon and return STL-ready triangles."""
    meshes: list[trimesh.Trimesh] = []

    if isinstance(geom, Polygon):
        polys = [geom]
    elif isinstance(geom, MultiPolygon):
        polys = list(geom.geoms)
    else:
        return []

    for poly in polys:
        mesh = extrude_polygon_to_mesh(poly, height, ground_level=ground_level)
        if mesh is not None:
            meshes.append(mesh)

    if not meshes:
        return []

    if len(meshes) == 1:
        combined = meshes[0]
    else:
        combined = trimesh.util.concatenate(meshes)

    return mesh_to_triangle_list(combined)
