"""Terrain-following building facades for DEM-aligned extrusion."""

from __future__ import annotations

from shapely.geometry import LineString, MultiPolygon, Polygon

from cfd_geometry.raster.elevation import local_ground_z


def _exterior_ring(polygon: Polygon, samples_per_edge: int) -> list[tuple[float, float]]:
    coords = list(polygon.exterior.coords)
    if len(coords) >= 2 and coords[0] == coords[-1]:
        coords = coords[:-1]
    if len(coords) < 3:
        return []

    if samples_per_edge <= 1:
        return [(float(x), float(y)) for x, y in coords]

    ring: list[tuple[float, float]] = []
    n = len(coords)
    for i in range(n):
        p0 = coords[i]
        p1 = coords[(i + 1) % n]
        seg = LineString([p0, p1])
        for k in range(samples_per_edge):
            t = k / samples_per_edge
            pt = seg.interpolate(t, normalized=True)
            ring.append((float(pt.x), float(pt.y)))
    return ring


def polygon_to_triangles_stepped_facade(
    polygon: Polygon,
    height: float,
    elevation_data: dict,
    z_offset: float,
    *,
    samples_per_edge: int = 2,
    world_offset: tuple[float, float] = (0.0, 0.0),
) -> list[list[list[float]]]:
    """
    Extrude a footprint with a DEM-following base and vertical upper facade.

    The base ring follows local ground elevation; the roof stays flat at
    ``max(base_z) + height`` so the mesh stays suitable for block-style CFD.
    """
    if height <= 0:
        return []

    ring = _exterior_ring(polygon, samples_per_edge)
    if len(ring) < 3:
        return []

    ox, oy = world_offset
    base_z: list[float] = []
    for x, y in ring:
        base_z.append(
            local_ground_z(x + ox, y + oy, elevation_data, z_offset)
        )

    z_top = float(max(base_z)) + height
    roof_coords = [[x, y, z_top] for (x, y) in ring]
    base_coords = [[x, y, base_z[i]] for i, (x, y) in enumerate(ring)]

    triangles: list[list[list[float]]] = []
    triangles.extend(_triangulate_ring_3d(base_coords, invert=True))
    triangles.extend(_triangulate_ring_3d(roof_coords, invert=False))

    n = len(ring)
    for i in range(n):
        j = (i + 1) % n
        a = base_coords[i]
        b = base_coords[j]
        c = [a[0], a[1], z_top]
        d = [b[0], b[1], z_top]
        triangles.append([a, c, b])
        triangles.append([b, c, d])

    return triangles


def _triangulate_ring_3d(
    coords: list[list[float]],
    *,
    invert: bool,
) -> list[list[list[float]]]:
    """Fan triangulation for a 3D ring (vertices carry their own Z)."""
    if len(coords) < 3:
        return []
    cx = sum(p[0] for p in coords) / len(coords)
    cy = sum(p[1] for p in coords) / len(coords)
    cz = sum(p[2] for p in coords) / len(coords)
    center = [cx, cy, cz]
    triangles: list[list[list[float]]] = []
    for i in range(len(coords)):
        p1 = coords[i]
        p2 = coords[(i + 1) % len(coords)]
        if invert:
            triangles.append([center, p1, p2])
        else:
            triangles.append([center, p2, p1])
    return triangles


def extrude_geometry_stepped_facade(
    geom: Polygon | MultiPolygon,
    height: float,
    elevation_data: dict,
    z_offset: float,
    *,
    samples_per_edge: int = 2,
    world_offset: tuple[float, float] = (0.0, 0.0),
) -> list[list[list[float]]]:
    """Extrude Polygon or MultiPolygon with stepped facade triangles."""
    if isinstance(geom, Polygon):
        polys = [geom]
    elif isinstance(geom, MultiPolygon):
        polys = list(geom.geoms)
    else:
        return []

    all_tris: list[list[list[float]]] = []
    for poly in polys:
        if poly.is_empty:
            continue
        all_tris.extend(
            polygon_to_triangles_stepped_facade(
                poly,
                height,
                elevation_data,
                z_offset,
                samples_per_edge=samples_per_edge,
                world_offset=world_offset,
            )
        )
    return all_tris
