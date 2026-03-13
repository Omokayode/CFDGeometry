import geopandas as gpd
import numpy as np
import struct
from shapely.geometry import Point, LineString, box
from shapely.ops import transform
import warnings
import pandas as pd
import os
warnings.filterwarnings('ignore')

def fix_shapefile_crs(shapefile_path):
    """
    Fix missing CRS by reading from .prj file - same as building code
    """
    gdf = gpd.read_file(shapefile_path)
    
    if gdf.crs is None:
        print("⚠️ No CRS detected. Checking for .prj file...")
        prj_file = shapefile_path.replace('.shp', '.prj')
        try:
            with open(prj_file, 'r') as f:
                prj_content = f.read().strip()
                print(f"Found .prj file content: {prj_content[:100]}...")
                
                # Try to set CRS from .prj file
                gdf = gdf.set_crs(prj_content)
                print(f"✅ CRS set from .prj file: {gdf.crs}")
                
        except FileNotFoundError:
            print(f"❌ No .prj file found at {prj_file}")
            print("🔧 Assuming EPSG:4326 (WGS84). Please verify this is correct.")
            gdf = gdf.set_crs('EPSG:4326')
        except Exception as e:
            print(f"❌ Error reading .prj file: {e}")
            print("🔧 Assuming EPSG:4326 (WGS84). Please verify this is correct.")
            gdf = gdf.set_crs('EPSG:4326')
    
    return gdf

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

def get_offset_values(shapefile_paths=None, hardcoded_offset=None, target_epsg=32616):
    """
    Get offset values either from shapefiles or use hardcoded values.
    
    Args:
        shapefile_paths (list, optional): List of paths to shapefiles for calculating offset
        hardcoded_offset (tuple, optional): Tuple of (offset_x, offset_y) to use instead
        target_epsg (int): EPSG code for reprojection if using shapefiles
    
    Returns:
        (offset_x, offset_y): Tuple of offset coordinates
    """
    if hardcoded_offset is not None:
        offset_x, offset_y = hardcoded_offset
        print(f"🔧 Using hardcoded offset: ({offset_x:.2f}, {offset_y:.2f})")
        return offset_x, offset_y
    
    elif shapefile_paths and len(shapefile_paths) > 0:
        print("🔄 Calculating offset from shapefiles...")
        return get_combined_offset(shapefile_paths, target_epsg)
    
    else:
        print("⚠️ No offset method specified. Using default offset (0, 0)")
        return 0.0, 0.0

def create_highway_geometry(line_coords, width, height, padding=0.5):
    """
    Create 3D highway geometry from 2D line coordinates
    
    Args:
        line_coords: List of (x, y) coordinates defining the centerline
        width: Width of the highway
        height: Height/thickness of the highway
        padding: Additional padding around the highway
    
    Returns:
        List of triangles representing the highway surface
    """
    triangles = []
    total_width = width + (2 * padding)
    
    if len(line_coords) < 2:
        return triangles
    
    # Create offset lines for both sides of the highway
    left_coords = []
    right_coords = []
    
    for i in range(len(line_coords)):
        x, y = line_coords[i]
        
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
        
        left_coords.append([left_x, left_y, height])
        right_coords.append([right_x, right_y, height])
    
    # Create top surface triangles
    for i in range(len(line_coords) - 1):
        # Two triangles per segment
        p1 = left_coords[i]
        p2 = right_coords[i]
        p3 = left_coords[i+1]
        p4 = right_coords[i+1]
        
        # Triangle 1 (counter-clockwise for upward normal)
        triangles.append([p1, p3, p2])
        # Triangle 2
        triangles.append([p2, p3, p4])
    
    # Create bottom surface (at z=0)
    bottom_left = [[coord[0], coord[1], 0] for coord in left_coords]
    bottom_right = [[coord[0], coord[1], 0] for coord in right_coords]
    
    for i in range(len(line_coords) - 1):
        p1 = bottom_left[i]
        p2 = bottom_right[i]
        p3 = bottom_left[i+1]
        p4 = bottom_right[i+1]
        
        # Triangle 1 (clockwise for downward normal)
        triangles.append([p1, p2, p3])
        # Triangle 2
        triangles.append([p2, p4, p3])
    
    # Create side walls
    for i in range(len(line_coords) - 1):
        # Left wall
        tl1 = left_coords[i]
        tl2 = left_coords[i+1]
        bl1 = bottom_left[i]
        bl2 = bottom_left[i+1]
        
        # Left wall triangles (outward normal)
        triangles.append([bl1, tl1, bl2])
        triangles.append([bl2, tl1, tl2])
        
        # Right wall
        tr1 = right_coords[i]
        tr2 = right_coords[i+1]
        br1 = bottom_right[i]
        br2 = bottom_right[i+1]
        
        # Right wall triangles (outward normal)
        triangles.append([br1, br2, tr1])
        triangles.append([br2, tr2, tr1])
    
    # Create end caps
    if len(line_coords) >= 2:
        # Start cap
        start_left_top = left_coords[0]
        start_right_top = right_coords[0]
        start_left_bottom = bottom_left[0]
        start_right_bottom = bottom_right[0]
        
        triangles.append([start_left_bottom, start_left_top, start_right_bottom])
        triangles.append([start_right_bottom, start_left_top, start_right_top])
        
        # End cap
        end_left_top = left_coords[-1]
        end_right_top = right_coords[-1]
        end_left_bottom = bottom_left[-1]
        end_right_bottom = bottom_right[-1]
        
        triangles.append([end_left_bottom, end_right_bottom, end_left_top])
        triangles.append([end_right_bottom, end_right_top, end_left_top])
    
    return triangles

