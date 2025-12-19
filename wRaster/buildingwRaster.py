import geopandas as gpd
import pandas as pd
import numpy as np
import struct
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import transform
import pyproj
import warnings
import os
import rasterio
from rasterio.transform import from_bounds
from rasterio.warp import reproject, Resampling
from scipy.interpolate import RegularGridInterpolator
import matplotlib.pyplot as plt
warnings.filterwarnings('ignore')

# Keep all the highway-related functions unchanged...
def load_elevation_raster(tif_path, target_crs='EPSG:32616', resample_factor=1.0):
    """
    Load and process elevation raster from TIF file
    
    Args:
        tif_path: Path to the TIF file
        target_crs: Target coordinate reference system
        resample_factor: Factor to resample the raster (1.0 = original, 0.5 = half resolution)
    
    Returns:
        dict: Contains elevation data, bounds, transform, and interpolator
    """
    print(f"📊 Loading elevation raster: {tif_path}")
    
    with rasterio.open(tif_path) as src:
        # Get raster info
        print(f"Original CRS: {src.crs}")
        print(f"Original bounds: {src.bounds}")
        print(f"Original shape: {src.shape}")
        print(f"Original resolution: {src.res}")
        
        # Read elevation data
        elevation = src.read(1)
        original_transform = src.transform
        original_crs = src.crs
        
        # Handle no-data values
        if src.nodata is not None:
            elevation = np.where(elevation == src.nodata, np.nan, elevation)
        
        print(f"Elevation range: {np.nanmin(elevation):.2f} to {np.nanmax(elevation):.2f} meters")
        
        # Reproject if necessary
        if str(original_crs) != target_crs:
            print(f"🔄 Reprojecting raster from {original_crs} to {target_crs}")
            
            # Calculate new bounds in target CRS
            from rasterio.warp import transform_bounds
            new_bounds = transform_bounds(original_crs, target_crs, *src.bounds)
            
            # Calculate new dimensions maintaining aspect ratio
            width_m = new_bounds[2] - new_bounds[0]
            height_m = new_bounds[3] - new_bounds[1]
            
            # Use original resolution as reference
            orig_res_x, orig_res_y = src.res
            new_width = int(width_m / (orig_res_x * resample_factor))
            new_height = int(height_m / (orig_res_y * resample_factor))
            
            # Create new transform
            new_transform = from_bounds(*new_bounds, new_width, new_height)
            
            # Reproject the data
            elevation_reproj = np.empty((new_height, new_width), dtype=elevation.dtype)
            
            reproject(
                source=elevation,
                destination=elevation_reproj,
                src_transform=original_transform,
                src_crs=original_crs,
                dst_transform=new_transform,
                dst_crs=target_crs,
                resampling=Resampling.bilinear
            )
            
            elevation = elevation_reproj
            transform = new_transform
            bounds = new_bounds
            
        else:
            # Same CRS, just resample if requested
            if resample_factor != 1.0:
                new_width = int(src.width * resample_factor)
                new_height = int(src.height * resample_factor)
                
                bounds = src.bounds
                transform = from_bounds(*bounds, new_width, new_height)
                
                elevation_resampled = np.empty((new_height, new_width), dtype=elevation.dtype)
                
                reproject(
                    source=elevation,
                    destination=elevation_resampled,
                    src_transform=original_transform,
                    src_crs=original_crs,
                    dst_transform=transform,
                    dst_crs=target_crs,
                    resampling=Resampling.bilinear
                )
                
                elevation = elevation_resampled
            else:
                transform = original_transform
                bounds = src.bounds
    
    print(f"Final raster shape: {elevation.shape}")
    print(f"Final bounds: {bounds}")
    print(f"Final elevation range: {np.nanmin(elevation):.2f} to {np.nanmax(elevation):.2f} meters")
    
    # Create coordinate arrays for interpolation
    height, width = elevation.shape
    x_coords = np.linspace(bounds[0], bounds[2], width)
    y_coords = np.linspace(bounds[3], bounds[1], height)  # Note: y is flipped for rasters
    
    # Handle NaN values for interpolation
    elevation_clean = np.where(np.isnan(elevation), 0, elevation)
    
    # Create interpolator
    interpolator = RegularGridInterpolator(
        (y_coords, x_coords), 
        elevation_clean,
        method='linear',
        bounds_error=False,
        fill_value=0
    )
    
    return {
        'elevation': elevation,
        'bounds': bounds,
        'transform': transform,
        'interpolator': interpolator,
        'x_coords': x_coords,
        'y_coords': y_coords,
        'shape': elevation.shape
    }

