import numpy as np
import struct
from collections import defaultdict

##looks like this works if the terrain is large enough
#use this to generate terrain from building footprints
#it uses just the buildings minimum heights to create the terrain making it fast

def read_stl_binary(filename):
    """Read binary STL file and return vertices."""
    vertices = []
    
    with open(filename, 'rb') as f:
        # Skip 80-byte header
        f.read(80)
        
        # Read number of triangles
        num_triangles = struct.unpack('<I', f.read(4))[0]
        print(f"Reading {num_triangles} triangles...")
        
        for i in range(num_triangles):
            if i % 10000 == 0:
                print(f"Progress: {i}/{num_triangles}")
            
            # Skip normal vector (12 bytes)
            f.read(12)
            
            # Read 3 vertices (9 floats, 36 bytes total)
            for _ in range(3):
                x, y, z = struct.unpack('<3f', f.read(12))
                vertices.append([x, y, z])
            
            # Skip attribute byte count (2 bytes)
            f.read(2)
    
    return np.array(vertices)

def read_stl_ascii(filename):
    """Read ASCII STL file and return vertices."""
    vertices = []
    
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('vertex'):
                coords = line.split()[1:4]
                vertices.append([float(x) for x in coords])
    
    return np.array(vertices)

def read_stl(filename):
    """Read STL file (auto-detect binary or ASCII format)."""
    try:
        return read_stl_binary(filename)
    except:
        try:
            return read_stl_ascii(filename)
        except Exception as e:
            raise Exception(f"Could not read STL file: {e}")

def write_stl_binary(filename, triangles):
    """Write triangles to binary STL file."""
    with open(filename, 'wb') as f:
        # Write 80-byte header
        f.write(b'Terrain from building footprints' + b'\0' * 44)
        
        # Write number of triangles
        f.write(struct.pack('<I', len(triangles)))
        
        for i, triangle in enumerate(triangles):
            if i % 10000 == 0:
                print(f"Writing triangle {i}/{len(triangles)}")
            
            # Calculate normal vector
            v1 = triangle[1] - triangle[0]
            v2 = triangle[2] - triangle[0]
            normal = np.cross(v1, v2)
            norm = np.linalg.norm(normal)
            if norm > 1e-10:
                normal = normal / norm
            else:
                normal = np.array([0, 0, 1])
            
            # Write normal and vertices
            f.write(struct.pack('<3f', *normal))
            for vertex in triangle:
                f.write(struct.pack('<3f', *vertex))
            f.write(struct.pack('<H', 0))

def find_building_footprints(vertices, tolerance=0.1):
    """
    Find minimum Z values across the XY plane by discretizing space.
    This is MUCH faster than any interpolation method.
    """
    print("Finding building footprints...")
    
    # Get bounds
    x_min, x_max = vertices[:, 0].min(), vertices[:, 0].max()
    y_min, y_max = vertices[:, 1].min(), vertices[:, 1].max()
    
    # Create a dictionary to store minimum Z for each XY location
    # We'll discretize to a reasonable resolution
    resolution = 1000  # Adjust based on your model scale
    
    footprint_dict = defaultdict(lambda: float('inf'))
    
    print(f"Processing {len(vertices)} vertices...")
    
    for i, (x, y, z) in enumerate(vertices):
        if i % 50000 == 0:
            print(f"Processed {i}/{len(vertices)} vertices")
        
        # Discretize XY coordinates
        x_idx = int((x - x_min) / (x_max - x_min) * resolution)
        y_idx = int((y - y_min) / (y_max - y_min) * resolution)
        
        # Store minimum Z for this XY location
        key = (x_idx, y_idx)
        footprint_dict[key] = min(footprint_dict[key], z)
    
    # Convert back to actual coordinates
    footprint_points = []
    for (x_idx, y_idx), min_z in footprint_dict.items():
        actual_x = x_min + (x_idx / resolution) * (x_max - x_min)
        actual_y = y_min + (y_idx / resolution) * (y_max - y_min)
        footprint_points.append([actual_x, actual_y, min_z])
    
    print(f"Found {len(footprint_points)} unique footprint points")
    return np.array(footprint_points)

def create_terrain_triangulation(footprint_points, margin_factor=0.1):
    """Create terrain using Delaunay triangulation of footprint points."""
    from scipy.spatial import Delaunay
    
    print("Creating terrain triangulation...")
    
    # Remove duplicate points first
    unique_points = np.unique(footprint_points, axis=0)
    print(f"Removed {len(footprint_points) - len(unique_points)} duplicate points")
    footprint_points = unique_points
    
    # Get bounds and add margin points
    x_min, x_max = footprint_points[:, 0].min(), footprint_points[:, 0].max()
    y_min, y_max = footprint_points[:, 1].min(), footprint_points[:, 1].max()
    z_min = footprint_points[:, 2].min()
    
    # Add margin
    x_range = x_max - x_min
    y_range = y_max - y_min
    x_margin = x_range * margin_factor
    y_margin = y_range * margin_factor
    
    # Add corner points and edge points for better triangulation
    margin_points = np.array([
        # Corners
        [x_min - x_margin, y_min - y_margin, z_min],
        [x_max + x_margin, y_min - y_margin, z_min],
        [x_max + x_margin, y_max + y_margin, z_min],
        [x_min - x_margin, y_max + y_margin, z_min],
        # Edge midpoints
        [x_min - x_margin, (y_min + y_max) / 2, z_min],
        [x_max + x_margin, (y_min + y_max) / 2, z_min],
        [(x_min + x_max) / 2, y_min - y_margin, z_min],
        [(x_min + x_max) / 2, y_max + y_margin, z_min]
    ])
    
    # Combine footprint and margin points
    all_points = np.vstack([footprint_points, margin_points])
    
    print(f"Triangulating {len(all_points)} points...")
    
    try:
        # Create Delaunay triangulation in 2D (XY plane)
        tri = Delaunay(all_points[:, :2])
        
        # Create 3D triangles with proper vertex ordering (counter-clockwise)
        triangles = []
        for simplex in tri.simplices:
            # Get the 3 points of the triangle
            p0, p1, p2 = all_points[simplex]
            
            # Ensure counter-clockwise ordering (normal pointing up)
            v1 = p1 - p0
            v2 = p2 - p0
            normal = np.cross(v1, v2)
            
            if normal[2] < 0:  # If normal points down, flip vertex order
                triangle = np.array([p0, p2, p1])
            else:
                triangle = np.array([p0, p1, p2])
            
            triangles.append(triangle)
        
        print(f"Created {len(triangles)} triangles")
        return np.array(triangles)
        
    except Exception as e:
        print(f"Triangulation failed: {e}")
        print("Falling back to simple grid method...")
        return create_simple_grid_terrain(footprint_points, margin_factor)