def get_highway_config():
    """
    Define highway types and their characteristics
    """
    return {
        'highway': {'width': 12.0, 'height': 0.3, 'padding': 1.0},      # Major highway
        'primary': {'width': 10.0, 'height': 0.25, 'padding': 0.8},    # Primary road
        'secondary': {'width': 8.0, 'height': 0.2, 'padding': 0.6},    # Secondary road
        'tertiary': {'width': 6.0, 'height': 0.15, 'padding': 0.5},    # Tertiary road
        'residential': {'width': 5.0, 'height': 0.1, 'padding': 0.3},  # Residential street
        'service': {'width': 3.0, 'height': 0.08, 'padding': 0.2},     # Service road
        'path': {'width': 2.0, 'height': 0.05, 'padding': 0.1},        # Path/trail
        'trunk': {'width': 14.0, 'height': 0.35, 'padding': 1.2},      # Trunk road
        'motorway': {'width': 16.0, 'height': 0.4, 'padding': 1.5},    # Motorway
        'default': {'width': 4.0, 'height': 0.1, 'padding': 0.3}       # Default for unknown types
    }

def clip_to_reference_bounds(highway_gdf, reference_shapefiles, buffer_meters=100):
    """
    Clip highways to the bounds of reference shapefiles (trees/buildings) plus buffer
    
    Args:
        highway_gdf: Highway GeoDataFrame
        reference_shapefiles: List of reference shapefile paths
        buffer_meters: Buffer around reference bounds
    
    Returns:
        Clipped highway GeoDataFrame
    """
    # Get combined bounds from reference shapefiles
    all_bounds = []
    
    for path in reference_shapefiles:
        if os.path.exists(path):
            ref_gdf = gpd.read_file(path)
            if ref_gdf.crs is None:
                ref_gdf = fix_shapefile_crs(path)
            if ref_gdf.crs.to_epsg() != highway_gdf.crs.to_epsg():
                ref_gdf = ref_gdf.to_crs(highway_gdf.crs)
            all_bounds.append(ref_gdf.total_bounds)
    
    if not all_bounds:
        print("⚠️ No reference shapefiles found, using highway bounds")
        return highway_gdf
    
    # Find overall bounds
    all_bounds = np.array(all_bounds)
    minx = all_bounds[:, 0].min() - buffer_meters
    miny = all_bounds[:, 1].min() - buffer_meters
    maxx = all_bounds[:, 2].max() + buffer_meters
    maxy = all_bounds[:, 3].max() + buffer_meters
    
    print(f"Clipping highways to reference bounds + {buffer_meters}m buffer:")
    print(f"  X: [{minx:.2f}, {maxx:.2f}]")
    print(f"  Y: [{miny:.2f}, {maxy:.2f}]")
    
    # Create clipping polygon
    clip_poly = box(minx, miny, maxx, maxy)
    
    # Clip the geometries
    clipped_gdf = highway_gdf.copy()
    clipped_gdf['geometry'] = clipped_gdf['geometry'].intersection(clip_poly)
    
    # Remove empty geometries
    clipped_gdf = clipped_gdf[~clipped_gdf['geometry'].is_empty]
    
    print(f"Highways after clipping: {len(clipped_gdf)} features (was {len(highway_gdf)})")
    return clipped_gdf

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
        header = b'Highway STL for OpenFOAM'
        f.write(header + b'\0' * (80 - len(header)))
        
        f.write(struct.pack('<I', len(triangles)))
        
        for triangle in triangles:
            normal = calculate_normal(triangle)
            f.write(struct.pack('<fff', float(normal[0]), float(normal[1]), float(normal[2])))
            
            for vertex in triangle:
                f.write(struct.pack('<fff', float(vertex[0]), float(vertex[1]), float(vertex[2])))
            
            f.write(struct.pack('<H', 0))

