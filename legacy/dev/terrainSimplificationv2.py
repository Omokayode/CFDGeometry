import numpy as np
from stl import mesh
import os
from scipy.spatial import cKDTree
from scipy.ndimage import gaussian_filter
from scipy.interpolate import griddata

'''
Module: terrainSimplificationv2.py
Purpose
-------
Provide tools to generate a simplified, "flattened" version of a terrain mesh (STL)
that preserves meaningful elevation changes while protecting against isolated
outlier spikes. The module samples the input STL onto a regular 2D grid, selectively
transfers significant elevation features, applies smoothing, enforces a maximum
neighbor-to-neighbor elevation difference, validates continuity, and writes a new
triangulated STL mesh.
Key functions
-------------
flatten_terrain_with_outlier_protection(input_stl_path, output_stl_path,
                                        smoothing_sigma=2.0)
    - Create a flattened terrain mesh from an input STL and save to output_stl_path.
    - Algorithm summary:
        1. Load input STL and compute bounding box and median elevation (base_elevation).
        2. Create a regular XY grid at grid_resolution and initialize all Z to base_elevation.
        3. For each grid cell, search nearby mesh vertices (using cKDTree). If the median
           local vertex elevation differs from base_elevation by more than elevation_threshold,
           adopt the median elevation for that grid cell. (Median reduces single-vertex outlier influence.)
        4. Smooth Z with a Gaussian filter (smoothing_sigma).
        5. Iteratively enforce a max_neighbor_diff constraint so no grid cell differs from
           the median of its 8-connected neighbors by more than max_neighbor_diff.
        6. Apply a final light smoothing pass.
        7. Validate neighbor continuity (reports max/mean/95th percentile neighbor diffs).
        8. Triangulate the regular grid into two triangles per cell and write a new STL.
    - Important parameters:
        - elevation_threshold: minimum absolute Z offset from base_elevation to preserve (prevents small noise)
        - base_elevation: if None, uses median Z of all input vertices
        - grid_resolution: number of grid points per dimension (NxN grid)
        - max_neighbor_diff: clamps isolated spikes by limiting elevation difference to neighbors
        - smoothing_sigma: Gaussian smoothing strength (higher -> smoother)
    - Returns:
        - The created stl mesh.Mesh object (and writes the file to output_stl_path)
    - Side effects:
        - Loads input_stl_path, writes to output_stl_path, prints progress and statistics.
detect_and_visualize_outliers(stl_path)
    - Simple diagnostic utility that loads an STL and checks every vertex against its
      nearest neighbors (via cKDTree). Flags vertices whose elevation deviates from
      the median of its nearest neighbors by a hard threshold (currently 10.0 units).
    - Returns:
        - A list of detected outlier dictionaries with index, position, z, neighbor_median_z, difference.
    - Use to debug and confirm whether the output STL still contains isolated spikes.
    - Example driver that:
        1. Loads a hardcoded input terrain file (path configurable in the function).
        2. Computes the overall elevation range.
        3. Generates multiple flattened variants using different configurations
           (conservative/moderate/aggressive) by calling flatten_terrain_with_outlier_protection.
        4. Runs detect_and_visualize_outliers on created outputs to validate results.
    - Intended for local quick experimentation; paths and configurations are currently
      hard-coded and should be adapted before reuse.
Usage notes, tuning and trade-offs
---------------------------------
- grid_resolution controls the output mesh resolution (memory/time scales ~O(N^2)).
  Use a higher resolution for more fidelity but expect increased compute and output size.
- elevation_threshold controls sensitivity to small features: smaller values preserve
  more terrain detail but may allow small spikes; larger values produce flatter output.
- max_neighbor_diff is the primary protection against isolated spikes: reduce it to clamp
  more aggressively, or increase to preserve steeper local slopes.
- smoothing_sigma influences visual smoothness and helps remove checkerboard artifacts.
- The approach intentionally uses local median sampling to reduce influence from single-vertex
  outliers; the iterative neighbor-clamping enforces local continuity after smoothing.
- Performance: the code uses cKDTree for neighbor queries but iterates over grid points
  in Python loops; for very large grids consider vectorized sampling or parallelization.
Limitations and caveats
-----------------------
- Input/Output paths are not parameterized beyond function arguments; main() contains demo paths.
- The current implementation assumes well-formed STL meshes and works in XY plane sampling
  (Z treated as elevation). Non-planar or multi-layered STLs may require additional handling.
- Triangulation produced is a simple regular-grid triangulation and will not preserve
  original mesh topology or features not captured by the grid sampling.
- The outlier detection threshold in detect_and_visualize_outliers is a constant (10.0);
  adjust according to units and dataset scale.
Example (conceptual)
--------------------
- Import module and call:
    flatten_terrain_with_outlier_protection("input.stl", "output_flattened.stl",
                                            elevation_threshold=1.0,
                                            grid_resolution=150,
                                            max_neighbor_diff=3.0,
                                            smoothing_sigma=2.5)
Return values and side effects are documented with the function docstrings; this module
is intended for interactive/experimental use and for producing STL files that are
smoother, more regularized, and less prone to isolated elevation spikes.
'''

