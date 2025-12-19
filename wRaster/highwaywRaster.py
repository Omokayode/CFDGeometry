import geopandas as gpd
import numpy as np
import struct
from shapely.geometry import Point, LineString, box
from shapely.ops import transform
import warnings
import pandas as pd
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

def create_highway_geometry_with_elevation(line_coords, elevations, width, height, padding=0.5, 
                                         elevation_offset=0.1, smooth_elevation=True):
    """
    Create 3D highway geometry from 2D line coordinates with elevation data
    
    Args:
        line_coords: List of (x, y) coordinates defining the centerline
        elevations: List of elevation values corresponding to line_coords
        width: Width of the highway
        height: Height/thickness of the highway above ground
        padding: Additional padding around the highway
        elevation_offset: Additional height above ground elevation
        smooth_elevation: Whether to smooth elevation changes
    
    Returns:
        List of triangles representing the highway surface
    """
    triangles = []
    total_width = width + (2 * padding)
    
    if len(line_coords) < 2:
        return triangles
    
    # Smooth elevations if requested
    if smooth_elevation and len(elevations) > 2:
        # Simple moving average smoothing
        window_size = min(3, len(elevations))
        smoothed_elevations = []
        for i in range(len(elevations)):
            start_idx = max(0, i - window_size // 2)
            end_idx = min(len(elevations), i + window_size // 2 + 1)
            smoothed_elevations.append(np.mean(elevations[start_idx:end_idx]))
        elevations = smoothed_elevations
    
    # Create offset lines for both sides of the highway
    left_coords = []
    right_coords = []
    
    for i in range(len(line_coords)):
        x, y = line_coords[i]
        ground_elevation = elevations[i]
        highway_top_z = ground_elevation + elevation_offset + height
        highway_bottom_z = ground_elevation + elevation_offset
        
        # Calculate perpendicular direction
        if i == 0:
            # First point - use direction to next point
            dx = line_coords[i+1][0] - x
            dy = line_coords[i+1][1] - y
        elif i == len(line_coords) - 1:
            # Last point - use direction from previous point
            dx = x - line_coords[i-1][0]
            dy = y - line_coords[i-1][1]
        else:
            # Middle points - use average direction
            dx1 = x - line_coords[i-1][0]
            dy1 = y - line_coords[i-1][1]
            dx2 = line_coords[i+1][0] - x
            dy2 = line_coords[i+1][1] - y
            dx = (dx1 + dx2) / 2
            dy = (dy1 + dy2) / 2
        
        # Normalize and create perpendicular
        length = np.sqrt(dx**2 + dy**2)
        if length > 0:
            dx /= length
            dy /= length
            
        # Perpendicular vector (rotate 90 degrees)
        perp_x = -dy
        perp_y = dx
        
        # Create left and right points
        half_width = total_width / 2
        left_x = x + perp_x * half_width
        left_y = y + perp_y * half_width
        right_x = x - perp_x * half_width
        right_y = y - perp_y * half_width
        
        left_coords.append({
            'top': [left_x, left_y, highway_top_z],
            'bottom': [left_x, left_y, highway_bottom_z]
        })
        right_coords.append({
            'top': [right_x, right_y, highway_top_z],
            'bottom': [right_x, right_y, highway_bottom_z]
        })
    
    # Create top surface triangles
    for i in range(len(line_coords) - 1):
        # Two triangles per segment
        p1 = left_coords[i]['top']
        p2 = right_coords[i]['top']
        p3 = left_coords[i+1]['top']
        p4 = right_coords[i+1]['top']
        
        # Triangle 1 (counter-clockwise for upward normal)
        triangles.append([p1, p3, p2])
        # Triangle 2
        triangles.append([p2, p3, p4])
    
    # Create bottom surface triangles
    for i in range(len(line_coords) - 1):
        p1 = left_coords[i]['bottom']
        p2 = right_coords[i]['bottom']
        p3 = left_coords[i+1]['bottom']
        p4 = right_coords[i+1]['bottom']
        
        # Triangle 1 (clockwise for downward normal)
        triangles.append([p1, p2, p3])
        # Triangle 2
        triangles.append([p2, p4, p3])
    
    # Create side walls
    for i in range(len(line_coords) - 1):
        # Left wall
        tl1 = left_coords[i]['top']
        tl2 = left_coords[i+1]['top']
        bl1 = left_coords[i]['bottom']
        bl2 = left_coords[i+1]['bottom']
        
        # Left wall triangles (outward normal)
        triangles.append([bl1, tl1, bl2])
        triangles.append([bl2, tl1, tl2])
        
        # Right wall
        tr1 = right_coords[i]['top']
        tr2 = right_coords[i+1]['top']
        br1 = right_coords[i]['bottom']
        br2 = right_coords[i+1]['bottom']
        
        # Right wall triangles (outward normal)
        triangles.append([br1, br2, tr1])
        triangles.append([br2, tr2, tr1])
    
    # Create end caps
    if len(line_coords) >= 2:
        # Start cap
        start_left_top = left_coords[0]['top']
        start_right_top = right_coords[0]['top']
        start_left_bottom = left_coords[0]['bottom']
        start_right_bottom = right_coords[0]['bottom']
        
        triangles.append([start_left_bottom, start_left_top, start_right_bottom])
        triangles.append([start_right_bottom, start_left_top, start_right_top])
        
        # End cap
        end_left_top = left_coords[-1]['top']
        end_right_top = right_coords[-1]['top']
        end_left_bottom = left_coords[-1]['bottom']
        end_right_bottom = right_coords[-1]['bottom']
        
        triangles.append([end_left_bottom, end_right_bottom, end_left_top])
        triangles.append([end_right_bottom, end_right_top, end_left_top])
    
    return triangles

def visualize_elevation_profile(line_coords, elevations, title="Highway Elevation Profile"):
    """
    Create a simple elevation profile plot
    
    Args:
        line_coords: List of (x, y) coordinates
        elevations: List of elevation values
        title: Plot title
    """
    if len(line_coords) < 2:
        print("Not enough points for elevation profile")
        return
    
    # Calculate cumulative distance along the line
    distances = [0]
    for i in range(1, len(line_coords)):
        dx = line_coords[i][0] - line_coords[i-1][0]
        dy = line_coords[i][1] - line_coords[i-1][1]
        dist = np.sqrt(dx**2 + dy**2)
        distances.append(distances[-1] + dist)
    
    plt.figure(figsize=(12, 6))
    plt.plot(distances, elevations, 'b-', linewidth=2, label='Ground Elevation')
    plt.xlabel('Distance along highway (m)')
    plt.ylabel('Elevation (m)')
    plt.title(title)
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # Add statistics
    plt.text(0.02, 0.98, 
             f'Min: {np.min(elevations):.1f}m\n'
             f'Max: {np.max(elevations):.1f}m\n'
             f'Range: {np.max(elevations) - np.min(elevations):.1f}m',
             transform=plt.gca().transAxes,
             verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    plt.show()

def fix_shapefile_crs(shapefile_path):
    """Fix missing CRS by reading from .prj file"""
    gdf = gpd.read_file(shapefile_path)
    
    if gdf.crs is None:
        print("⚠️ No CRS detected. Checking for .prj file...")
        prj_file = shapefile_path.replace('.shp', '.prj')
        try:
            with open(prj_file, 'r') as f:
                prj_content = f.read().strip()
                print(f"Found .prj file content: {prj_content[:100]}...")
                
                gdf = gdf.set_crs(prj_content)
                print(f"✅ CRS set from .prj file: {gdf.crs}")
                
        except FileNotFoundError:
            print(f"❌ No .prj file found at {prj_file}")
            print("🔧 Assuming EPSG:4326 (WGS84). Please verify this is correct.")
            gdf = gdf.set_crs('EPSG:4326')
        except Exception as e:
            print(f"❌ Error reading .prj file: {e}")
            gdf = gdf.set_crs('EPSG:4326')
    
    return gdf

def get_highway_config():
    """Define highway types and their characteristics"""
    return {
        'highway': {'width': 12.0, 'height': 0.3, 'padding': 1.0},
        'primary': {'width': 10.0, 'height': 0.25, 'padding': 0.8},
        'secondary': {'width': 8.0, 'height': 0.2, 'padding': 0.6},
        'tertiary': {'width': 6.0, 'height': 0.15, 'padding': 0.5},
        'residential': {'width': 5.0, 'height': 0.1, 'padding': 0.3},
        'service': {'width': 3.0, 'height': 0.08, 'padding': 0.2},
        'path': {'width': 2.0, 'height': 0.05, 'padding': 0.1},
        'trunk': {'width': 14.0, 'height': 0.35, 'padding': 1.2},
        'motorway': {'width': 16.0, 'height': 0.4, 'padding': 1.5},
        'default': {'width': 4.0, 'height': 0.1, 'padding': 0.3}
    }

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
        header = b'Highway STL with Elevation for OpenFOAM'
        f.write(header + b'\0' * (80 - len(header)))
        
        f.write(struct.pack('<I', len(triangles)))
        
        for triangle in triangles:
            normal = calculate_normal(triangle)
            f.write(struct.pack('<fff', float(normal[0]), float(normal[1]), float(normal[2])))
            
            for vertex in triangle:
                f.write(struct.pack('<fff', float(vertex[0]), float(vertex[1]), float(vertex[2])))
            
            f.write(struct.pack('<H', 0))

def shapefile_highways_to_stl_with_elevation(shapefile_path, tif_path, output_path,
                                           offset_x, offset_y,
                                           highway_type_column=None,
                                           elevation_offset=0.1,
                                           smooth_elevation=True,
                                           show_elevation_profile=False,
                                           target_crs='EPSG:32616'):
    """
    Convert highway shapefile to STL using elevation data from TIF file
    
    Args:
        shapefile_path: Path to highway shapefile
        tif_path: Path to elevation TIF file
        output_path: Output STL file path
        offset_x, offset_y: Coordinate offset for alignment
        highway_type_column: Column name for highway type
        elevation_offset: Height above ground elevation (meters)
        smooth_elevation: Whether to smooth elevation changes
        show_elevation_profile: Whether to display elevation profiles
        target_crs: Target coordinate reference system
    """
    
    print(f"🛣️ Converting highways with elevation data")
    print(f"Highway shapefile: {shapefile_path}")
    print(f"Elevation TIF: {tif_path}")
    
    # Load elevation data
    elevation_data = load_elevation_raster(tif_path, target_crs)
    
    # Read highway shapefile
    gdf = gpd.read_file(shapefile_path)
    if gdf.crs is None:
        gdf = fix_shapefile_crs(shapefile_path)
    
    # Reproject if necessary
    if gdf.crs.to_epsg() != int(target_crs.split(':')[1]):
        print(f"🔄 Reprojecting highways from {gdf.crs} to {target_crs}")
        gdf = gdf.to_crs(target_crs)
    
    # Filter to line geometries
    line_gdf = gdf[gdf.geometry.geom_type.isin(['LineString', 'MultiLineString'])].copy()
    print(f"Found {len(line_gdf)} highway features")
    
    if len(line_gdf) == 0:
        raise ValueError("No line geometries found in shapefile")
    
    highway_config = get_highway_config()
    triangles = []
    highways_created = 0
    highway_stats = {'types': {}, 'total_length': 0, 'elevation_range': {'min': float('inf'), 'max': float('-inf')}}
    
    for idx, row in line_gdf.iterrows():
        geom = row.geometry
        
        # Handle MultiLineString
        if geom.geom_type == 'MultiLineString':
            lines = list(geom.geoms)
        else:
            lines = [geom]
        
        # Determine highway type
        highway_type = 'default'
        if highway_type_column and highway_type_column in row:
            specified_type = str(row[highway_type_column]).lower()
            if specified_type in highway_config:
                highway_type = specified_type
            else:
                for config_type in highway_config.keys():
                    if config_type in specified_type:
                        highway_type = config_type
                        break
        
        params = highway_config[highway_type]
        
        # Track statistics
        if highway_type not in highway_stats['types']:
            highway_stats['types'][highway_type] = 0
        highway_stats['types'][highway_type] += 1
        
        for line in lines:
            try:
                # Get line coordinates
                coords = list(line.coords)
                
                # Apply coordinate transformation
                adjusted_coords = [(x - offset_x, y - offset_y) for x, y in coords]
                original_coords = [(x, y) for x, y in coords]  # Keep original for elevation lookup
                
                # Get elevation values at highway points
                elevations = get_elevation_at_points(original_coords, elevation_data)
                
                # Update elevation statistics
                valid_elevations = [e for e in elevations if not np.isnan(e)]
                if valid_elevations:
                    highway_stats['elevation_range']['min'] = min(highway_stats['elevation_range']['min'], min(valid_elevations))
                    highway_stats['elevation_range']['max'] = max(highway_stats['elevation_range']['max'], max(valid_elevations))
                
                # Show elevation profile if requested
                if show_elevation_profile and len(coords) > 5:
                    visualize_elevation_profile(coords, elevations, f"Highway {highways_created + 1} - {highway_type}")
                
                # Calculate length for statistics
                highway_stats['total_length'] += line.length
                
                # Create highway geometry with elevation
                highway_triangles = create_highway_geometry_with_elevation(
                    line_coords=adjusted_coords,
                    elevations=elevations,
                    width=params['width'],
                    height=params['height'],
                    padding=params['padding'],
                    elevation_offset=elevation_offset,
                    smooth_elevation=smooth_elevation
                )
                
                triangles.extend(highway_triangles)
                highways_created += 1
                
                if highways_created % 25 == 0:
                    print(f"Processed {highways_created} highway segments...")
                    
            except Exception as e:
                print(f"Error processing highway at index {idx}: {e}")
    
    if not triangles:
        print("❌ No triangles generated!")
        return
    
    # Write STL file
    write_stl_binary(output_path, triangles)
    
    print(f"\n✅ Highway processing complete!")
    print(f"✅ Created {highways_created} highway segments")
    print(f"✅ Generated {len(triangles)} triangles")
    print(f"✅ STL file written to: {output_path}")
    
    # Print statistics
    print(f"\nHighway Statistics:")
    for htype, count in highway_stats['types'].items():
        print(f"  {htype}: {count} segments")
    print(f"Total length: {highway_stats['total_length']/1000:.2f} km")
    
    if highway_stats['elevation_range']['min'] != float('inf'):
        elev_min = highway_stats['elevation_range']['min']
        elev_max = highway_stats['elevation_range']['max']
        print(f"Elevation range: {elev_min:.1f} to {elev_max:.1f} meters ({elev_max - elev_min:.1f}m range)")
    
    # Print bounds
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
        
        print(f"\nHighway mesh bounds:")
        print(f"X: [{bounds['x_min']:.2f}, {bounds['x_max']:.2f}]")
        print(f"Y: [{bounds['y_min']:.2f}, {bounds['y_max']:.2f}]") 
        print(f"Z: [{bounds['z_min']:.2f}, {bounds['z_max']:.2f}]")
    
    return {
        'highways_created': highways_created,
        'triangles_generated': len(triangles),
        'bounds': bounds,
        'coordinate_system': str(line_gdf.crs),
        'offset_used': (offset_x, offset_y),
        'highway_stats': highway_stats,
        'elevation_data_bounds': elevation_data['bounds']
    }

# Example usage
if __name__ == "__main__":
    
    # Define paths
    highway_shp = "windAroundBuildings/Tools/input/highwayKilbourn.shp"
    # elevation_tif = "windAroundBuildings/Tools/input/rasterKilbourn.tif" 
    elevation_tif = "windAroundBuildings/Tools/input/demdataforground/demdataforground.tif"
    highway_output = "windAroundBuildings/Tools/output/wRaster/highwayKilbourn.stl"
    
    # Offset values (use your hardcoded values or calculate from other shapefiles)
    HARDCODED_OFFSET = (424265.04, 4765565.05)  
    
    # Check if files exist
    if not os.path.exists(highway_shp):
        print(f"❌ Highway shapefile not found: {highway_shp}")
        exit(1)
    
    if not os.path.exists(elevation_tif):
        print(f"❌ Elevation TIF file not found: {elevation_tif}")
        print("Please update the elevation_tif path to your actual TIF file.")
        exit(1)
    
    # Generate highways with elevation
    result = shapefile_highways_to_stl_with_elevation(
        shapefile_path=highway_shp,
        tif_path=elevation_tif,
        output_path=highway_output,
        offset_x=HARDCODED_OFFSET[0],
        offset_y=HARDCODED_OFFSET[1],
        highway_type_column='highway',  # Adjust as needed
        elevation_offset=0.1,          # Height above ground (meters)
        smooth_elevation=True,         # Smooth elevation changes
        show_elevation_profile=False,  # Set to True to see elevation plots
        target_crs='EPSG:32616'
    )
    
    print(f"\n📊 Final Summary:")
    for k, v in result.items():
        print(f"  {k}: {v}")