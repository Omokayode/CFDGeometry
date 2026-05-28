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
    
    # Create x and y coordinate arrays
    x_coords = np.linspace(bounds[0], bounds[2], width)
    y_coords = np.linspace(bounds[3], bounds[1], height)  # Note: reversed for raster coordinates
    
    # Create interpolator
    interpolator = RegularGridInterpolator(
        (y_coords, x_coords),  # Note: y first for raster indexing
        elevation,
        method='linear',
        bounds_error=False,
        fill_value=np.nanmean(elevation)  # Use mean elevation for out-of-bounds points
    )
    
    return {
        'elevation': elevation,
        'bounds': bounds,
        'transform': transform,
        'interpolator': interpolator,
        'x_coords': x_coords,
        'y_coords': y_coords
    }

def get_elevation_at_point(x, y, elevation_data):
    """
    Get elevation at a specific point using the interpolator
    
    Args:
        x, y: Coordinates in the same CRS as the elevation data
        elevation_data: Dictionary returned by load_elevation_raster
    
    Returns:
        float: Elevation at the point
    """
    try:
        # Use interpolator (note: y first for raster indexing)
        elevation = elevation_data['interpolator']((y, x))
        return float(elevation) if not np.isnan(elevation) else 0.0
    except Exception as e:
        print(f"Warning: Could not get elevation at ({x:.2f}, {y:.2f}): {e}")
        return 0.0

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
    """
    Fix missing CRS by reading from .prj file - same as building code
    """
    trees = gpd.read_file(shapefile_path)
    
    if trees.crs is None:
        print("⚠️ No CRS detected. Checking for .prj file...")
        prj_file = shapefile_path.replace('.shp', '.prj')
        try:
            with open(prj_file, 'r') as f:
                prj_content = f.read().strip()
                print(f"Found .prj file content: {prj_content[:100]}...")
                
                # Try to set CRS from .prj file
                trees = trees.set_crs(prj_content)
                print(f"✅ CRS set from .prj file: {trees.crs}")
                
        except FileNotFoundError:
            print(f"❌ No .prj file found at {prj_file}")
            print("🔧 Assuming EPSG:4326 (WGS84). Please verify this is correct.")
            trees = trees.set_crs('EPSG:4326')
        except Exception as e:
            print(f"❌ Error reading .prj file: {e}")
            print("🔧 Assuming EPSG:4326 (WGS84). Please verify this is correct.")
            trees = trees.set_crs('EPSG:4326')
    
    return trees