def create_simple_grid_terrain(footprint_points, margin_factor=0.1):
    """Fallback: create simple grid-based terrain."""
    print("Creating simple grid terrain...")
    
    # Get bounds
    x_min, x_max = footprint_points[:, 0].min(), footprint_points[:, 0].max()
    y_min, y_max = footprint_points[:, 1].min(), footprint_points[:, 1].max()
    z_min = footprint_points[:, 2].min()
    
    # Add margin
    x_range = x_max - x_min
    y_range = y_max - y_min
    x_margin = x_range * margin_factor
    y_margin = y_range * margin_factor
    
    # Create simple rectangular terrain at minimum height
    corners = np.array([
        [x_min - x_margin, y_min - y_margin, z_min],
        [x_max + x_margin, y_min - y_margin, z_min],
        [x_max + x_margin, y_max + y_margin, z_min],
        [x_min - x_margin, y_max + y_margin, z_min]
    ])
    
    # Create two triangles for the rectangle
    triangles = np.array([
        [corners[0], corners[1], corners[2]],  # First triangle
        [corners[0], corners[2], corners[3]]   # Second triangle
    ])
    
    print(f"Created simple terrain with {len(triangles)} triangles")
    return triangles

def generate_terrain_from_buildings(input_stl, output_stl, margin_factor=0.1, resolution=500):
    """
    Generate terrain STL that touches building bases.
    Uses building footprint points directly - much faster!
    
    Args:
        input_stl: Path to input STL file containing buildings
        output_stl: Path to output terrain STL file
        margin_factor: Factor to extend terrain beyond building bounds
        resolution: Discretization resolution (higher = more accurate but slower)
    """
    print(f"=== GENERATING TERRAIN FROM {input_stl} ===")
    
    # Read buildings
    vertices = read_stl(input_stl)
    print(f"Loaded {len(vertices)} vertices from buildings")
    
    # Find footprint points (minimum Z for each XY location)
    footprint_points = find_building_footprints(vertices)
    
    # Create terrain triangulation
    triangles = create_terrain_triangulation(footprint_points, margin_factor)
    
    # Write terrain STL
    print(f"Writing terrain to {output_stl}...")
    write_stl_binary(output_stl, triangles)
    
    print(f"=== TERRAIN GENERATION COMPLETE ===")
    print(f"- Input vertices: {len(vertices)}")
    print(f"- Footprint points: {len(footprint_points)}")
    print(f"- Output triangles: {len(triangles)}")
    
    z_min = footprint_points[:, 2].min()
    z_max = footprint_points[:, 2].max()
    print(f"- Terrain height range: {z_min:.2f} to {z_max:.2f}")

def quick_analysis(input_stl):
    """Quick analysis of building file."""
    print("=== QUICK ANALYSIS ===")
    vertices = read_stl(input_stl)
    
    x_min, x_max = vertices[:, 0].min(), vertices[:, 0].max()
    y_min, y_max = vertices[:, 1].min(), vertices[:, 1].max()
    z_min, z_max = vertices[:, 2].min(), vertices[:, 2].max()
    
    print(f"Vertices: {len(vertices)}")
    print(f"X range: {x_min:.2f} to {x_max:.2f} (size: {x_max-x_min:.2f})")
    print(f"Y range: {y_min:.2f} to {y_max:.2f} (size: {y_max-y_min:.2f})")
    print(f"Z range: {z_min:.2f} to {z_max:.2f} (size: {z_max-z_min:.2f})")

# Example usage
if __name__ == "__main__":
    input_file = "/Users/omokayj/Library/CloudStorage/OneDrive-MarquetteUniversity/Research/Fall 25 - Research/Geometry/STLs/buildingsKilbourn0904.stl"  # Replace with your buildings STL file
    output_file = "/Users/omokayj/Library/CloudStorage/OneDrive-MarquetteUniversity/Research/Fall 25 - Research/Geometry/pythonMod/terrain.stl"  # Output terrain file

    try:
        # Quick analysis first
        quick_analysis(input_file)
        
        print("\n" + "="*50)
        
        # Generate terrain
        generate_terrain_from_buildings(
            input_stl=input_file,
            output_stl=output_file,
            margin_factor=0.15,  # 15% margin around buildings
            resolution=500       # Adjust based on your model detail needs
        )
        
    except FileNotFoundError:
        print(f"Error: Could not find input file '{input_file}'")
        print("Please update the 'input_file' variable with your STL filename.")
        
    except ImportError:
        print("Error: This script requires scipy for triangulation.")
        print("Install with: pip install scipy")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