def shapefile_highways_to_stl_aligned(shapefile_path, output_path,
                                    offset_x, offset_y,
                                    highway_type_column=None,
                                    reference_shapefiles=None,
                                    use_local_coords=True,
                                    target_crs='EPSG:32616'):
    """
    Convert highway shapefile to STL using provided offset for alignment
    
    Args:
        shapefile_path: Path to highway shapefile
        output_path: Output STL file path
        offset_x, offset_y: Offset coordinates for alignment
        highway_type_column: Column name for highway type classification
        reference_shapefiles: List of reference shapefile paths for clipping bounds
        use_local_coords: Whether to apply offset transformation
        target_crs: Target coordinate reference system
    """
    
    print(f"Reading highway shapefile: {shapefile_path}")
    
    # Read and handle CRS
    gdf = gpd.read_file(shapefile_path)
    
    if gdf.crs is None:
        gdf = fix_shapefile_crs(shapefile_path)
    
    print(f"Original CRS: {gdf.crs}")
    print(f"Original features: {len(gdf)}")
    
    # Handle coordinate system
    if gdf.crs.to_epsg() == 4326:
        print(f"⚠️ Reprojecting from EPSG:4326 to {target_crs}")
        gdf = gdf.to_crs(target_crs)
    elif gdf.crs.to_epsg() != int(target_crs.split(':')[1]):
        print(f"⚠️ Reprojecting from {gdf.crs} to {target_crs}")
        gdf = gdf.to_crs(target_crs)
    
    # Filter to LineString geometries only
    line_gdf = gdf[gdf.geometry.geom_type.isin(['LineString', 'MultiLineString'])].copy()
    print(f"Found {len(line_gdf)} line features")
    
    if len(line_gdf) == 0:
        raise ValueError("No line geometries found in shapefile")
    
    # Clip to reference bounds if provided
    if reference_shapefiles:
        line_gdf = clip_to_reference_bounds(line_gdf, reference_shapefiles, buffer_meters=200)
    
    # Use the provided offset
    print(f"Using coordinate offset: ({offset_x:.2f}, {offset_y:.2f})")
    
    # Get highway configuration
    highway_config = get_highway_config()
    
    triangles = []
    highways_created = 0
    highway_stats = {'types': {}, 'total_length': 0}
    
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
                # Try to match partial strings
                for config_type in highway_config.keys():
                    if config_type in specified_type:
                        highway_type = config_type
                        break
        
        # Get highway parameters
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
                if use_local_coords:
                    adjusted_coords = [(x - offset_x, y - offset_y) for x, y in coords]
                else:
                    adjusted_coords = coords
                
                # Calculate length for statistics
                line_length = line.length
                highway_stats['total_length'] += line_length
                
                # Create highway geometry
                highway_triangles = create_highway_geometry(
                    line_coords=adjusted_coords,
                    width=params['width'],
                    height=params['height'],
                    padding=params['padding']
                )
                
                triangles.extend(highway_triangles)
                highways_created += 1
                
                if highways_created % 50 == 0:
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
    
    # Print highway statistics
    print(f"\nHighway type statistics:")
    for htype, count in highway_stats['types'].items():
        print(f"  {htype}: {count} segments")
    print(f"Total length: {highway_stats['total_length']/1000:.2f} km")
    
    # Print bounds for OpenFOAM reference
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
        
        print(f"\nHighway mesh bounds for OpenFOAM blockMeshDict:")
        print(f"X: [{bounds['x_min']:.2f}, {bounds['x_max']:.2f}]")
        print(f"Y: [{bounds['y_min']:.2f}, {bounds['y_max']:.2f}]") 
        print(f"Z: [{bounds['z_min']:.2f}, {bounds['z_max']:.2f}]")
    
    return {
        'highways_created': highways_created,
        'triangles_generated': len(triangles),
        'bounds': bounds,
        'coordinate_system': str(line_gdf.crs),
        'offset_used': (offset_x, offset_y),
        'highway_stats': highway_stats
    }

