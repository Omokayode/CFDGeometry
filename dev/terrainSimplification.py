import numpy as np
from stl import mesh
import os
from scipy.spatial import cKDTree
from collections import defaultdict

def analyze_terrain_complexity(stl_path):
    """Analyze terrain mesh to understand complexity"""
    terrain_mesh = mesh.Mesh.from_file(stl_path)
    vertices = terrain_mesh.vectors.reshape(-1, 3)
    
    print("=== TERRAIN ANALYSIS ===")
    print(f"Triangles: {len(terrain_mesh.data)}")
    print(f"Vertices: {len(vertices)}")
    
    # Analyze elevation range
    z_coords = vertices[:, 2]
    elevation_range = np.max(z_coords) - np.min(z_coords)
    print(f"Elevation range: {elevation_range:.3f} units")
    print(f"Min elevation: {np.min(z_coords):.3f}")
    print(f"Max elevation: {np.max(z_coords):.3f}")
    
    # Analyze terrain bounds
    bounds = np.array([np.min(vertices, axis=0), np.max(vertices, axis=0)])
    terrain_size = bounds[1] - bounds[0]
    print(f"Terrain dimensions: {terrain_size}")
    
    # Calculate approximate mesh density
    area = terrain_size[0] * terrain_size[1]  # XY area
    density = len(terrain_mesh.data) / area if area > 0 else 0
    print(f"Triangle density: {density:.2f} triangles per unit area")
    
    return {
        'triangles': len(terrain_mesh.data),
        'vertices': len(vertices),
        'elevation_range': elevation_range,
        'bounds': bounds,
        'density': density,
        'z_coords': z_coords
    }

