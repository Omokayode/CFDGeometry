"""Point tree shapefiles to STL."""

__all__ = ["extrude_trees_to_stl", "extrude_trees_to_stl_with_dem"]


def __getattr__(name: str):
    if name == "extrude_trees_to_stl":
        from cfd_geometry.trees.extrude import extrude_trees_to_stl

        return extrude_trees_to_stl
    if name == "extrude_trees_to_stl_with_dem":
        from cfd_geometry.trees.extrude_dem import extrude_trees_to_stl_with_dem

        return extrude_trees_to_stl_with_dem
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
