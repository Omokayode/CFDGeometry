"""CFD geometry: GIS and DEM data to STL for urban wind simulations."""

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "get_combined_offset",
    "get_local_transform",
    "extrude_buildings_to_stl",
    "extrude_buildings_to_stl_with_dem",
    "extrude_highways_to_stl",
    "extrude_trees_to_stl",
    "extrude_trees_to_stl_with_dem",
    "dem_to_stl_with_offset",
    "STLClipper",
    "OptimizedRectangularBaseGenerator",
]

_LAZY_EXPORTS = {
    "get_combined_offset": ("cfd_geometry.geo.offsets", "get_combined_offset"),
    "get_local_transform": ("cfd_geometry.geo.offsets", "get_local_transform"),
    "extrude_buildings_to_stl": ("cfd_geometry.buildings.extrude", "extrude_buildings_to_stl"),
    "extrude_buildings_to_stl_with_dem": (
        "cfd_geometry.buildings.extrude_dem",
        "extrude_buildings_to_stl_with_dem",
    ),
    "extrude_highways_to_stl": ("cfd_geometry.highways.extrude", "extrude_highways_to_stl"),
    "extrude_trees_to_stl": ("cfd_geometry.trees.extrude", "extrude_trees_to_stl"),
    "extrude_trees_to_stl_with_dem": (
        "cfd_geometry.trees.extrude_dem",
        "extrude_trees_to_stl_with_dem",
    ),
    "dem_to_stl_with_offset": ("cfd_geometry.terrain.dem_to_stl", "dem_to_stl_with_offset"),
    "STLClipper": ("cfd_geometry.clipper.clipper", "STLClipper"),
    "OptimizedRectangularBaseGenerator": (
        "cfd_geometry.base.terrain_base",
        "OptimizedRectangularBaseGenerator",
    ),
}


def __getattr__(name: str):
    if name in _LAZY_EXPORTS:
        module_path, attr = _LAZY_EXPORTS[name]
        import importlib

        return getattr(importlib.import_module(module_path), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
