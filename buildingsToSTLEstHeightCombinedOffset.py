import geopandas as gpd
import pandas as pd
import numpy as np
import struct
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import transform
import pyproj
import warnings
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
    Fix missing CRS by reading from .prj file
    """
    buildings = gpd.read_file(shapefile_path)
    
    if buildings.crs is None:
        print("⚠️ No CRS detected. Checking for .prj file...")
        prj_file = shapefile_path.replace('.shp', '.prj')
        try:
            with open(prj_file, 'r') as f:
                prj_content = f.read().strip()
                print(f"Found .prj file content: {prj_content[:100]}...")
                
                # Try to set CRS from .prj file
                buildings = buildings.set_crs(prj_content)
                print(f"✅ CRS set from .prj file: {buildings.crs}")
                
                # Save the shapefile with proper CRS
                buildings.to_file(shapefile_path)
                print(f"✅ Shapefile saved with CRS information")
                
        except FileNotFoundError:
            print(f"❌ No .prj file found at {prj_file}")
            print("🔧 Assuming EPSG:4326 (WGS84). Please verify this is correct.")
            buildings = buildings.set_crs('EPSG:4326')
        except Exception as e:
            print(f"❌ Error reading .prj file: {e}")
            print("🔧 Assuming EPSG:4326 (WGS84). Please verify this is correct.")
            buildings = buildings.set_crs('EPSG:4326')
    
    return buildings

def estimate_heights_from_footprint_area(shapefile_path, output_path=None):
    """
    Estimate building heights based on footprint area and urban planning rules
    """
    
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

def polygon_to_triangles(polygon: Polygon, height: float, ground_level: float = 0.0):
    """Extrude 2D polygon vertically into 3D triangles (roof, base, sides)"""
    triangles = []
    exterior = list(polygon.exterior.coords)
    
    if len(exterior) < 4:  # Need at least 3 unique points + closing point
        return triangles
    
    # Remove duplicate closing point for processing
    if exterior[0] == exterior[-1]:
        exterior = exterior[:-1]
    
    if len(exterior) < 3:
        return triangles
    
    # Triangulate base (at ground level) and roof (at ground + height)
    base_tri = triangulate_2d(exterior, z=ground_level, invert=True)  # Invert for downward normal
    roof_tri = triangulate_2d(exterior, z=ground_level + height, invert=False)  # Upward normal
    
    triangles.extend(base_tri + roof_tri)
    
    # Side walls - ensure proper winding order for outward normals
    for i in range(len(exterior)):
        p1 = exterior[i]
        p2 = exterior[(i + 1) % len(exterior)]
        
        # Bottom edge vertices
        a = [p1[0], p1[1], ground_level]
        b = [p2[0], p2[1], ground_level]
        # Top edge vertices  
        c = [p1[0], p1[1], ground_level + height]
        d = [p2[0], p2[1], ground_level + height]
        
        # Two triangles per wall - ensure outward normals
        triangles.append([a, c, b])  # First triangle
        triangles.append([b, c, d])  # Second triangle
    
    return triangles

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
        header = b'Building STL for OpenFOAM'
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

def extrude_buildings_with_height_estimation(shapefile, output_stl, height_col=None, 
                                           default_height=10.0, ground_level=0.0, 
                                           use_local_coords=True, target_crs=None,
                                           estimate_heights=True, combined_offset=None,
                                           shapefile_list=None):
    """
    Convert building footprints to extruded STL file for OpenFOAM with height estimation
    
    Parameters:
    -----------
    shapefile : str
        Path to input shapefile
    output_stl : str  
        Path to output STL file
    height_col : str, optional
        Column name containing building heights
    default_height : float
        Default height for buildings without height data
    ground_level : float
        Z-coordinate for building base
    use_local_coords : bool
        Whether to translate to local coordinate system
    target_crs : str or int, optional
        Target CRS (e.g., 'EPSG:32616' for UTM Zone 16N)
    estimate_heights : bool
        Whether to estimate heights from footprint areas
    combined_offset : tuple, optional
        Pre-calculated combined offset (offset_x, offset_y)
    shapefile_list : list, optional
        List of all shapefiles for combined offset calculation
    """
    
    print(f"Reading shapefile: {shapefile}")
    
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
    if target_crs is None:
        target_crs = 'EPSG:32616'  # Default to UTM Zone 16N for Milwaukee
        
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
        
        # Apply local coordinate transformation
        if use_local_coords:
            geom = transform(lambda x, y: (x - offset_x, y - offset_y), geom)
        
        # Process geometry
        if isinstance(geom, Polygon):
            tris = polygon_to_triangles(geom, height, ground_level)
            all_triangles.extend(tris)
            processed_buildings += 1
            
        elif isinstance(geom, MultiPolygon):
            for poly in geom.geoms:
                if poly.is_valid and not poly.is_empty:
                    tris = polygon_to_triangles(poly, height, ground_level)
                    all_triangles.extend(tris)
            processed_buildings += 1
    
    if not all_triangles:
        print("❌ No triangles generated!")
        return
    
    # Write STL file
    write_stl_binary(output_stl, all_triangles)
    
    print(f"\n✅ Processing complete!")
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
        
        print(f"\nMesh bounds for OpenFOAM blockMeshDict:")
        print(f"X: [{bounds['x_min']:.2f}, {bounds['x_max']:.2f}]")
        print(f"Y: [{bounds['y_min']:.2f}, {bounds['y_max']:.2f}]") 
        print(f"Z: [{bounds['z_min']:.2f}, {bounds['z_max']:.2f}]")

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
            expected_size = 80 + 4 + (triangle_count * 50)  # Header + count + triangles
            actual_size = f.seek(0, 2)  # Seek to end
            
            if actual_size == expected_size:
                print("✅ File size matches expected size")
            else:
                print(f"⚠️ Size mismatch: expected {expected_size}, got {actual_size}")
                
    except Exception as e:
        print(f"❌ STL validation failed: {e}")

def process_multiple_shapefiles_with_combined_offset(shapefile_list, output_dir, 
                                                   target_crs='EPSG:32616', **kwargs):
    """
    Process multiple shapefiles using the same combined offset for consistency
    
    Parameters:
    -----------
    shapefile_list : list
        List of shapefile paths to process
    output_dir : str
        Directory for output STL files
    target_crs : str
        Target coordinate reference system
    **kwargs : dict
        Additional arguments passed to extrude_buildings_with_height_estimation
    """
    import os
    
    # Calculate combined offset once for all shapefiles
    target_epsg = int(target_crs.split(':')[1])
    combined_offset = get_combined_offset(shapefile_list, target_epsg)
    
    print(f"\n🔄 Processing {len(shapefile_list)} shapefiles with combined offset...")
    
    for shapefile in shapefile_list:
        # Generate output filename
        base_name = os.path.splitext(os.path.basename(shapefile))[0]
        output_stl = os.path.join(output_dir, f"{base_name}.stl")
        
        print(f"\n{'='*60}")
        print(f"Processing: {shapefile}")
        print(f"Output: {output_stl}")
        
        # Process with combined offset
        extrude_buildings_with_height_estimation(
            shapefile=shapefile,
            output_stl=output_stl,
            target_crs=target_crs,
            combined_offset=combined_offset,
            shapefile_list=shapefile_list,
            **kwargs
        )
        
        # Validate each STL
        validate_stl(output_stl)

# Example usage
if __name__ == "__main__":
    
    # Example 1: Single shapefile with combined offset calculation
    # shapefile = "/mnt/nas/vsCode/resources/urbanWindFlow/Tools/input/kilbourntoClybourn.shp"
    # output_stl = "/mnt/nas/vsCode/resources/urbanWindFlow/Tools/output/buildingsKilbourn.stl"
    shapefile = "/home/omokayj/marquetteDrive/Research/s26Research/shp/okcity.shp"
    output_stl = "/home/omokayj/marquetteDrive/Research/s26Research/shp/okcity_python.stl"
    
    # List of all shapefiles for combined offset (even if processing one at a time)
    all_shapefiles = [
        # "/mnt/nas/vsCode/resources/urbanWindFlow/Tools/input/kilbourntoClybourn.shp",
        # "/mnt/nas/vsCode/resources/urbanWindFlow/Tools/input/treesshapefileKilbourn.shp"
        "/home/omokayj/marquetteDrive/Research/s26Research/shp/okcity.shp"
        # Add other shapefile paths here for combined offset calculation
    ]
    
    extrude_buildings_with_height_estimation(
        shapefile=shapefile,
        output_stl=output_stl,
        default_height=12.0,          # Default height in meters
        ground_level=0.0,             # Ground level Z-coordinate
        use_local_coords=True,        # Translate to local coordinates
        target_crs='EPSG:32616',      # UTM Zone 16N for Milwaukee
        estimate_heights=True,        # Enable height estimation
        shapefile_list=all_shapefiles # For combined offset calculation
    )
    
    validate_stl(output_stl)
    
    # Example 2: Process multiple shapefiles with shared combined offset
    """
    shapefile_list = [
        "/mnt/nas/vsCode/resources/urbanWindFlow/Tools/input/shapefile1.shp",
        "/mnt/nas/vsCode/resources/urbanWindFlow/Tools/input/shapefile2.shp",
        "/mnt/nas/vsCode/resources/urbanWindFlow/Tools/input/shapefile3.shp"
    ]
    
    process_multiple_shapefiles_with_combined_offset(
        shapefile_list=shapefile_list,
        output_dir="/mnt/nas/vsCode/resources/urbanWindFlow/Tools/output/",
        target_crs='EPSG:32616',
        default_height=12.0,
        ground_level=0.0,
        use_local_coords=True,
        estimate_heights=True
    )
    """