def validate_stl(stl_file):
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

# Main execution - Highway STL with hardcoded offset support
if __name__ == "__main__":
    
    # Define paths
    tree_shp = "/mnt/nas/vsCode/resources/urbanWindFlow/Tools/input/treesshapefileKilbourn.shp"
    building_shp = "/mnt/nas/vsCode/resources/urbanWindFlow/Tools/input/kilbourntoClybourn.shp"
    highway_shp = "/mnt/nas/vsCode/resources/urbanWindFlow/Tools/input/highwayKilbourn.shp"  
    
    highway_output = "/mnt/nas/vsCode/resources/urbanWindFlow/Tools/output/highwayKilbuorn.stl"
    
    # =============================================================================
    # OFFSET CONFIGURATION - Choose one of the following methods:
    # =============================================================================
    
    # Method 1: Use hardcoded offset values (RECOMMENDED FOR CONSISTENCY)
    # Uncomment the line below and set your specific offset values:
    HARDCODED_OFFSET = (424265.04, 4765565.05)  # Replace with your actual values
    
    # Method 2: Calculate offset from shapefiles (original behavior)
    # Comment out HARDCODED_OFFSET above and uncomment the line below:
    # HARDCODED_OFFSET = None
    
    # =============================================================================
    
    # Step 1: Get offset values (either hardcoded or calculated)
    print("🔄 Determining offset values...")
    
    # Prepare shapefile list for offset calculation (only used if HARDCODED_OFFSET is None)
    shapefiles = []
    if os.path.exists(tree_shp):
        shapefiles.append(tree_shp)
    if os.path.exists(building_shp):
        shapefiles.append(building_shp)
    if os.path.exists(highway_shp):
        shapefiles.append(highway_shp)
    
    # Get offset values using the new function
    offset_x, offset_y = get_offset_values(
        shapefile_paths=shapefiles if HARDCODED_OFFSET is None else None,
        hardcoded_offset=HARDCODED_OFFSET,
        target_epsg=32616
    )
    
    # Step 2: Generate highways with determined offset
    if os.path.exists(highway_shp):
        print(f"\n🛣️ Generating highway STL with offset: ({offset_x:.2f}, {offset_y:.2f})")
        
        # Reference shapefiles for clipping bounds
        reference_files = []
        if os.path.exists(tree_shp):
            reference_files.append(tree_shp)
        if os.path.exists(building_shp):
            reference_files.append(building_shp)
        
        highway_result = shapefile_highways_to_stl_aligned(
            shapefile_path=highway_shp,
            output_path=highway_output,
            offset_x=offset_x,
            offset_y=offset_y,
            highway_type_column='highway',    # Adjust column name as needed
            reference_shapefiles=reference_files,
            use_local_coords=True,
            target_crs='EPSG:32616'
        )
        
        # Step 3: Validate the generated STL file
        validate_stl(highway_output)
        
        print("\n📊 Highway STL Summary:")
        for k, v in highway_result.items():
            print(f"  {k}: {v}")
        
        offset_method = "hardcoded" if HARDCODED_OFFSET is not None else "calculated"
        print(f"\n✅ Highway STL generated using {offset_method} offset: ({offset_x:.2f}, {offset_y:.2f})")
        
    else:
        print(f"❌ Highway shapefile not found at: {highway_shp}")
        print("Please update the highway_shp path to your actual highway shapefile.")