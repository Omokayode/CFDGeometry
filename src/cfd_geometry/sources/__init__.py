"""Pluggable strategies for heights, ground, and trees."""

from cfd_geometry.sources.base import (
    GroundSourceStrategy,
    HeightAssignOptions,
    HeightSourceStrategy,
    TreeModelStrategy,
)

__all__ = [
    "AreaHeightSource",
    "CanopyTreeModel",
    "ColumnHeightSource",
    "CompositeHeightSource",
    "CylinderTreeModel",
    "DefaultHeightSource",
    "DemGroundSource",
    "FlatGroundSource",
    "GroundSourceStrategy",
    "HeightAssignOptions",
    "HeightSourceStrategy",
    "OsmHeightSource",
    "RasterHeightSource",
    "SkipTreeModel",
    "SphereTreeModel",
    "TreeModelStrategy",
    "ground_source_from_name",
    "height_source_from_name",
    "tree_model_from_name",
]

_LAZY = {
    "AreaHeightSource": ("cfd_geometry.sources.height", "AreaHeightSource"),
    "ColumnHeightSource": ("cfd_geometry.sources.height", "ColumnHeightSource"),
    "CompositeHeightSource": ("cfd_geometry.sources.height", "CompositeHeightSource"),
    "DefaultHeightSource": ("cfd_geometry.sources.height", "DefaultHeightSource"),
    "OsmHeightSource": ("cfd_geometry.sources.height", "OsmHeightSource"),
    "RasterHeightSource": ("cfd_geometry.sources.height", "RasterHeightSource"),
    "height_source_from_name": ("cfd_geometry.sources.height", "height_source_from_name"),
    "DemGroundSource": ("cfd_geometry.sources.ground", "DemGroundSource"),
    "FlatGroundSource": ("cfd_geometry.sources.ground", "FlatGroundSource"),
    "ground_source_from_name": ("cfd_geometry.sources.ground", "ground_source_from_name"),
    "CanopyTreeModel": ("cfd_geometry.sources.trees", "CanopyTreeModel"),
    "CylinderTreeModel": ("cfd_geometry.sources.trees", "CylinderTreeModel"),
    "SkipTreeModel": ("cfd_geometry.sources.trees", "SkipTreeModel"),
    "SphereTreeModel": ("cfd_geometry.sources.trees", "SphereTreeModel"),
    "tree_model_from_name": ("cfd_geometry.sources.trees", "tree_model_from_name"),
}


def __getattr__(name: str):
    if name in _LAZY:
        module_name, attr = _LAZY[name]
        import importlib

        return getattr(importlib.import_module(module_name), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
