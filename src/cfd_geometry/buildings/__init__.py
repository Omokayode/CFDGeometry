"""Building footprint load, height assignment, and STL extrusion."""

__all__ = [
    "apply_osm_heights_to_gdf",
    "estimate_height_from_attributes",
    "estimate_heights_from_footprint_area",
    "extrude_buildings_gdf_to_stl",
    "extrude_buildings_to_stl",
    "extrude_buildings_to_stl_with_dem",
    "extrude_buildings_to_stl_with_lidar",
    "prepare_buildings_gdf",
    "parse_height_string",
    "process_shapefiles_to_stl",
]


def __getattr__(name: str):
    if name in (
        "extrude_buildings_gdf_to_stl",
        "extrude_buildings_to_stl",
        "process_shapefiles_to_stl",
    ):
        from cfd_geometry.buildings.extrude import (
            extrude_buildings_gdf_to_stl,
            extrude_buildings_to_stl,
            process_shapefiles_to_stl,
        )

        return {
            "extrude_buildings_gdf_to_stl": extrude_buildings_gdf_to_stl,
            "extrude_buildings_to_stl": extrude_buildings_to_stl,
            "process_shapefiles_to_stl": process_shapefiles_to_stl,
        }[name]
    if name == "extrude_buildings_to_stl_with_dem":
        from cfd_geometry.buildings.extrude_dem import extrude_buildings_to_stl_with_dem

        return extrude_buildings_to_stl_with_dem
    if name == "extrude_buildings_to_stl_with_lidar":
        from cfd_geometry.buildings.extrude_lidar import extrude_buildings_to_stl_with_lidar

        return extrude_buildings_to_stl_with_lidar
    if name == "prepare_buildings_gdf":
        from cfd_geometry.buildings.load import prepare_buildings_gdf

        return prepare_buildings_gdf
    if name in (
        "apply_osm_heights_to_gdf",
        "estimate_height_from_attributes",
        "parse_height_string",
    ):
        from cfd_geometry.buildings.heights_osm import (
            apply_osm_heights_to_gdf,
            estimate_height_from_attributes,
            parse_height_string,
        )

        return {
            "apply_osm_heights_to_gdf": apply_osm_heights_to_gdf,
            "estimate_height_from_attributes": estimate_height_from_attributes,
            "parse_height_string": parse_height_string,
        }[name]
    if name == "estimate_heights_from_footprint_area":
        from cfd_geometry.buildings.heights import estimate_heights_from_footprint_area

        return estimate_heights_from_footprint_area
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