def create_tree_canopy_with_elevation(point, canopy_radius, trunk_height, canopy_height, trunk_radius,
                                    ground_elevation, canopy_shape='cone', sides=8):
    """
    Create tree geometry with proper triangle winding and ground elevation
    
    Args:
        point: Shapely Point
        canopy_radius: Radius of canopy base
        trunk_height: Height of trunk
        canopy_height: Height of canopy
        trunk_radius: Radius of trunk
        ground_elevation: Ground elevation from DEM
        canopy_shape: 'cone', 'cylinder', or 'sphere'
        sides: Number of sides for approximation
    """
    x, y = point.x, point.y
    triangles = []
    angles = np.linspace(0, 2*np.pi, sides+1)[:-1]
    
    # All Z coordinates are relative to ground elevation
    base_z = ground_elevation
    trunk_top_z = ground_elevation + trunk_height
    canopy_top_z = ground_elevation + trunk_height + canopy_height
    
    # Trunk (if present)
    if trunk_height > 0 and trunk_radius > 0:
        trunk_bottom = [[x + trunk_radius*np.cos(a), y + trunk_radius*np.sin(a), base_z] for a in angles]
        trunk_top = [[x + trunk_radius*np.cos(a), y + trunk_radius*np.sin(a), trunk_top_z] for a in angles]
        trunk_center_bottom = [x, y, base_z]
        trunk_center_top = [x, y, trunk_top_z]
        
        # Create trunk triangles with proper winding
        for i in range(sides):
            next_i = (i + 1) % sides
            # Bottom face (downward normal)
            triangles.append([trunk_center_bottom, trunk_bottom[i], trunk_bottom[next_i]])
            # Top face (upward normal)
            triangles.append([trunk_center_top, trunk_top[next_i], trunk_top[i]])
            # Side faces (outward normals)
            triangles.append([trunk_bottom[i], trunk_top[i], trunk_bottom[next_i]])
            triangles.append([trunk_bottom[next_i], trunk_top[i], trunk_top[next_i]])
    
    # Canopy
    canopy_base_z = trunk_top_z
    
    if canopy_shape == 'cone':
        # Triangular cone - apex at top, circular base
        canopy_bottom = [[x + canopy_radius*np.cos(a), y + canopy_radius*np.sin(a), canopy_base_z] for a in angles]
        apex = [x, y, canopy_top_z]
        canopy_center_bottom = [x, y, canopy_base_z]
        
        for i in range(sides):
            next_i = (i + 1) % sides
            # Bottom face (downward normal)
            triangles.append([canopy_center_bottom, canopy_bottom[i], canopy_bottom[next_i]])
            # Cone surface (outward normals) - each face is a triangle from base edge to apex
            triangles.append([canopy_bottom[i], canopy_bottom[next_i], apex])
    
    elif canopy_shape == 'cylinder':
        canopy_bottom = [[x + canopy_radius*np.cos(a), y + canopy_radius*np.sin(a), canopy_base_z] for a in angles]
        canopy_top = [[x + canopy_radius*np.cos(a), y + canopy_radius*np.sin(a), canopy_top_z] for a in angles]
        canopy_center_bottom = [x, y, canopy_base_z]
        canopy_center_top = [x, y, canopy_top_z]
        
        # Create canopy triangles with proper winding
        for i in range(sides):
            next_i = (i + 1) % sides
            # Bottom face (downward normal)
            triangles.append([canopy_center_bottom, canopy_bottom[i], canopy_bottom[next_i]])
            # Top face (upward normal)
            triangles.append([canopy_center_top, canopy_top[next_i], canopy_top[i]])
            # Side faces (outward normals)
            triangles.append([canopy_bottom[i], canopy_bottom[next_i], canopy_top[i]])
            triangles.append([canopy_bottom[next_i], canopy_top[next_i], canopy_top[i]])
    
    elif canopy_shape == 'sphere':
        # Simple sphere approximation using latitude/longitude divisions
        lat_divs = sides // 2
        lon_divs = sides
        
        for lat_i in range(lat_divs):
            lat1 = np.pi * (-0.5 + lat_i / lat_divs)
            lat2 = np.pi * (-0.5 + (lat_i + 1) / lat_divs)
            
            for lon_i in range(lon_divs):
                lon1 = 2 * np.pi * lon_i / lon_divs
                lon2 = 2 * np.pi * (lon_i + 1) / lon_divs
                
                # Calculate sphere vertices
                r = canopy_radius
                z_offset = (canopy_base_z + canopy_top_z) / 2
                
                p1 = [x + r * np.cos(lat1) * np.cos(lon1), 
                      y + r * np.cos(lat1) * np.sin(lon1), 
                      z_offset + r * np.sin(lat1)]
                p2 = [x + r * np.cos(lat2) * np.cos(lon1), 
                      y + r * np.cos(lat2) * np.sin(lon1), 
                      z_offset + r * np.sin(lat2)]
                p3 = [x + r * np.cos(lat2) * np.cos(lon2), 
                      y + r * np.cos(lat2) * np.sin(lon2), 
                      z_offset + r * np.sin(lat2)]
                p4 = [x + r * np.cos(lat1) * np.cos(lon2), 
                      y + r * np.cos(lat1) * np.sin(lon2), 
                      z_offset + r * np.sin(lat1)]
                
                # Create triangles
                triangles.append([p1, p2, p3])
                triangles.append([p1, p3, p4])
    
    return triangles

def calculate_normal(triangle):
    """Calculate unit normal vector for triangle"""
    p1, p2, p3 = triangle
    v1 = np.array(p2) - np.array(p1)
    v2 = np.array(p3) - np.array(p1)
    normal = np.cross(v1, v2)
    norm = np.linalg.norm(normal)
    return normal / norm if norm > 1e-10 else np.array([0, 0, 1])

def write_stl_binary(filename, triangles):
    """Write triangles to binary STL file"""
    with open(filename, 'wb') as f:
        header = b'Tree STL for OpenFOAM'
        f.write(header + b'\0' * (80 - len(header)))
        
        f.write(struct.pack('<I', len(triangles)))
        
        for triangle in triangles:
            normal = calculate_normal(triangle)
            f.write(struct.pack('<fff', float(normal[0]), float(normal[1]), float(normal[2])))
            
            for vertex in triangle:
                f.write(struct.pack('<fff', float(vertex[0]), float(vertex[1]), float(vertex[2])))
            
            f.write(struct.pack('<H', 0))