def flatten_terrain_with_outlier_protection(input_stl_path, output_stl_path, 
                                            elevation_threshold=2.0, 
                                            base_elevation=None,
                                            grid_resolution=100,
                                            max_neighbor_diff=5.0,
                                            smoothing_sigma=2.0):
    """
    Create flattened terrain that tracks elevation changes BUT prevents outlier spikes
    
    Key features:
    - Preserves significant elevation changes (for building alignment)
    - Enforces maximum difference between neighboring grid points
    - Validates elevation continuity
    - Removes isolated spikes
    
    Args:
        elevation_threshold: Minimum elevation change to preserve
        max_neighbor_diff: Maximum allowed elevation difference between adjacent grid points
        smoothing_sigma: Amount of smoothing (higher = smoother)
    """
    print(f"Loading terrain (threshold: {elevation_threshold}, max neighbor diff: {max_neighbor_diff})...")
    terrain_mesh = mesh.Mesh.from_file(input_stl_path)
    
    all_vertices = terrain_mesh.vectors.reshape(-1, 3)
    bounds = np.array([np.min(all_vertices, axis=0), np.max(all_vertices, axis=0)])
    terrain_size = bounds[1] - bounds[0]
    
    if base_elevation is None:
        base_elevation = np.median(all_vertices[:, 2])
    
    print(f"Base elevation: {base_elevation:.3f}")
    print(f"Terrain bounds: X[{bounds[0,0]:.1f}, {bounds[1,0]:.1f}] Y[{bounds[0,1]:.1f}, {bounds[1,1]:.1f}] Z[{bounds[0,2]:.1f}, {bounds[1,2]:.1f}]")
    
    # Create grid
    x_grid = np.linspace(bounds[0,0], bounds[1,0], grid_resolution)
    y_grid = np.linspace(bounds[0,1], bounds[1,1], grid_resolution)
    X, Y = np.meshgrid(x_grid, y_grid)
    
    # Initialize with base elevation
    Z = np.full_like(X, base_elevation)
    
    # Create spatial index
    tree = cKDTree(all_vertices[:, :2])
    
    # Grid spacing for neighbor search
    grid_spacing_x = (bounds[1,0] - bounds[0,0]) / (grid_resolution - 1)
    grid_spacing_y = (bounds[1,1] - bounds[0,1]) / (grid_resolution - 1)
    search_radius = max(grid_spacing_x, grid_spacing_y) * 1.5
    
    print("Sampling elevations at grid points...")
    
    # For each grid point, find representative elevation
    for i in range(grid_resolution):
        for j in range(grid_resolution):
            grid_point = np.array([X[i,j], Y[i,j]])
            
            # Find nearby vertices
            nearby_indices = tree.query_ball_point(grid_point, search_radius)
            
            if nearby_indices:
                nearby_z_values = all_vertices[nearby_indices, 2]
                
                # Use MEDIAN of nearby points (more robust than max)
                # This prevents single outlier vertices from creating spikes
                median_z = np.median(nearby_z_values)
                
                # Check if elevation change is significant
                elevation_diff = abs(median_z - base_elevation)
                
                if elevation_diff > elevation_threshold:
                    Z[i,j] = median_z
    
    # Apply smoothing to reduce sharp transitions
    print(f"Applying smoothing (sigma={smoothing_sigma})...")
    Z_smoothed = gaussian_filter(Z, sigma=smoothing_sigma)
    
    # CRITICAL FIX: Enforce maximum neighbor difference constraint
    print(f"Enforcing max neighbor difference ({max_neighbor_diff})...")
    
    Z_constrained = Z_smoothed.copy()
    max_iterations = 10
    
    for iteration in range(max_iterations):
        changes_made = 0
        
        for i in range(grid_resolution):
            for j in range(grid_resolution):
                # Get neighboring elevations (8-connected)
                neighbors = []
                
                for di in [-1, 0, 1]:
                    for dj in [-1, 0, 1]:
                        if di == 0 and dj == 0:
                            continue
                        ni, nj = i + di, j + dj
                        if 0 <= ni < grid_resolution and 0 <= nj < grid_resolution:
                            neighbors.append(Z_constrained[ni, nj])
                
                if neighbors:
                    neighbors = np.array(neighbors)
                    median_neighbor = np.median(neighbors)
                    
                    # Check if current point is too different from neighbors
                    diff = abs(Z_constrained[i,j] - median_neighbor)
                    
                    if diff > max_neighbor_diff:
                        # Clamp to acceptable range
                        if Z_constrained[i,j] > median_neighbor:
                            Z_constrained[i,j] = median_neighbor + max_neighbor_diff
                        else:
                            Z_constrained[i,j] = median_neighbor - max_neighbor_diff
                        changes_made += 1
        
        print(f"  Iteration {iteration+1}: {changes_made} points adjusted")
        
        if changes_made == 0:
            break
    
    # Final light smoothing to blend any remaining discontinuities
    Z_final = gaussian_filter(Z_constrained, sigma=smoothing_sigma * 0.5)
    
    # Validate: Check for remaining outliers
    print("\nValidating elevation continuity...")
    max_differences = []
    for i in range(grid_resolution):
        for j in range(grid_resolution):
            neighbors = []
            for di in [-1, 0, 1]:
                for dj in [-1, 0, 1]:
                    if di == 0 and dj == 0:
                        continue
                    ni, nj = i + di, j + dj
                    if 0 <= ni < grid_resolution and 0 <= nj < grid_resolution:
                        neighbors.append(Z_final[ni, nj])
            
            if neighbors:
                max_diff = max(abs(Z_final[i,j] - np.array(neighbors)))
                max_differences.append(max_diff)
    
    max_differences = np.array(max_differences)
    print(f"  Max neighbor difference in result: {np.max(max_differences):.3f}")
    print(f"  Mean neighbor difference: {np.mean(max_differences):.3f}")
    print(f"  95th percentile difference: {np.percentile(max_differences, 95):.3f}")
    
    # Create triangular mesh
    print("Creating mesh...")
    triangles = []
    
    for i in range(grid_resolution - 1):
        for j in range(grid_resolution - 1):
            # Triangle 1
            v1 = [X[i,j], Y[i,j], Z_final[i,j]]
            v2 = [X[i+1,j], Y[i+1,j], Z_final[i+1,j]]
            v3 = [X[i,j+1], Y[i,j+1], Z_final[i,j+1]]
            triangles.append([v1, v2, v3])
            
            # Triangle 2
            v1 = [X[i+1,j], Y[i+1,j], Z_final[i+1,j]]
            v2 = [X[i+1,j+1], Y[i+1,j+1], Z_final[i+1,j+1]]
            v3 = [X[i,j+1], Y[i,j+1], Z_final[i,j+1]]
            triangles.append([v1, v2, v3])
    
    triangles = np.array(triangles)
    flattened_mesh = mesh.Mesh(np.zeros(len(triangles), dtype=mesh.Mesh.dtype))
    flattened_mesh.vectors = triangles
    
    # Statistics
    elevation_range_new = np.max(Z_final) - np.min(Z_final)
    elevation_range_original = bounds[1,2] - bounds[0,2]
    
    print(f"\nFlattening Results:")
    print(f"  Original triangles: {len(terrain_mesh.data):,}")
    print(f"  New triangles: {len(triangles):,}")
    print(f"  Original elevation range: {elevation_range_original:.3f}")
    print(f"  New elevation range: {elevation_range_new:.3f}")
    print(f"  Elevation reduction: {(1 - elevation_range_new/elevation_range_original):.1%}")
    
    flattened_mesh.save(output_stl_path)
    print(f"  Saved to: {output_stl_path}")
    
    return flattened_mesh


