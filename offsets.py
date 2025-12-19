import geopandas as gpd
import pandas as pd
def get_combined_offset(shapefile_paths, target_epsg=32616):
    """
    Compute the center of bounding box from multiple shapefiles (projected).
    
    Args:
        shapefile_paths (list): List of paths to shapefiles.
        target_epsg (int): EPSG code for reprojection (default = UTM Zone 16N).
    
    Returns:
        (offset_x, offset_y): Tuple of center coordinates.
    """
    all_geoms = []
    
    for path in shapefile_paths:
        gdf = gpd.read_file(path)
        
        if gdf.crs.to_epsg() != target_epsg:
            print(f"🔄 Reprojecting {path} from {gdf.crs} to EPSG:{target_epsg}")
            gdf = gdf.to_crs(epsg=target_epsg)
        
        all_geoms.append(gdf[["geometry"]])
    
    # Combine all geometries
    combined_gdf = gpd.GeoDataFrame(pd.concat(all_geoms, ignore_index=True), crs=f"EPSG:{target_epsg}")
    
    bounds = combined_gdf.total_bounds
    offset_x = (bounds[0] + bounds[2]) / 2
    offset_y = (bounds[1] + bounds[3]) / 2
    print(f"✅ Combined offset: ({offset_x:.2f}, {offset_y:.2f})")
    
    return offset_x, offset_y

tree_shp = "windAroundBuildings/Tools/input/treesshapefileKilbourn.shp"
buildings_shp = "windAroundBuildings/Tools/input/kilbourntoClybourn.shp"
offset_x, offset_y = get_combined_offset([tree_shp, buildings_shp])