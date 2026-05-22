"""Pluggable strategies for heights, ground, and trees."""

from cfd_geometry.sources.base import (
    GroundSourceStrategy,
    HeightAssignOptions,
    HeightSourceStrategy,
    TreeModelStrategy,
)
from cfd_geometry.sources.ground import (
    DemGroundSource,
    FlatGroundSource,
    ground_source_from_name,
)
from cfd_geometry.sources.height import (
    AreaHeightSource,
    ColumnHeightSource,
    CompositeHeightSource,
    DefaultHeightSource,
    OsmHeightSource,
    RasterHeightSource,
    height_source_from_name,
)
from cfd_geometry.sources.trees import (
    CanopyTreeModel,
    CylinderTreeModel,
    SkipTreeModel,
    SphereTreeModel,
    tree_model_from_name,
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