def shapefile_points_to_trees_with_elevation(shapefile_path, output_path, 
                                           elevation_data,
                                           offset_x, offset_y,
                                           height_column=None, default_height=5.0,
                                           tree_config=None, use_local_coords=True,
                                           target_crs='EPSG:32616'):
    """
    Convert point shapefile to tree STL using elevation data and hardcoded offset
    
    Args:
        shapefile_path: Path to tree shapefile
        output_path: Output STL file path
        elevation_data: Dictionary from load_elevation_raster()
        offset_x, offset_y: Hardcoded offset values
        height_column: Column name for tree heights (optional)
        default_height: Default tree height if no height column
        tree_config: Tree configuration dictionary
        use_local_coords: Whether to apply offset transformation
        target_crs: Target coordinate reference system
    """
    
    if tree_config is None:
        tree_config = {
            'canopy_shape': 'cone',  # 'cone', 'cylinder', or 'sphere'
            'trunk_height_ratio': 0.3,
            'canopy_radius_ratio': 0.4,
            'trunk_radius': 0.1,
            'detail_level': 12,
            'min_tree_height': 2.0,
            'max_tree_height': 25.0
        }
    
    print(f"Reading shapefile: {shapefile_path}")
    
    # Read and handle CRS same way as building code
    gdf = gpd.read_file(shapefile_path)
    
    if gdf.crs is None:
        gdf = fix_shapefile_crs(shapefile_path)
    
    print(f"Original CRS: {gdf.crs}")
    
    # Handle coordinate system same as building code
    if gdf.crs.to_epsg() == 4326:
        print(f"⚠️ Reprojecting from EPSG:4326 to {target_crs}")
        gdf = gdf.to_crs(target_crs)
    
    # Filter to point geometries only
    point_gdf = gdf[gdf.geometry.geom_type == 'Point'].copy()
    print(f"Found {len(point_gdf)} point features")
    
    if len(point_gdf) == 0:
        raise ValueError("No point geometries found in shapefile")
    
    # Use the provided hardcoded offset
    print(f"Using hardcoded coordinate offset: ({offset_x:.2f}, {offset_y:.2f})")
    print(f"🌲 Tree canopy shape: {tree_config['canopy_shape']}")
    
    triangles = []
    trees_created = 0
    height_stats = []
    elevation_stats = []
    
    for idx, row in point_gdf.iterrows():
        geom = row.geometry
        
        # Get ground elevation at original coordinates (before offset)
        ground_elevation = get_elevation_at_point(geom.x, geom.y, elevation_data)
        elevation_stats.append(ground_elevation)
        
        # Apply coordinate transformation for tree placement
        if use_local_coords:
            adjusted_point = Point(geom.x - offset_x, geom.y - offset_y)
        else:
            adjusted_point = Point(geom.x, geom.y)
        
        # Get tree height
        if height_column and height_column in row and row[height_column] is not None:
            try:
                height = float(row[height_column])
                height = max(tree_config['min_tree_height'],
                           min(tree_config['max_tree_height'], height))
            except Exception:
                height = default_height
        else:
            height = default_height
        
        height_stats.append(height)
        
        # Calculate tree dimensions
        trunk_height = height * tree_config['trunk_height_ratio']
        canopy_height = height - trunk_height
        trunk_radius = tree_config['trunk_radius']
        canopy_radius = height * tree_config['canopy_radius_ratio']
        
        try:
            tree_triangles = create_tree_canopy_with_elevation(
                point=adjusted_point,
                canopy_radius=canopy_radius,
                trunk_height=trunk_height,
                canopy_height=canopy_height,
                trunk_radius=trunk_radius,
                ground_elevation=ground_elevation,  # Use actual ground elevation
                canopy_shape=tree_config['canopy_shape'],
                sides=tree_config['detail_level']
            )
            
            triangles.extend(tree_triangles)
            trees_created += 1
            
            if trees_created % 100 == 0:
                print(f"Processed {trees_created} trees...")
                
        except Exception as e:
            print(f"Error processing tree at index {idx}: {e}")
    
    if not triangles:
        print("❌ No triangles generated!")
        return
    
    # Write STL file
    write_stl_binary(output_path, triangles)
    
    print(f"\n✅ Processing complete!")
    print(f"✅ Created {trees_created} trees")
    print(f"✅ Generated {len(triangles)} triangles")
    print(f"✅ STL file written to: {output_path}")
    
    # Print height statistics
    if height_stats:
        height_array = np.array(height_stats)
        print(f"\nTree height statistics:")
        print(f"  Mean height: {height_array.mean():.2f}m")
        print(f"  Min height: {height_array.min():.2f}m")
        print(f"  Max height: {height_array.max():.2f}m")
        print(f"  Std deviation: {height_array.std():.2f}m")
    
    # Print elevation statistics
    if elevation_stats:
        elevation_array = np.array(elevation_stats)
        print(f"\nGround elevation statistics:")
        print(f"  Mean elevation: {elevation_array.mean():.2f}m")
        print(f"  Min elevation: {elevation_array.min():.2f}m")
        print(f"  Max elevation: {elevation_array.max():.2f}m")
        print(f"  Std deviation: {elevation_array.std():.2f}m")
    
    # Print bounds for OpenFOAM reference (same format as building code)
    if triangles:
        all_points = np.array([point for triangle in triangles for point in triangle])
        bounds = {
            'x_min': all_points[:, 0].min(),
            'x_max': all_points[:, 0].max(),
            'y_min': all_points[:, 1].min(), 
            'y_max': all_points[:, 1].max(),
            'z_min': all_points[:, 2].min(),
            'z_max': all_points[:, 2].max()
        }
        
        print(f"\nMesh bounds for OpenFOAM blockMeshDict:")
        print(f"X: [{bounds['x_min']:.2f}, {bounds['x_max']:.2f}]")
        print(f"Y: [{bounds['y_min']:.2f}, {bounds['y_max']:.2f}]") 
        print(f"Z: [{bounds['z_min']:.2f}, {bounds['z_max']:.2f}]")
    
    return {
        'trees_created': trees_created,
        'triangles_generated': len(triangles),
        'bounds': bounds,
        'coordinate_system': str(point_gdf.crs),
        'offset': (offset_x, offset_y),
        'elevation_stats': {
            'mean': elevation_array.mean(),
            'min': elevation_array.min(),
            'max': elevation_array.max(),
            'std': elevation_array.std()
        }
    }

