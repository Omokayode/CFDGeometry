#!/usr/bin/env python3
"""
Optimized Rectangular Base STL Generator with Terrain Integration
Creates a rectangular base/platform that uses terrain as the top surface,
with significant performance optimizations for large terrain meshes.
"""
import numpy as np
import struct
import os
from typing import List, Tuple, Optional, Dict
from collections import defaultdict
import time

class OptimizedRectangularBaseGenerator:
    def __init__(self):
        self.triangles = []
        self.normals = []
        self.offset = (0.0, 0.0)
        self.terrain_triangles = []
        self.spatial_grid = None
        self.grid_size = 100.0  # Size of spatial grid cells
        
    def set_offset(self, offset_x: float, offset_y: float):
        """Set the coordinate offset to match terrain data"""
        self.offset = (offset_x, offset_y)
        print(f"Set coordinate offset: ({offset_x}, {offset_y})")
    
    def _build_spatial_grid(self):
        """Build a spatial grid to accelerate triangle lookups"""
        if not self.terrain_triangles:
            return
            
        print("Building spatial grid for fast triangle lookup...")
        start_time = time.time()
        
        # Find terrain bounds
        all_x = []
        all_y = []
        for triangle in self.terrain_triangles:
            for vertex in triangle:
                all_x.append(vertex[0])
                all_y.append(vertex[1])
        
        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)
        
        # Create grid
        self.spatial_grid = defaultdict(list)
        self.grid_bounds = (min_x, max_x, min_y, max_y)
        
        # Assign triangles to grid cells
        for i, triangle in enumerate(self.terrain_triangles):
            # Get triangle bounding box
            tri_x = [v[0] for v in triangle]
            tri_y = [v[1] for v in triangle]
            tri_min_x, tri_max_x = min(tri_x), max(tri_x)
            tri_min_y, tri_max_y = min(tri_y), max(tri_y)
            
            # Find grid cells this triangle overlaps
            start_gx = int((tri_min_x - min_x) / self.grid_size)
            end_gx = int((tri_max_x - min_x) / self.grid_size) + 1
            start_gy = int((tri_min_y - min_y) / self.grid_size)
            end_gy = int((tri_max_y - min_y) / self.grid_size) + 1
            
            # Add triangle to relevant grid cells
            for gx in range(start_gx, end_gx):
                for gy in range(start_gy, end_gy):
                    self.spatial_grid[(gx, gy)].append(i)
        
        build_time = time.time() - start_time
        print(f"Spatial grid built in {build_time:.2f} seconds")
        print(f"Grid covers {len(self.spatial_grid)} cells")
    
    def _get_candidate_triangles(self, x: float, y: float) -> List[int]:
        """Get candidate triangles for a point using spatial grid"""
        if not self.spatial_grid:
            return list(range(len(self.terrain_triangles)))
        
        min_x, max_x, min_y, max_y = self.grid_bounds
        
        # Find grid cell
        gx = int((x - min_x) / self.grid_size)
        gy = int((y - min_y) / self.grid_size)
        
        return self.spatial_grid.get((gx, gy), [])
    
    def load_terrain_from_stl(self, stl_filename: str) -> bool:
        """Load terrain triangles from an STL file"""
        try:
            if stl_filename.lower().endswith('.stl'):
                success = self._load_stl_binary(stl_filename)
                if success:
                    self._build_spatial_grid()
                return success
            else:
                print(f"Unsupported file format: {stl_filename}")
                return False
        except Exception as e:
            print(f"Error loading terrain file {stl_filename}: {e}")
            return False
    
    def _load_stl_binary(self, filename: str) -> bool:
        """Load triangles from binary STL file"""
        try:
            with open(filename, 'rb') as f:
                # Skip header
                f.read(80)
                
                # Read number of triangles
                num_triangles = struct.unpack('<I', f.read(4))[0]
                print(f"Loading {num_triangles} triangles from terrain STL...")
                
                self.terrain_triangles = []
                for i in range(num_triangles):
                    # Read normal (skip it)
                    f.read(12)
                    
                    # Read three vertices
                    triangle = []
                    for j in range(3):
                        vertex = struct.unpack('<3f', f.read(12))
                        triangle.append(list(vertex))
                    
                    self.terrain_triangles.append(triangle)
                    
                    # Skip attribute byte count
                    f.read(2)
                    
                    if (i + 1) % 10000 == 0:
                        print(f"  Loaded {i + 1}/{num_triangles} triangles...")
                
                print(f"Successfully loaded {len(self.terrain_triangles)} terrain triangles")
                return True
                
        except Exception as e:
            print(f"Error reading binary STL: {e}")
            return False
    
    def _get_terrain_height_at_point(self, x: float, y: float) -> Optional[float]:
        """Get terrain height at a specific X,Y coordinate using optimized triangle lookup"""
        candidate_indices = self._get_candidate_triangles(x, y)
        best_z = None
        
        for triangle_idx in candidate_indices:
            triangle = self.terrain_triangles[triangle_idx]
            # Check if point is inside triangle and get Z coordinate
            z = self._point_in_triangle_z(x, y, triangle)
            if z is not None:
                if best_z is None or z > best_z:  # Take highest Z if multiple triangles
                    best_z = z
        
        return best_z
    
    def _point_in_triangle_z(self, px: float, py: float, triangle: List[List[float]]) -> Optional[float]:
        """Check if point (px, py) is inside triangle and return interpolated Z coordinate"""
        v0, v1, v2 = triangle
        
        # Barycentric coordinate method
        denom = (v1[1] - v2[1]) * (v0[0] - v2[0]) + (v2[0] - v1[0]) * (v0[1] - v2[1])
        
        if abs(denom) < 1e-10:
            return None  # Degenerate triangle
        
        a = ((v1[1] - v2[1]) * (px - v2[0]) + (v2[0] - v1[0]) * (py - v2[1])) / denom
        b = ((v2[1] - v0[1]) * (px - v2[0]) + (v0[0] - v2[0]) * (py - v2[1])) / denom
        c = 1 - a - b
        
        # Check if point is inside triangle
        if a >= -1e-10 and b >= -1e-10 and c >= -1e-10:  # Small tolerance for edge cases
            # Interpolate Z coordinate
            z = a * v0[2] + b * v1[2] + c * v2[2]
            return z
        
        return None
    
    def create_terrain_fitted_base(self, base_bounds: Dict[str, float], base_thickness: float = 20.0,
                                 grid_resolution: float = 10.0, terrain_stl_file: Optional[str] = None):
        """
        Create a base that uses terrain as the top surface
        
        Parameters:
        - base_bounds: Dict with 'x_min', 'x_max', 'y_min', 'y_max', 'z_min'
        - base_thickness: Thickness of base below terrain
        - grid_resolution: Resolution for sampling terrain (smaller = more detailed)
        - terrain_stl_file: Path to terrain STL file (if not already loaded)
        """
        
        if terrain_stl_file and not self.terrain_triangles:
            if not self.load_terrain_from_stl(terrain_stl_file):
                print("Failed to load terrain data, creating standard rectangular base")
                self._create_standard_base(base_bounds, base_thickness)
                return
        
        if not self.terrain_triangles:
            print("No terrain data available, creating standard rectangular base")
            self._create_standard_base(base_bounds, base_thickness)
            return
        
        print(f"Creating terrain-fitted base:")
        print(f"  Base bounds: X[{base_bounds['x_min']:.3f}, {base_bounds['x_max']:.3f}], "
              f"Y[{base_bounds['y_min']:.3f}, {base_bounds['y_max']:.3f}]")
        print(f"  Base thickness: {base_thickness:.3f}")
        print(f"  Grid resolution: {grid_resolution:.3f}")
        
        start_time = time.time()
        
        # Clear existing geometry
        self.triangles = []
        self.normals = []
        
        # Generate grid points
        x_range = np.arange(base_bounds['x_min'], base_bounds['x_max'] + grid_resolution, grid_resolution)
        y_range = np.arange(base_bounds['y_min'], base_bounds['y_max'] + grid_resolution, grid_resolution)
        
        print(f"  Grid size: {len(x_range)} x {len(y_range)} = {len(x_range) * len(y_range)} points")
        
        # Create height grid with progress tracking
        height_grid = {}
        points_with_terrain = 0
        total_points = len(x_range) * len(y_range)
        
        print("Sampling terrain heights...")
        for i, x in enumerate(x_range):
            if i % max(1, len(x_range) // 10) == 0:
                progress = (i * len(y_range)) / total_points * 100
                print(f"  Progress: {progress:.1f}%")
            
            for j, y in enumerate(y_range):
                terrain_z = self._get_terrain_height_at_point(x, y)
                if terrain_z is not None:
                    height_grid[(i, j)] = terrain_z
                    points_with_terrain += 1
                else:
                    # Use minimum Z if no terrain data at this point
                    height_grid[(i, j)] = base_bounds['z_min']
        
        sampling_time = time.time() - start_time
        print(f"Terrain sampling completed in {sampling_time:.2f} seconds")
        print(f"  Points with terrain data: {points_with_terrain}/{total_points}")
        
        print("Generating mesh...")
        mesh_start = time.time()
        
        # Generate triangles for terrain-fitted top surface
        for i in range(len(x_range) - 1):
            for j in range(len(y_range) - 1):
                x0, x1 = x_range[i], x_range[i + 1]
                y0, y1 = y_range[j], y_range[j + 1]
                
                # Get heights at four corners
                z00 = height_grid[(i, j)]
                z10 = height_grid[(i + 1, j)]
                z01 = height_grid[(i, j + 1)]
                z11 = height_grid[(i + 1, j + 1)]
                
                # Create two triangles for each grid cell (top surface)
                # Triangle 1: (x0,y0,z00) -> (x1,y0,z10) -> (x0,y1,z01)
                v1 = [x0, y0, z00]
                v2 = [x1, y0, z10]
                v3 = [x0, y1, z01]
                self._add_face([v1, v2, v3], [0, 0, 1])
                
                # Triangle 2: (x1,y0,z10) -> (x1,y1,z11) -> (x0,y1,z01)
                v1 = [x1, y0, z10]
                v2 = [x1, y1, z11]
                v3 = [x0, y1, z01]
                self._add_face([v1, v2, v3], [0, 0, 1])
                
                # Create bottom surface (flat at base_bounds['z_min'] - base_thickness)
                bottom_z = base_bounds['z_min'] - base_thickness
                
                # Bottom triangles (facing down)
                v1 = [x0, y0, bottom_z]
                v2 = [x0, y1, bottom_z]
                v3 = [x1, y0, bottom_z]
                self._add_face([v1, v2, v3], [0, 0, -1])
                
                v1 = [x1, y0, bottom_z]
                v2 = [x0, y1, bottom_z]
                v3 = [x1, y1, bottom_z]
                self._add_face([v1, v2, v3], [0, 0, -1])
        
        # Create side walls
        self._create_side_walls(x_range, y_range, height_grid, base_bounds['z_min'] - base_thickness)
        
        mesh_time = time.time() - mesh_start
        total_time = time.time() - start_time
        
        print(f"Mesh generation completed in {mesh_time:.2f} seconds")
        print(f"Total processing time: {total_time:.2f} seconds")
        print(f"Generated {len(self.triangles)} triangles for terrain-fitted base")
    
    def _create_side_walls(self, x_range: np.ndarray, y_range: np.ndarray, 
                          height_grid: Dict[Tuple[int, int], float], bottom_z: float):
        """Create vertical side walls for the base"""
        
        # Front wall (y = y_min)
        j = 0
        for i in range(len(x_range) - 1):
            x0, x1 = x_range[i], x_range[i + 1]
            y = y_range[j]
            z0 = height_grid[(i, j)]
            z1 = height_grid[(i + 1, j)]
            
            # Two triangles for wall segment
            self._add_face([[x0, y, bottom_z], [x0, y, z0], [x1, y, z1]], [0, -1, 0])
            self._add_face([[x0, y, bottom_z], [x1, y, z1], [x1, y, bottom_z]], [0, -1, 0])
        
        # Back wall (y = y_max)
        j = len(y_range) - 1
        for i in range(len(x_range) - 1):
            x0, x1 = x_range[i], x_range[i + 1]
            y = y_range[j]
            z0 = height_grid[(i, j)]
            z1 = height_grid[(i + 1, j)]
            
            # Two triangles for wall segment
            self._add_face([[x0, y, z0], [x0, y, bottom_z], [x1, y, bottom_z]], [0, 1, 0])
            self._add_face([[x0, y, z0], [x1, y, bottom_z], [x1, y, z1]], [0, 1, 0])
        
        # Left wall (x = x_min)
        i = 0
        for j in range(len(y_range) - 1):
            y0, y1 = y_range[j], y_range[j + 1]
            x = x_range[i]
            z0 = height_grid[(i, j)]
            z1 = height_grid[(i, j + 1)]
            
            # Two triangles for wall segment
            self._add_face([[x, y0, z0], [x, y0, bottom_z], [x, y1, bottom_z]], [-1, 0, 0])
            self._add_face([[x, y0, z0], [x, y1, bottom_z], [x, y1, z1]], [-1, 0, 0])
        
        # Right wall (x = x_max)
        i = len(x_range) - 1
        for j in range(len(y_range) - 1):
            y0, y1 = y_range[j], y_range[j + 1]
            x = x_range[i]
            z0 = height_grid[(i, j)]
            z1 = height_grid[(i, j + 1)]
            
            # Two triangles for wall segment
            self._add_face([[x, y0, bottom_z], [x, y0, z0], [x, y1, z1]], [1, 0, 0])
            self._add_face([[x, y0, bottom_z], [x, y1, z1], [x, y1, bottom_z]], [1, 0, 0])
    
    def _create_standard_base(self, base_bounds: Dict[str, float], base_thickness: float):
        """Create a standard rectangular base as fallback"""
        z_max = base_bounds.get('z_max', base_bounds['z_min'] + base_thickness)
        self.create_rectangular_base(
            base_bounds['x_min'], base_bounds['y_min'], base_bounds['z_min'] - base_thickness,
            base_bounds['x_max'], base_bounds['y_max'], z_max,
            use_offset=False
        )
    
    def create_rectangular_base(self, x_min: float, y_min: float, z_min: float,
                              x_max: float, y_max: float, z_max: float,
                              use_offset: bool = True):
        """Create a standard rectangular base (box) with the specified extents"""
        
        # Apply offset if requested
        if use_offset:
            x_min_world = x_min + self.offset[0]
            x_max_world = x_max + self.offset[0]
            y_min_world = y_min + self.offset[1]
            y_max_world = y_max + self.offset[1]
            
            print(f"Creating rectangular base with offset:")
            print(f"  Local coordinates:")
            print(f"    X range: {x_min:.3f} to {x_max:.3f} (width: {x_max-x_min:.3f})")
            print(f"    Y range: {y_min:.3f} to {y_max:.3f} (depth: {y_max-y_min:.3f})")
            print(f"    Z range: {z_min:.3f} to {z_max:.3f} (height: {z_max-z_min:.3f})")
            print(f"  World coordinates (with offset {self.offset}):")
            print(f"    X range: {x_min_world:.3f} to {x_max_world:.3f}")
            print(f"    Y range: {y_min_world:.3f} to {y_max_world:.3f}")
            print(f"    Z range: {z_min:.3f} to {z_max:.3f}")
            
            x_min, x_max = x_min_world, x_max_world
            y_min, y_max = y_min_world, y_max_world
            
        else:
            print(f"Creating rectangular base (no offset):")
            print(f"  X range: {x_min:.3f} to {x_max:.3f} (width: {x_max-x_min:.3f})")
            print(f"  Y range: {y_min:.3f} to {y_max:.3f} (depth: {y_max-y_min:.3f})")
            print(f"  Z range: {z_min:.3f} to {z_max:.3f} (height: {z_max-z_min:.3f})")
        
        # Define the 8 vertices of the rectangular box
        vertices = [
            [x_min, y_min, z_min],  # 0: bottom-front-left
            [x_max, y_min, z_min],  # 1: bottom-front-right
            [x_max, y_max, z_min],  # 2: bottom-back-right
            [x_min, y_max, z_min],  # 3: bottom-back-left
            [x_min, y_min, z_max],  # 4: top-front-left
            [x_max, y_min, z_max],  # 5: top-front-right
            [x_max, y_max, z_max],  # 6: top-back-right
            [x_min, y_max, z_max],  # 7: top-back-left
        ]
        
        # Clear any existing geometry
        self.triangles = []
        self.normals = []
        
        # Create all 6 faces of the box
        # Bottom face (Z = z_min)
        self._add_face([vertices[0], vertices[2], vertices[1]], [0, 0, -1])
        self._add_face([vertices[0], vertices[3], vertices[2]], [0, 0, -1])
        
        # Top face (Z = z_max)
        self._add_face([vertices[4], vertices[5], vertices[6]], [0, 0, 1])
        self._add_face([vertices[4], vertices[6], vertices[7]], [0, 0, 1])
        
        # Front face (Y = y_min)
        self._add_face([vertices[0], vertices[1], vertices[5]], [0, -1, 0])
        self._add_face([vertices[0], vertices[5], vertices[4]], [0, -1, 0])
        
        # Back face (Y = y_max)
        self._add_face([vertices[2], vertices[7], vertices[6]], [0, 1, 0])
        self._add_face([vertices[2], vertices[3], vertices[7]], [0, 1, 0])
        
        # Left face (X = x_min)
        self._add_face([vertices[0], vertices[4], vertices[7]], [-1, 0, 0])
        self._add_face([vertices[0], vertices[7], vertices[3]], [-1, 0, 0])
        
        # Right face (X = x_max)
        self._add_face([vertices[1], vertices[2], vertices[6]], [1, 0, 0])
        self._add_face([vertices[1], vertices[6], vertices[5]], [1, 0, 0])
        
        print(f"Generated {len(self.triangles)} triangles")
    
    def _add_face(self, vertices: List[List[float]], normal: List[float]):
        """Add a triangular face to the mesh"""
        self.triangles.append(vertices)
        self.normals.append(normal)
    
    def write_stl_binary(self, filename: str) -> bool:
        """Write binary STL file"""
        try:
            with open(filename, 'wb') as f:
                # Write header (80 bytes)
                header = b'Optimized terrain-fitted base STL' + b'\0' * (80 - 33)
                f.write(header)
                
                # Write number of triangles
                f.write(struct.pack('<I', len(self.triangles)))
                
                # Write triangles
                for i, triangle in enumerate(self.triangles):
                    # Write normal
                    normal = self.normals[i]
                    f.write(struct.pack('<3f', *normal))
                    
                    # Write vertices
                    for vertex in triangle:
                        f.write(struct.pack('<3f', *vertex))
                    
                    # Write attribute byte count (0)
                    f.write(struct.pack('<H', 0))
            
            return True
        except Exception as e:
            print(f"Error writing binary STL: {e}")
            return False
    
    def write_stl_ascii(self, filename: str) -> bool:
        """Write ASCII STL file"""
        try:
            with open(filename, 'w') as f:
                f.write("solid optimized_terrain_fitted_base\n")
                
                for i, triangle in enumerate(self.triangles):
                    normal = self.normals[i]
                    f.write(f"  facet normal {normal[0]:.6f} {normal[1]:.6f} {normal[2]:.6f}\n")
                    f.write("    outer loop\n")
                    
                    for vertex in triangle:
                        f.write(f"      vertex {vertex[0]:.6f} {vertex[1]:.6f} {vertex[2]:.6f}\n")
                    
                    f.write("    endloop\n")
                    f.write("  endfacet\n")
                
                f.write("endsolid optimized_terrain_fitted_base\n")
            
            return True
        except Exception as e:
            print(f"Error writing ASCII STL: {e}")
            return False

def main():
    # =============================================================================
    # CONFIGURATION - Set these values for your terrain-fitted base
    # =============================================================================
    
    # Method selection
    USE_TERRAIN_FITTED_BASE = True          # Set to True to create terrain-fitted base
    
    # Terrain STL file (your terrain mesh)
    TERRAIN_STL_FILE = "windAroundBuildings/Tools/output/terrainKilbourn_clipped.stl"   # Path to your terrain STL file
    
    # Your terrain data bounds (from your output)
    TERRAIN_BOUNDS = {
        'x_min': -352.895,   # np.float64(-352.89520972478203)
        'x_max': 350.988,    # np.float64(350.9880754571059)  
        'y_min': -302.330,   # np.float64(-302.33025516569614)
        'y_max': 306.979,    # np.float64(306.9790263324976)
        'z_min': 630.338,    # np.float64(630.3375607466452)
        'z_max': 704.983     # np.float64(704.9825786398455)
    }
    
    # Your coordinate offset (from your output)
    COORDINATE_OFFSET = (424265.04, 4765565.05)
    
    # Base configuration for terrain-fitted method
    BASE_THICKNESS = 20.0           # How thick the base should be below terrain
    BASE_MARGIN = 50.0              # Extra margin around terrain bounds
    GRID_RESOLUTION = 10.0          # Grid resolution for sampling terrain (start larger for testing)
    
    # Standard rectangular base settings (fallback)
    BASE_EXTENTS = [-400, -350, 560, 400, 350, 580]
    
    # Output settings
    OUTPUT_FILE = "windAroundBuildings/Tools/output/wRaster/basewTerrainFast.stl"
    OUTPUT_ASCII = False
    
    # =============================================================================
    # END CONFIGURATION
    # =============================================================================
    
    print("Starting optimized terrain-fitted base generation...")
    start_time = time.time()
    
    # Create generator instance
    generator = OptimizedRectangularBaseGenerator()
    
    # Set coordinate offset
    generator.set_offset(COORDINATE_OFFSET[0], COORDINATE_OFFSET[1])
    
    if USE_TERRAIN_FITTED_BASE:
        # Create base bounds with margin
        base_bounds = {
            'x_min': TERRAIN_BOUNDS['x_min'] - BASE_MARGIN,
            'x_max': TERRAIN_BOUNDS['x_max'] + BASE_MARGIN,
            'y_min': TERRAIN_BOUNDS['y_min'] - BASE_MARGIN,
            'y_max': TERRAIN_BOUNDS['y_max'] + BASE_MARGIN,
            'z_min': TERRAIN_BOUNDS['z_min'],
            'z_max': TERRAIN_BOUNDS['z_max']
        }
        
        # Create terrain-fitted base
        generator.create_terrain_fitted_base(
            base_bounds,
            base_thickness=BASE_THICKNESS,
            grid_resolution=GRID_RESOLUTION,
            terrain_stl_file=TERRAIN_STL_FILE
        )
        
        # Calculate volume estimate
        base_area = ((base_bounds['x_max'] - base_bounds['x_min']) * 
                    (base_bounds['y_max'] - base_bounds['y_min']))
        volume_estimate = base_area * BASE_THICKNESS
        
        print(f"\nTerrain-fitted base statistics:")
        print(f"  Base area: {base_area:.3f} square units")
        print(f"  Estimated volume: {volume_estimate:.3f} cubic units")
        print(f"  Grid resolution: {GRID_RESOLUTION} units")
        
    else:
        # Create standard rectangular base
        if len(BASE_EXTENTS) != 6:
            print("Error: BASE_EXTENTS must contain exactly 6 values")
            return 1
        
        x_min, y_min, z_min, x_max, y_max, z_max = BASE_EXTENTS
        generator.create_rectangular_base(x_min, y_min, z_min, x_max, y_max, z_max)
    
    # Write output file
    print(f"\nWriting output file...")
    if OUTPUT_ASCII:
        success = generator.write_stl_ascii(OUTPUT_FILE)
        format_str = "ASCII"
    else:
        success = generator.write_stl_binary(OUTPUT_FILE)
        format_str = "binary"
    
    total_time = time.time() - start_time
    
    if success:
        print(f"\nSuccessfully wrote {format_str} STL file: {OUTPUT_FILE}")
        
        # Show file size
        file_size = os.path.getsize(OUTPUT_FILE)
        if file_size < 1024:
            size_str = f"{file_size} bytes"
        elif file_size < 1024*1024:
            size_str = f"{file_size/1024:.1f} KB"
        else:
            size_str = f"{file_size/(1024*1024):.1f} MB"
        
        print(f"File size: {size_str}")
        print(f"Triangles generated: {len(generator.triangles)}")
        
        if USE_TERRAIN_FITTED_BASE:
            print(f"\nTerrain-fitted base created:")
            print(f"  Uses terrain surface as top of base")
            print(f"  Base extends {BASE_THICKNESS} units below terrain minimum")
            print(f"  Coordinate system: EPSG:32616 with offset {COORDINATE_OFFSET}")
            print(f"  Compatible with terrain file: {TERRAIN_STL_FILE}")
        
        return 0
    else:
        print("Failed to write output file")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())