def detect_and_visualize_outliers(stl_path):
    """
    Helper function to detect outliers in an STL terrain
    Use this to debug existing files
    """
    print(f"\n=== OUTLIER DETECTION: {os.path.basename(stl_path)} ===")
    terrain_mesh = mesh.Mesh.from_file(stl_path)
    vertices = terrain_mesh.vectors.reshape(-1, 3)
    
    # Build spatial index
    tree = cKDTree(vertices[:, :2])
    
    outliers = []
    
    # For each vertex, check neighbors
    for i, vertex in enumerate(vertices):
        # Find 8 nearest neighbors
        distances, indices = tree.query(vertex[:2], k=9)  # k=9 includes self
        
        if len(indices) > 1:
            neighbor_z = vertices[indices[1:], 2]  # Exclude self
            neighbor_median = np.median(neighbor_z)
            
            diff = abs(vertex[2] - neighbor_median)
            
            if diff > 10.0:  # Flag if >10 units different
                outliers.append({
                    'index': i,
                    'position': vertex,
                    'z': vertex[2],
                    'neighbor_median_z': neighbor_median,
                    'difference': diff
                })
    
    if outliers:
        print(f"⚠️  Found {len(outliers)} potential outliers:")
        for out in sorted(outliers, key=lambda x: x['difference'], reverse=True)[:10]:
            print(f"  Point at ({out['position'][0]:.1f}, {out['position'][1]:.1f}): "
                  f"Z={out['z']:.3f}, neighbors median={out['neighbor_median_z']:.3f}, "
                  f"diff={out['difference']:.3f}")
    else:
        print("✅ No significant outliers detected")
    
    return outliers