def get_elevation_at_points(points, elevation_data):
    """
    Get elevation values at specific points using interpolation
    
    Args:
        points: List of (x, y) coordinate tuples
        elevation_data: Dictionary from load_elevation_raster()
    
    Returns:
        List of elevation values
    """
    if not points:
        return []
    
    interpolator = elevation_data['interpolator']
    
    # Convert points to numpy array for efficient processing
    points_array = np.array(points)
    
    # Note: interpolator expects (y, x) order
    elevations = interpolator((points_array[:, 1], points_array[:, 0]))
    
    return elevations.tolist()

def get_building_ground_elevation(polygon, elevation_data, sample_points=5):
    """
    Get ground elevation for a building polygon by sampling multiple points
    
    Args:
        polygon: Shapely Polygon representing building footprint
        elevation_data: Dictionary from load_elevation_raster()
        sample_points: Number of points to sample for elevation
    
    Returns:
        Average ground elevation for the building
    """
    try:
        # Get polygon bounds
        minx, miny, maxx, maxy = polygon.bounds
        
        # Sample points within the polygon
        sample_x = np.linspace(minx, maxx, sample_points)
        sample_y = np.linspace(miny, maxy, sample_points)
        
        points_to_sample = []
        for x in sample_x:
            for y in sample_y:
                point = Point(x, y)
                if polygon.contains(point) or polygon.touches(point):
                    points_to_sample.append((x, y))
        
        # If no points inside polygon, use boundary points
        if not points_to_sample:
            boundary_coords = list(polygon.exterior.coords)
            points_to_sample = [(x, y) for x, y in boundary_coords[:sample_points]]
        
        # Get elevations
        elevations = get_elevation_at_points(points_to_sample, elevation_data)
        
        # Return average elevation, filtering out invalid values
        valid_elevations = [e for e in elevations if not np.isnan(e) and e != 0]
        
        if valid_elevations:
            return np.mean(valid_elevations)
        else:
            return 0.0  # Fallback to sea level
            
    except Exception as e:
        print(f"Warning: Error calculating building elevation: {e}")
        return 0.0

def polygon_to_triangles_with_elevation(polygon: Polygon, height: float, ground_elevation: float):
    """
    Extrude 2D polygon vertically into 3D triangles using ground elevation as base
    
    Args:
        polygon: Shapely Polygon
        height: Building height above ground
        ground_elevation: Ground elevation from raster
    
    Returns:
        List of triangles
    """
    triangles = []
    exterior = list(polygon.exterior.coords)
    
    if len(exterior) < 4:  # Need at least 3 unique points + closing point
        return triangles
    
    # Remove duplicate closing point for processing
    if exterior[0] == exterior[-1]:
        exterior = exterior[:-1]
    
    if len(exterior) < 3:
        return triangles
    
    # Building base is at ground elevation, top is at ground + height
    base_level = ground_elevation
    top_level = ground_elevation + height
    
    # Triangulate base (at ground level) and roof (at ground + height)
    base_tri = triangulate_2d(exterior, z=base_level, invert=True)  # Invert for downward normal
    roof_tri = triangulate_2d(exterior, z=top_level, invert=False)  # Upward normal
    
    triangles.extend(base_tri + roof_tri)
    
    # Side walls - ensure proper winding order for outward normals
    for i in range(len(exterior)):
        p1 = exterior[i]
        p2 = exterior[(i + 1) % len(exterior)]
        
        # Bottom edge vertices (at ground elevation)
        a = [p1[0], p1[1], base_level]
        b = [p2[0], p2[1], base_level]
        # Top edge vertices (at ground + height)
        c = [p1[0], p1[1], top_level]
        d = [p2[0], p2[1], top_level]
        
        # Two triangles per wall - ensure outward normals
        triangles.append([a, c, b])  # First triangle
        triangles.append([b, c, d])  # Second triangle
    
    return triangles

