"""Extrude footprints with trimesh (proper polygon triangulation)."""

from __future__ import annotations

import trimesh
import trimesh.util
from shapely.geometry import MultiPolygon, Polygon

# Prefer mapbox-earcut (FSF-friendly); manifold3d is optional fallback
_ENGINE_ORDER = ("earcut", "manifold")


def resolve_triangulation_engine() -> str | None:
    """Return the first installed trimesh triangulation engine name."""
    from trimesh import creation

    for name, available in creation._engines:
        if available:
            return name

    for name in _ENGINE_ORDER:
        if name == "earcut":
            try:
                import mapbox_earcut  # noqa: F401

                return "earcut"
            except ImportError:
                continue
        if name == "manifold":
            try:
                import manifold3d  # noqa: F401

                return "manifold"
            except ImportError:
                continue
    return None


def ensure_triangulation_backend() -> str:
    """Require a working triangulation backend or raise a clear install hint."""
    engine = resolve_triangulation_engine()
    if engine is None:
        raise RuntimeError(
            "No polygon triangulation backend installed (trimesh cannot extrude footprints). "
            "Install one of:\n"
            "  pip install mapbox-earcut\n"
            "  pip install manifold3d"
        )
    return engine


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
    engine: str | None = None,
) -> trimesh.Trimesh | None:
    """Extrude a single footprint to a watertight mesh."""
    if height <= 0:
        return None

    polygon = _fix_polygon(polygon)
    if polygon is None:
        return None

    if engine is None:
        engine = ensure_triangulation_backend()

    try:
        mesh = trimesh.creation.extrude_polygon(polygon, height, engine=engine)
    except ValueError as exc:
        if "triangulation" in str(exc).lower() or "engine" in str(exc).lower():
            raise RuntimeError(
                "Polygon triangulation failed. Install: pip install mapbox-earcut"
            ) from exc
        return None
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
    engine: str | None = None,
) -> list[list[list[float]]]:
    """Extrude a Polygon or MultiPolygon and return STL-ready triangles."""
    if engine is None:
        engine = ensure_triangulation_backend()

    meshes: list[trimesh.Trimesh] = []

    if isinstance(geom, Polygon):
        polys = [geom]
    elif isinstance(geom, MultiPolygon):
        polys = list(geom.geoms)
    else:
        return []

    for poly in polys:
        mesh = extrude_polygon_to_mesh(
            poly, height, ground_level=ground_level, engine=engine
        )
        if mesh is not None:
            meshes.append(mesh)

    if not meshes:
        return []

    if len(meshes) == 1:
        combined = meshes[0]
    else:
        combined = trimesh.util.concatenate(meshes)

    return mesh_to_triangle_list(combined)