def main():
    base_path = "/Users/omokayj/vsCode.local/urbanWindFlow/Tools/output/terrainSimplification/"
    input_terrain = "/Users/omokayj/vsCode.local/urbanWindFlow/Tools/output/terrainMarquetteClipped.stl"
    
    if not os.path.exists(input_terrain):
        print(f"Terrain file not found: {input_terrain}")
        return
    
    # Analyze original terrain
    terrain_mesh = mesh.Mesh.from_file(input_terrain)
    all_vertices = terrain_mesh.vectors.reshape(-1, 3)
    elevation_range = np.max(all_vertices[:, 2]) - np.min(all_vertices[:, 2])
    
    print(f"Original elevation range: {elevation_range:.3f}")
    
    # Create versions with different settings
    print("\n=== CREATING FLATTENED TERRAINS WITH OUTLIER PROTECTION ===\n")
    
    configs = [
        # (threshold, max_neighbor_diff, smoothing, suffix)
        (elevation_range * 0.10, 3.0, 2.0, "conservative"),
        (elevation_range * 0.20, 5.0, 2.5, "moderate"),
        (elevation_range * 0.50, 10.0, 3.0, "aggressive"),
    ]
    
    created_files = []
    
    for threshold, max_diff, smoothing, suffix in configs:
        print(f"🔹 Creating {suffix.upper()} terrain...")
        print(f"   Threshold: {threshold:.2f}, Max neighbor diff: {max_diff:.2f}, Smoothing: {smoothing:.2f}")
        
        output_path = base_path + f"terrain_Marquette_{suffix}_fixed.stl"
        
        flatten_terrain_with_outlier_protection(
            input_terrain,
            output_path,
            elevation_threshold=threshold,
            max_neighbor_diff=max_diff,
            smoothing_sigma=smoothing,
            grid_resolution=100
        )
        
        created_files.append(output_path)
        print()
    
    # Validate created files
    print("\n=== VALIDATION: CHECKING FOR OUTLIERS ===")
    for file_path in created_files:
        if os.path.exists(file_path):
            detect_and_visualize_outliers(file_path)
    
    print("\n✅ DONE! All files created with outlier protection.")
    print("\n💡 If you still see issues, try:")
    print("   - Reduce max_neighbor_diff (e.g., 2.0 or 3.0)")
    print("   - Increase smoothing_sigma (e.g., 3.0 or 4.0)")
    print("   - Increase grid_resolution (e.g., 150 or 200)")


if __name__ == "__main__":
    main()