# Keep all other highway functions unchanged...
# [Include all the highway functions here: create_highway_geometry_with_elevation, visualize_elevation_profile, get_highway_config, etc.]

# Updated building functions...

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
        
        # Handle missing CRS
        if gdf.crs is None:
            gdf = fix_shapefile_crs(path)
        
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

def fix_shapefile_crs(shapefile_path):
    """Fix missing CRS by reading from .prj file"""
    buildings = gpd.read_file(shapefile_path)
    
    if buildings.crs is None:
        print("⚠️ No CRS detected. Checking for .prj file...")
        prj_file = shapefile_path.replace('.shp', '.prj')
        try:
            with open(prj_file, 'r') as f:
                prj_content = f.read().strip()
                print(f"Found .prj file content: {prj_content[:100]}...")
                
                buildings = buildings.set_crs(prj_content)
                print(f"✅ CRS set from .prj file: {buildings.crs}")
                
        except FileNotFoundError:
            print(f"❌ No .prj file found at {prj_file}")
            print("🔧 Assuming EPSG:4326 (WGS84). Please verify this is correct.")
            buildings = buildings.set_crs('EPSG:4326')
        except Exception as e:
            print(f"❌ Error reading .prj file: {e}")
            buildings = buildings.set_crs('EPSG:4326')
    
    return buildings

def estimate_heights_from_footprint_area(shapefile_path, output_path=None):
    """Estimate building heights based on footprint area and urban planning rules"""
    
    print("📐 Estimating heights from building footprint areas...")
    
    buildings = gpd.read_file(shapefile_path)
    
    # Handle missing CRS using the fix function
    if buildings.crs is None:
        buildings = fix_shapefile_crs(shapefile_path)
    
    print(f"Current CRS: {buildings.crs}")
    
    # Calculate footprint area
    if buildings.crs.to_epsg() == 4326:
        # Convert to metric CRS for area calculation
        print("🔄 Converting to UTM Zone 16N for accurate area calculation...")
        buildings_metric = buildings.to_crs('EPSG:32616')  # UTM Zone 16N for Milwaukee
        buildings['area_sqm'] = buildings_metric.geometry.area
    else:
        # Already in a projected CRS, calculate area directly
        buildings['area_sqm'] = buildings.geometry.area
    
    # Height estimation rules (rough approximations)
    def estimate_height(area):
        if area < 100:  # Small buildings (< 100 sqm)
            return 6.0  # Single story
        elif area < 300:  # Medium buildings
            return 9.0  # 1-2 stories
        elif area < 800:  # Large buildings  
            return 15.0  # 2-3 stories
        elif area < 2000:  # Very large buildings
            return 25.0  # 4-6 stories
        else:  # Massive buildings
            return 40.0  # 7+ stories
    
    buildings['estimated_height'] = buildings['area_sqm'].apply(estimate_height)
    
    if output_path:
        buildings.to_file(output_path)
    
    print(f"✅ Estimated heights for {len(buildings)} buildings")
    print("Height distribution:")
    print(buildings['estimated_height'].value_counts().sort_index())
    
    return buildings