def flatten_terrain_with_threshold(input_stl_path, output_stl_path, 
                                 elevation_threshold=2.0, 
                                 base_elevation=None,
                                 grid_resolution=50):
    """
    Create a flattened terrain that preserves elevation changes above threshold
    
    Args:
        input_stl_path: Input terrain STL file
        output_stl_path: Output flattened STL file
        elevation_threshold: Minimum elevation change to preserve (in model units)
        base_elevation: Base elevation for flat areas (None = use mean elevation)
        grid_resolution: Resolution of the flattened grid
    """
    print(f"Loading terrain for flattening (threshold: {elevation_threshold})...")
    terrain_mesh = mesh.Mesh.from_file(input_stl_path)
    
    # Extract all vertices and find unique points
    all_vertices = terrain_mesh.vectors.reshape(-1, 3)
    
    # Get terrain bounds
    bounds = np.array([np.min(all_vertices, axis=0), np.max(all_vertices, axis=0)])
    terrain_size = bounds[1] - bounds[0]
    
    # Set base elevation
    if base_elevation is None:
        base_elevation = np.mean(all_vertices[:, 2])
    
    print(f"Base elevation: {base_elevation:.3f}")
    print(f"Terrain bounds: X[{bounds[0,0]:.1f}, {bounds[1,0]:.1f}] Y[{bounds[0,1]:.1f}, {bounds[1,1]:.1f}] Z[{bounds[0,2]:.1f}, {bounds[1,2]:.1f}]")
    
    # Create regular grid for flattened terrain
    x_grid = np.linspace(bounds[0,0], bounds[1,0], grid_resolution)
    y_grid = np.linspace(bounds[0,1], bounds[1,1], grid_resolution)
    X, Y = np.meshgrid(x_grid, y_grid)
    
    # Initialize elevation grid with base elevation
    Z = np.full_like(X, base_elevation)
    
    # Find areas where elevation changes exceed threshold
    print("Identifying significant elevation changes...")
    
    # Create spatial index of original vertices for efficient lookup
    tree = cKDTree(all_vertices[:, :2])  # Only X,Y coordinates
    
    # For each grid point, check nearby original vertices for significant elevation changes
    significant_elevations = []
    
    for i in range(grid_resolution):
        for j in range(grid_resolution):
            grid_point = np.array([X[i,j], Y[i,j]])
            
            # Find nearby vertices (within reasonable distance)
            search_radius = max(terrain_size[0], terrain_size[1]) / (grid_resolution * 0.5)
            nearby_indices = tree.query_ball_point(grid_point, search_radius)
            
            if nearby_indices:
                nearby_z_values = all_vertices[nearby_indices, 2]
                
                # Check if any nearby elevation differs from base by more than threshold
                max_elevation_diff = np.max(np.abs(nearby_z_values - base_elevation))
                
                if max_elevation_diff > elevation_threshold:
                    # Use the most significant elevation (furthest from base)
                    extreme_z = nearby_z_values[np.argmax(np.abs(nearby_z_values - base_elevation))]
                    Z[i,j] = extreme_z
                    significant_elevations.append((i, j, extreme_z))
    
    print(f"Found {len(significant_elevations)} grid points with significant elevation changes")
    
    # Smooth transitions between flat and elevated areas
    print("Smoothing elevation transitions...")
    Z_smoothed = Z.copy()
    
    # Apply Gaussian smoothing to reduce abrupt transitions
    from scipy.ndimage import gaussian_filter
    smoothing_sigma = grid_resolution / 20  # Adjust for desired smoothness
    Z_smoothed = gaussian_filter(Z, sigma=smoothing_sigma)
    
    # But preserve the significant elevations
    for i, j, elev in significant_elevations:
        Z_smoothed[i,j] = elev
    
    # Create triangular mesh from the grid
    print("Creating triangular mesh...")
    triangles = []
    
    for i in range(grid_resolution - 1):
        for j in range(grid_resolution - 1):
            # Each grid cell creates 2 triangles
            
            # Triangle 1: (i,j) -> (i+1,j) -> (i,j+1)
            v1 = [X[i,j], Y[i,j], Z_smoothed[i,j]]
            v2 = [X[i+1,j], Y[i+1,j], Z_smoothed[i+1,j]]
            v3 = [X[i,j+1], Y[i,j+1], Z_smoothed[i,j+1]]
            triangles.append([v1, v2, v3])
            
            # Triangle 2: (i+1,j) -> (i+1,j+1) -> (i,j+1)
            v1 = [X[i+1,j], Y[i+1,j], Z_smoothed[i+1,j]]
            v2 = [X[i+1,j+1], Y[i+1,j+1], Z_smoothed[i+1,j+1]]
            v3 = [X[i,j+1], Y[i,j+1], Z_smoothed[i,j+1]]
            triangles.append([v1, v2, v3])
    
    # Convert to numpy array
    triangles = np.array(triangles)
    
    # Create STL mesh
    flattened_mesh = mesh.Mesh(np.zeros(len(triangles), dtype=mesh.Mesh.dtype))
    flattened_mesh.vectors = triangles
    
    # Calculate statistics
    flat_area_ratio = 1.0 - (len(significant_elevations) / (grid_resolution * grid_resolution))
    elevation_range_new = np.max(Z_smoothed) - np.min(Z_smoothed)
    elevation_range_original = bounds[1,2] - bounds[0,2]
    
    print(f"\nFlattening Results:")
    print(f"  Original triangles: {len(terrain_mesh.data):,}")
    print(f"  New triangles: {len(triangles):,}")
    print(f"  Grid resolution: {grid_resolution}x{grid_resolution}")
    print(f"  Elevation threshold: {elevation_threshold}")
    print(f"  Flat area ratio: {flat_area_ratio:.1%}")
    print(f"  Original elevation range: {elevation_range_original:.3f}")
    print(f"  New elevation range: {elevation_range_new:.3f}")
    print(f"  Elevation reduction: {(1 - elevation_range_new/elevation_range_original):.1%}")
    
    flattened_mesh.save(output_stl_path)
    print(f"  Saved to: {output_stl_path}")
    
    return flattened_mesh

def create_simple_flat_terrain(input_stl_path, output_stl_path, elevation=None):
    """
    Create a completely flat terrain at specified elevation
    """
    print("Creating completely flat terrain...")
    terrain_mesh = mesh.Mesh.from_file(input_stl_path)
    all_vertices = terrain_mesh.vectors.reshape(-1, 3)
    
    # Get terrain bounds
    bounds = np.array([np.min(all_vertices, axis=0), np.max(all_vertices, axis=0)])
    
    if elevation is None:
        elevation = np.mean(all_vertices[:, 2])
    
    print(f"Flat elevation: {elevation:.3f}")
    
    # Create simple rectangular flat surface (2 triangles)
    x_min, x_max = bounds[0,0], bounds[1,0]
    y_min, y_max = bounds[0,1], bounds[1,1]
    
    # Triangle 1
    t1 = [[x_min, y_min, elevation],
          [x_max, y_min, elevation], 
          [x_min, y_max, elevation]]
    
    # Triangle 2  
    t2 = [[x_max, y_min, elevation],
          [x_max, y_max, elevation],
          [x_min, y_max, elevation]]
    
    triangles = np.array([t1, t2])
    
    flat_mesh = mesh.Mesh(np.zeros(2, dtype=mesh.Mesh.dtype))
    flat_mesh.vectors = triangles
    
    flat_mesh.save(output_stl_path)
    print(f"Flat terrain saved to: {output_stl_path}")
    
    return flat_mesh

