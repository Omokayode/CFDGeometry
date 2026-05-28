"""Ground elevation strategies."""

from __future__ import annotations

from dataclasses import dataclass

from cfd_geometry.raster.elevation import local_ground_z


@dataclass
class FlatGroundSource:
    """Flat ground plane at a constant Z."""

    z: float = 0.0
    name: str = "flat"

    def ground_z(self, x: float, y: float, *, polygon=None) -> float:
        return self.z


@dataclass
class DemGroundSource:
    """Sample ground from a preloaded DEM / elevation_data dict."""

    elevation_data: dict
    z_offset: float = 0.0
    elevation_offset: float = 0.0
    use_polygon_mean: bool = False
    name: str = "dem"

    def ground_z(self, x: float, y: float, *, polygon=None) -> float:
        if self.use_polygon_mean and polygon is not None:
            from cfd_geometry.raster.elevation import ground_elevation_for_polygon

            world_x = x
            world_y = y
            if hasattr(polygon, "centroid"):
                c = polygon.centroid
                world_x, world_y = c.x, c.y
            elev = ground_elevation_for_polygon(polygon, self.elevation_data)
            return elev - self.z_offset + self.elevation_offset
        return (
            local_ground_z(x, y, self.elevation_data, self.z_offset)
            + self.elevation_offset
        )


def ground_source_from_name(
    name: str,
    *,
    z: float = 0.0,
    elevation_data: dict | None = None,
    z_offset: float = 0.0,
    elevation_offset: float = 0.0,
) -> FlatGroundSource | DemGroundSource:
    """Names: ``flat``, ``dem``."""
    key = name.lower().strip()
    if key == "flat":
        return FlatGroundSource(z=z)
    if key == "dem":
        if elevation_data is None:
            raise ValueError("dem ground source requires elevation_data=")
        return DemGroundSource(
            elevation_data=elevation_data,
            z_offset=z_offset,
            elevation_offset=elevation_offset,
        )
    raise ValueError(f"Unknown ground source: {name!r}")