def triangulate_2d(coords, z=0, invert=False):
    """Improved fan triangulation for simple polygons"""
    triangles = []
    
    if len(coords) < 3:
        return triangles
    
    # Use centroid for fan triangulation
    center_x = sum(p[0] for p in coords) / len(coords)
    center_y = sum(p[1] for p in coords) / len(coords)
    center = [center_x, center_y, z]
    
    # Create triangles with proper winding order
    for i in range(len(coords)):
        p1 = [coords[i][0], coords[i][1], z]
        p2 = [coords[(i + 1) % len(coords)][0], coords[(i + 1) % len(coords)][1], z]
        
        if invert:
            triangles.append([center, p1, p2])  # Clockwise (downward normal)
        else:
            triangles.append([center, p2, p1])  # Counter-clockwise (upward normal)
    
    return triangles

def calculate_normal(tri):
    """Calculate unit normal vector for triangle"""
    a, b, c = np.array(tri[0]), np.array(tri[1]), np.array(tri[2])
    normal = np.cross(b - a, c - a)
    norm = np.linalg.norm(normal)
    return normal / norm if norm > 1e-10 else np.array([0, 0, 1])

def write_stl_binary(filename, triangles):
    """Write triangles to binary STL file"""
    with open(filename, 'wb') as f:
        # STL header (80 bytes)
        header = b'Building STL with Elevation for OpenFOAM'
        f.write(header + b'\0' * (80 - len(header)))
        
        # Number of triangles (4 bytes)
        f.write(struct.pack('<I', len(triangles)))
        
        # Write each triangle
        for tri in triangles:
            normal = calculate_normal(tri)
            
            # Normal vector (12 bytes)
            f.write(struct.pack('<fff', float(normal[0]), float(normal[1]), float(normal[2])))
            
            # Three vertices (36 bytes)
            for vertex in tri:
                f.write(struct.pack('<fff', float(vertex[0]), float(vertex[1]), float(vertex[2])))
            
            # Attribute byte count (2 bytes) - unused
            f.write(struct.pack('<H', 0))

def get_local_transform(gdf):
    """Create transformation to local coordinate system centered on data bounds"""
    bounds = gdf.total_bounds
    center_x = (bounds[0] + bounds[2]) / 2
    center_y = (bounds[1] + bounds[3]) / 2
    
    return center_x, center_y