def main():
    # Your specific file paths
    base_path = "/Users/omokayj/vsCode.local/urbanWindFlow/Tools/output/terrainSimplification/"
    # input_terrain = base_path + "terrainKilbourn_clippedExtended.stl"
    input_terrain = "/Users/omokayj/vsCode.local/urbanWindFlow/Tools/output/terrainMarquetteClipped.stl"

    print("TERRAIN FLATTENING TOOL FOR CFD")
    print("=" * 50)
    print(f"Looking for terrain in: {base_path}")
    
    # Check if input file exists
    if not os.path.exists(input_terrain):
        print(f"Default terrain file not found: {input_terrain}")
        print("Searching for terrain files in directory...")
        
        terrain_files = []
        if os.path.exists(base_path):
            for file in os.listdir(base_path):
                if file.lower().endswith('.stl') and 'terrain' in file.lower():
                    terrain_files.append(file)
        
        if terrain_files:
            print("Found potential terrain files:")
            for i, file in enumerate(terrain_files):
                print(f"  {i+1}. {file}")
            
            input_terrain = base_path + terrain_files[0]
            print(f"Using: {terrain_files[0]}")
        else:
            print("No terrain files found. Please check the path or filename.")
            return
    
    try:
        # Analyze original terrain
        stats = analyze_terrain_complexity(input_terrain)
        elevation_range = stats['elevation_range']
        
        print("\n" + "=" * 50)
        print("CREATING FLATTENED TERRAIN VERSIONS")
        print("=" * 50)
        
        # Suggest thresholds based on elevation range
        suggested_thresholds = [
            elevation_range * 0.05,  # 5% of range
            elevation_range * 0.10,  # 10% of range  
            elevation_range * 0.20,  # 20% of range
        ]
        
        print(f"Suggested elevation thresholds (based on {elevation_range:.2f} total range):")
        for i, thresh in enumerate(suggested_thresholds):
            print(f"  {i+1}. {thresh:.2f} units ({thresh/elevation_range:.0%} of range)")
        
        # Create multiple versions with different thresholds
        thresholds_to_create = [
            (elevation_range * 0.10, "conservative", "10% threshold"),
            (elevation_range * 0.20, "moderate", "20% threshold"), 
            (elevation_range * 0.50, "aggressive", "50% threshold")
        ]
        
        for threshold, suffix, description in thresholds_to_create:
            print(f"\n🔹 Creating {description.upper()} flattened terrain...")
            # output_path = base_path + f"terrain_flat_{suffix}.stl"
            output_path = base_path + f"terrain_Marquette_{suffix}.stl"
            flatten_terrain_with_threshold(
                input_terrain, 
                output_path,
                elevation_threshold=threshold,
                grid_resolution=100  # Higher resolution for better quality
            )
        
        # Also create completely flat version
        print(f"\n🔹 Creating COMPLETELY FLAT terrain...")
        flat_output = base_path + "terrain_completely_flat.stl"
        create_simple_flat_terrain(input_terrain, flat_output)
        
        print("\n" + "="*50)
        print("✅ TERRAIN FLATTENING COMPLETE!")
        print("="*50)
        print("Created files:")
        print(f"  🟢 Conservative: terrain_flat_conservative.stl (preserves 10%+ elevation changes)")
        print(f"  🟡 Moderate: terrain_flat_moderate.stl (preserves 20%+ elevation changes)")
        print(f"  🔴 Aggressive: terrain_flat_aggressive.stl (preserves 50%+ elevation changes)")
        print(f"  ⚪ Completely Flat: terrain_completely_flat.stl (no elevation variation)")
        print()
        print("💡 RECOMMENDATIONS FOR CFD:")
        print("  • Use CONSERVATIVE for maintaining important topographic features")
        print("  • Use MODERATE for balanced simplification")
        print("  • Use AGGRESSIVE for nearly flat terrain with only major features")
        print("  • Use COMPLETELY FLAT for baseline comparisons")
        print("  • All versions maintain original terrain boundaries")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()