"""CFD geometry: GIS and DEM data to STL for urban wind simulations."""

__version__ = "0.1.0"

from cfd_geometry.geo.offsets import get_combined_offset, get_local_transform
from cfd_geometry.buildings.extrude import extrude_buildings_to_stl
from cfd_geometry.terrain.dem_to_stl import dem_to_stl_with_offset
from cfd_geometry.clipper.clipper import STLClipper
from cfd_geometry.base.terrain_base import OptimizedRectangularBaseGenerator

__all__ = [
    "__version__",
    "get_combined_offset",
    "get_local_transform",
    "extrude_buildings_to_stl",
    "dem_to_stl_with_offset",
    "STLClipper",
    "OptimizedRectangularBaseGenerator",
]