def extrude_buildings_with_elevation(shapefile, tif_path, output_stl, height_col=None, 
                                   default_height=10.0, use_local_coords=True, 
                                   target_crs='EPSG:32616', estimate_heights=True, 
                                   combined_offset=None, shapefile_list=None,
                                   elevation_offset=0.0):
    """
    Convert building footprints to extruded STL file using elevation raster as base
    
    Parameters:
    -----------
    shapefile : str
        Path to input shapefile
    tif_path : str
        Path to elevation raster TIF file
    output_stl : str  
        Path to output STL file
    height_col : str, optional
        Column name containing building heights
    default_height : float
        Default height for buildings without height data
    use_local_coords : bool
        Whether to translate to local coordinate system
    target_crs : str
        Target CRS (e.g., 'EPSG:32616' for UTM Zone 16N)
    estimate_heights : bool
        Whether to estimate heights from footprint areas
    combined_offset : tuple, optional
        Pre-calculated combined offset (offset_x, offset_y)
    shapefile_list : list, optional
        List of all shapefiles for combined offset calculation
    elevation_offset : float
        Additional offset above ground elevation (meters)
    """
    
    print(f"🏢 Converting buildings with elevation data")
    print(f"Building shapefile: {shapefile}")
    print(f"Elevation TIF: {tif_path}")
    
    # Load elevation data
    elevation_data = load_elevation_raster(tif_path, target_crs)
    
    # First, estimate heights if requested
    if estimate_heights:
        print("\n🔄 Step 1: Estimating building heights from footprint areas...")
        gdf = estimate_heights_from_footprint_area(shapefile)
        # Use estimated heights as the height column
        height_col = 'estimated_height'
    else:
        gdf = gpd.read_file(shapefile)
        # Handle missing CRS
        if gdf.crs is None:
            gdf = fix_shapefile_crs(shapefile)
    
    print(f"\n🔄 Step 2: Processing geometry for STL export...")
    print(f"Original CRS: {gdf.crs}")
    print(f"Number of features: {len(gdf)}")
    
    # Handle coordinate system
    if gdf.crs.to_epsg() == 4326:
        print(f"⚠️ Reprojecting from EPSG:4326 to {target_crs}")
        gdf = gdf.to_crs(target_crs)
    elif gdf.crs.to_epsg() != int(target_crs.split(':')[1]):
        print(f"⚠️ Reprojecting from {gdf.crs} to {target_crs}")
        gdf = gdf.to_crs(target_crs)
    
    # Filter valid geometries
    gdf = gdf[gdf.geometry.notna()]
    gdf = gdf[gdf.is_valid]
    
    print(f"Valid geometries: {len(gdf)}")
    
    # Get coordinate transformation offset
    offset_x, offset_y = (0, 0)
    if use_local_coords:
        if combined_offset is not None:
            # Use pre-calculated combined offset
            offset_x, offset_y = combined_offset
            print(f"Using provided combined offset: ({offset_x:.2f}, {offset_y:.2f})")
        elif shapefile_list is not None:
            # Calculate combined offset from multiple shapefiles
            target_epsg = int(target_crs.split(':')[1])
            offset_x, offset_y = get_combined_offset(shapefile_list, target_epsg)
        else:
            # Fall back to individual shapefile transform
            offset_x, offset_y = get_local_transform(gdf)
            print(f"Local coordinate offset: ({offset_x:.2f}, {offset_y:.2f})")
    
    all_triangles = []
    processed_buildings = 0
    height_stats = []
    elevation_stats = []
    
    for idx, row in gdf.iterrows():
        geom = row.geometry
        
        if geom.is_empty or not geom.is_valid:
            continue
            
        # Get building height
        height = default_height
        if height_col and height_col in row and pd.notna(row[height_col]):
            try:
                height = float(row[height_col])
                if height <= 0:
                    height = default_height
            except (ValueError, TypeError):
                height = default_height
        
        height_stats.append(height)
        
        # Apply local coordinate transformation first
        if use_local_coords:
            geom = transform(lambda x, y: (x - offset_x, y - offset_y), geom)
        
        # Get ground elevation for this building from the raster data
        # Transform geometry back to raster coordinates for elevation lookup
        if use_local_coords:
            geom_for_elevation = transform(lambda x, y: (x + offset_x, y + offset_y), geom)
        else:
            geom_for_elevation = geom
            
        ground_elevation = get_building_ground_elevation(geom_for_elevation, elevation_data) + elevation_offset
        elevation_stats.append(ground_elevation)
        
        if idx == 0:
            print(f"First building ground elevation: {ground_elevation:.2f}m")
        # Process geometry with elevation
        if isinstance(geom, Polygon):
            tris = polygon_to_triangles_with_elevation(geom, height, ground_elevation)
            all_triangles.extend(tris)
            processed_buildings += 1
            
        elif isinstance(geom, MultiPolygon):
            for poly in geom.geoms:
                if poly.is_valid and not poly.is_empty:
                    tris = polygon_to_triangles_with_elevation(poly, height, ground_elevation)
                    all_triangles.extend(tris)
            processed_buildings += 1
        
        if processed_buildings % 25 == 0:
            print(f"Processed {processed_buildings} buildings...")
    
    if not all_triangles:
        print("❌ No triangles generated!")
        return
    
    # Write STL file
    write_stl_binary(output_stl, all_triangles)
    
    print(f"\n✅ Building processing complete!")
    print(f"✅ Processed {processed_buildings} buildings")
    print(f"✅ Generated {len(all_triangles)} triangles")
    print(f"✅ STL file written to: {output_stl}")
    
    # Print height statistics
    if height_stats:
        height_array = np.array(height_stats)
        print(f"\nBuilding height statistics:")
        print(f"  Mean height: {height_array.mean():.2f}m")
        print(f"  Min height: {height_array.min():.2f}m")
        print(f"  Max height: {height_array.max():.2f}m")
        print(f"  Std deviation: {height_array.std():.2f}m")
    
    # Print elevation statistics
    if elevation_stats:
        elev_array = np.array(elevation_stats)
        print(f"\nGround elevation statistics:")
        print(f"  Mean elevation: {elev_array.mean():.2f}m")
        print(f"  Min elevation: {elev_array.min():.2f}m")
        print(f"  Max elevation: {elev_array.max():.2f}m")
        print(f"  Elevation range: {elev_array.max() - elev_array.min():.2f}m")
    
    # Print bounds for OpenFOAM reference
    if all_triangles:
        all_points = np.array([point for triangle in all_triangles for point in triangle])
        bounds = {
            'x_min': all_points[:, 0].min(),
            'x_max': all_points[:, 0].max(),
            'y_min': all_points[:, 1].min(), 
            'y_max': all_points[:, 1].max(),
            'z_min': all_points[:, 2].min(),
            'z_max': all_points[:, 2].max()
        }
        
        print(f"\nBuilding mesh bounds:")
        print(f"X: [{bounds['x_min']:.2f}, {bounds['x_max']:.2f}]")
        print(f"Y: [{bounds['y_min']:.2f}, {bounds['y_max']:.2f}]") 
        print(f"Z: [{bounds['z_min']:.2f}, {bounds['z_max']:.2f}]")
        
        return {
            'buildings_processed': processed_buildings,
            'triangles_generated': len(all_triangles),
            'bounds': bounds,
            'coordinate_system': str(gdf.crs),
            'offset_used': (offset_x, offset_y),
            'height_stats': {'mean': height_array.mean(), 'min': height_array.min(), 'max': height_array.max()},
            'elevation_stats': {'mean': elev_array.mean(), 'min': elev_array.min(), 'max': elev_array.max()},
            'elevation_data_bounds': elevation_data['bounds']
        }