def validate_tree_stl(stl_file):
    """Basic validation of generated STL file"""
    try:
        with open(stl_file, 'rb') as f:
            header = f.read(80)
            triangle_count = struct.unpack('<I', f.read(4))[0]
            
            print(f"\nSTL Validation:")
            print(f"Header: {header[:25].decode('ascii', errors='ignore')}")
            print(f"Triangle count: {triangle_count}")
            
            # Check file size
            expected_size = 80 + 4 + (triangle_count * 50)
            actual_size = f.seek(0, 2)
            
            if actual_size == expected_size:
                print("✅ File size matches expected size")
            else:
                print(f"⚠️ Size mismatch: expected {expected_size}, got {actual_size}")
                
    except Exception as e:
        print(f"❌ STL validation failed: {e}")

# Main execution
if __name__ == "__main__":
    
    # Define paths
    tree_shp = "/Users/omokayj/vsCode.local/urbanWindFlow/Tools/input/treesshapefileKilbourn.shp"
    building_shp = "/Users/omokayj/vsCode.local/urbanWindFlow/Tools/input/kilbourntoClybourn.shp"
    output_path = "/Users/omokayj/vsCode.local/urbanWindFlow/Tools/output/wRaster/treesKilbourn1028_cone.stl"
    elevation_tif = "/Users/omokayj/vsCode.local/urbanWindFlow/Tools/input/demdataforground/demdataforground.tif"

    # Hardcoded offset values (replace with your actual values)
    HARDCODED_OFFSET_X = 424265.04  # Replace with your actual offset
    HARDCODED_OFFSET_Y = 4765565.05  # Replace with your actual offset
    
    print(f"🏔️ Using hardcoded offset: ({HARDCODED_OFFSET_X:.2f}, {HARDCODED_OFFSET_Y:.2f})")
    
    # Step 1: Load elevation data
    print("🌍 Loading elevation raster...")
    elevation_data = load_elevation_raster(
        tif_path=elevation_tif,
        target_crs='EPSG:32616',
        resample_factor=1.0
    )
    
    # Tree configuration - EASILY SWITCH CANOPY SHAPE HERE!
    custom_tree_config = {
        'canopy_shape': 'cone',        # OPTIONS: 'cone', 'cylinder', 'sphere'
        'trunk_height_ratio': 0.3,     # Trunk is 30% of total height
        'canopy_radius_ratio': 0.4,    # Canopy radius relative to height
        'trunk_radius': 0.2,           # Trunk radius in meters
        'detail_level': 12,            # Number of sides (higher = smoother)
        'min_tree_height': 2.0,
        'max_tree_height': 30.0
    }
    
    # Step 2: Generate trees using elevation data and hardcoded offset
    print("\n🌳 Generating tree STL with elevation data...")
    result = shapefile_points_to_trees_with_elevation(
        shapefile_path=tree_shp,
        output_path=output_path,
        elevation_data=elevation_data,
        offset_x=HARDCODED_OFFSET_X,
        offset_y=HARDCODED_OFFSET_Y,
        height_column=None,            # Or specify height column name
        default_height=10.0,
        tree_config=custom_tree_config,
        use_local_coords=True,         # Apply offset transformation
        target_crs='EPSG:32616'        # Same as building code
    )
    
    # Step 3: Validate the generated STL
    validate_tree_stl(output_path)
    
    print("\n📊 Final Summary:")
    for k, v in result.items():
        print(f"  {k}: {v}")
    
    print(f"\n✅ Trees generated with elevation data using hardcoded offset: ({HARDCODED_OFFSET_X:.2f}, {HARDCODED_OFFSET_Y:.2f})")
    print("🌲 Trees are now positioned at their correct ground elevations!")