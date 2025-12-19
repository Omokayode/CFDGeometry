import geopandas as gpd
import numpy as np
import struct
from shapely.geometry import Point
import warnings
import pandas as pd
warnings.filterwarnings('ignore')

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

def create_tree_canopy(point, canopy_radius, trunk_height, canopy_height, trunk_radius,
                      canopy_shape='cylinder', sides=8):
    """Create tree geometry with proper triangle winding"""
    x, y = point.x, point.y
    triangles = []
    angles = np.linspace(0, 2*np.pi, sides+1)[:-1]
    
    # Trunk (if present)
    if trunk_height > 0 and trunk_radius > 0:
        trunk_bottom = [[x + trunk_radius*np.cos(a), y + trunk_radius*np.sin(a), 0] for a in angles]
        trunk_top = [[x + trunk_radius*np.cos(a), y + trunk_radius*np.sin(a), trunk_height] for a in angles]
        trunk_center_bottom = [x, y, 0]
        trunk_center_top = [x, y, trunk_height]
        
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
    canopy_base_z = trunk_height
    canopy_top_z = trunk_height + canopy_height
    
    if canopy_shape == 'cylinder':
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

def shapefile_points_to_trees_aligned(shapefile_path, output_path, 
                                    combined_offset_x, combined_offset_y,
                                    height_column=None, default_height=5.0,
                                    tree_config=None, use_local_coords=True,
                                    target_crs='EPSG:32616'):
    """
    Convert point shapefile to tree STL using combined offset for alignment
    
    Args:
        shapefile_path: Path to tree shapefile
        output_path: Output STL file path
        combined_offset_x, combined_offset_y: Combined offset from get_combined_offset()
        height_column: Column name for tree heights (optional)
        default_height: Default tree height if no height column
        tree_config: Tree configuration dictionary
        use_local_coords: Whether to apply offset transformation
        target_crs: Target coordinate reference system
    """
    
    if tree_config is None:
        tree_config = {
            'canopy_shape': 'cylinder',  # 'cylinder' or 'sphere'
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
    
    # Use the provided combined offset instead of calculating local offset
    print(f"Using combined coordinate offset: ({combined_offset_x:.2f}, {combined_offset_y:.2f})")
    
    triangles = []
    trees_created = 0
    height_stats = []
    
    for idx, row in point_gdf.iterrows():
        geom = row.geometry
        
        # Apply combined coordinate transformation
        if use_local_coords:
            adjusted_point = Point(geom.x - combined_offset_x, geom.y - combined_offset_y)
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
            tree_triangles = create_tree_canopy(
                point=adjusted_point,
                canopy_radius=canopy_radius,
                trunk_height=trunk_height,
                canopy_height=canopy_height,
                trunk_radius=trunk_radius,
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
        'combined_offset': (combined_offset_x, combined_offset_y)
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
    tree_shp = "windAroundBuildings/Tools/input/treesshapefileKilbourn.shp"
    building_shp = "windAroundBuildings/Tools/input/kilbourntoClybourn.shp"
    output_path = "windAroundBuildings/Tools/output/treesKilbourn.stl"
    
    # Step 1: Calculate combined offset from both shapefiles for alignment
    print("🔄 Calculating combined offset for alignment...")
    offset_x, offset_y = get_combined_offset([tree_shp, building_shp], target_epsg=32616)
    
    # Tree configuration
    custom_tree_config = {
        'canopy_shape': 'cylinder',    # or 'sphere'
        'trunk_height_ratio': 0.3,
        'canopy_radius_ratio': 0.4,
        'trunk_radius': 0.1,
        'detail_level': 12,
        'min_tree_height': 2.0,
        'max_tree_height': 20.0
    }
    
    # Step 2: Generate trees using the combined offset for alignment
    print("\n🌳 Generating tree STL with combined alignment...")
    result = shapefile_points_to_trees_aligned(
        shapefile_path=tree_shp,
        output_path=output_path,
        combined_offset_x=offset_x,    # Use combined offset
        combined_offset_y=offset_y,    # Use combined offset
        height_column=None,            # Or specify height column name
        default_height=5.0,
        tree_config=custom_tree_config,
        use_local_coords=True,         # Apply offset transformation
        target_crs='EPSG:32616'        # Same as building code
    )
    
    # Step 3: Validate the generated STL
    validate_tree_stl(output_path)
    
    print("\n📊 Final Summary:")
    for k, v in result.items():
        print(f"  {k}: {v}")
    
    print(f"\n✅ Trees and buildings are now aligned using combined offset: ({offset_x:.2f}, {offset_y:.2f})")