# Keep all highway functions here...
# [Include the complete highway processing functions]

# Example usage
if __name__ == "__main__":
    
    # Example with buildings using elevation raster
    building_shp = "windAroundBuildings/Tools/input/kilbourntoClybourn.shp"
    # elevation_tif = "windAroundBuildings/Tools/input/rasterKilbourn.tif" 
    elevation_tif = "windAroundBuildings/Tools/input/demdataforground/demdataforground.tif"
    building_output = "windAroundBuildings/Tools/output/wRaster/buildingsKilbourn.stl"
    
    # Offset values (use your hardcoded values or calculate from other shapefiles)
    HARDCODED_OFFSET = (424265.04, 4765565.05)  
    
    # Check if files exist
    if not os.path.exists(building_shp):
        print(f"❌ Building shapefile not found: {building_shp}")
        exit(1)
    
    if not os.path.exists(elevation_tif):
        print(f"❌ Elevation TIF file not found: {elevation_tif}")
        print("Please update the elevation_tif path to your actual TIF file.")
        exit(1)
    
    # Generate buildings with elevation
    result = extrude_buildings_with_elevation(
        shapefile=building_shp,
        tif_path=elevation_tif,
        output_stl=building_output,
        height_col=None,                # Let it use estimated heights
        default_height=12.0,            # Default height in meters
        use_local_coords=True,          # Translate to local coordinates
        target_crs='EPSG:32616',        # UTM Zone 16N for Milwaukee
        estimate_heights=True,          # Enable height estimation
        combined_offset=(HARDCODED_OFFSET[0], HARDCODED_OFFSET[1]),  # Use hardcoded offset
        elevation_offset=0.0            # Buildings sit directly on ground
    )
    
    print(f"\n📊 Building Processing Summary:")
    for k, v in result.items():
        print(f"  {k}: {v}")
