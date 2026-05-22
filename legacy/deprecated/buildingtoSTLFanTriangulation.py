import geopandas as gpd
import numpy as np
import struct
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import transform
import pyproj

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
    
    # Check if polygon is roughly convex for fan triangulation
    # For complex polygons, you might want to use a proper triangulation library
    
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

def extrude_buildings(shapefile, output_stl, height_col=None, default_height=10.0, 
                     ground_level=0.0, use_local_coords=True, target_crs=None):
    """
    Convert building footprints to extruded STL file for OpenFOAM
    
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
    """
    
    print(f"Reading shapefile: {shapefile}")
    gdf = gpd.read_file(shapefile)
    
    print(f"Original CRS: {gdf.crs}")
    print(f"Number of features: {len(gdf)}")
    
    # Handle coordinate system
    if gdf.crs is None:
        print("⚠️ No CRS defined. Assuming EPSG:4326")
        gdf = gdf.set_crs(epsg=4326)
    
    if gdf.crs.to_epsg() == 4326:
        if target_crs is None:
            # Default to UTM Zone 16N for Milwaukee area
            target_crs = 'EPSG:32616'
        print(f"⚠️ Reprojecting from EPSG:4326 to {target_crs}")
        gdf = gdf.to_crs(target_crs)
    
    # Filter valid geometries
    gdf = gdf[gdf.geometry.notna()]
    gdf = gdf[gdf.is_valid]
    
    print(f"Valid geometries: {len(gdf)}")
    
    # Get local coordinate transformation if requested
    offset_x, offset_y = (0, 0)
    if use_local_coords:
        offset_x, offset_y = get_local_transform(gdf)
        print(f"Local coordinate offset: ({offset_x:.2f}, {offset_y:.2f})")
    
    all_triangles = []
    processed_buildings = 0
    
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
    
    print(f"✅ Processed {processed_buildings} buildings")
    print(f"✅ Generated {len(all_triangles)} triangles")
    print(f"✅ STL file written to: {output_stl}")
    
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

# Example usage
if __name__ == "__main__":
    import pandas as pd
    
    shapefile = "windAroundBuildings/Tools/input/kilbourntoClybourn.shp"
    output_stl = "windAroundBuildings/Tools/output/buildingsKilbourn.stl"
    
    extrude_buildings(
        shapefile=shapefile,
        output_stl=output_stl,
        height_col="height",          # Column with building heights
        default_height=12.0,          # Default height in meters
        ground_level=0.0,             # Ground level Z-coordinate
        use_local_coords=True,        # Translate to local coordinates
        target_crs='EPSG:32616'       # UTM Zone 16N for Milwaukee
    )
    
    # Validate the generated STL
    validate_stl(output_stl)