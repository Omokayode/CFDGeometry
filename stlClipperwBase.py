#!/usr/bin/env python3
"""
STL Clipping Tool with Boundary Walls
Clips an STL file to a user-defined bounding box region and adds boundary walls and base.
"""
import numpy as np
import struct
import os
from typing import Tuple, List

class STLClipper:
    def __init__(self):
        self.vertices = []
        self.normals = []
        self.triangles = []
    
    def read_stl_ascii(self, filename: str) -> bool:
        """Read ASCII STL file"""
        try:
            with open(filename, 'r') as f:
                lines = f.readlines()
            
            i = 0
            while i < len(lines):
                line = lines[i].strip().lower()
                if line.startswith('facet normal'):
                    # Parse normal vector
                    normal = [float(x) for x in line.split()[2:5]]
                    
                    # Skip 'outer loop'
                    i += 2
                    
                    # Read three vertices
                    triangle_vertices = []
                    for _ in range(3):
                        vertex_line = lines[i].strip().lower()
                        if vertex_line.startswith('vertex'):
                            vertex = [float(x) for x in vertex_line.split()[1:4]]
                            triangle_vertices.append(vertex)
                        i += 1
                    
                    if len(triangle_vertices) == 3:
                        self.triangles.append(triangle_vertices)
                        self.normals.append(normal)
                    
                    # Skip 'endloop' and 'endfacet'
                    i += 2
                else:
                    i += 1
            
            return True
        except Exception as e:
            print(f"Error reading ASCII STL: {e}")
            return False
    
    def read_stl_binary(self, filename: str) -> bool:
        """Read binary STL file"""
        try:
            with open(filename, 'rb') as f:
                # Skip header (80 bytes)
                f.read(80)
                
                # Read number of triangles
                num_triangles = struct.unpack('<I', f.read(4))[0]
                
                for _ in range(num_triangles):
                    # Read normal (3 floats)
                    normal = struct.unpack('<3f', f.read(12))
                    
                    # Read three vertices (9 floats total)
                    triangle_vertices = []
                    for _ in range(3):
                        vertex = struct.unpack('<3f', f.read(12))
                        triangle_vertices.append(list(vertex))
                    
                    # Skip attribute byte count
                    f.read(2)
                    
                    self.triangles.append(triangle_vertices)
                    self.normals.append(list(normal))
            
            return True
        except Exception as e:
            print(f"Error reading binary STL: {e}")
            return False
    
    def is_binary_stl(self, filename: str) -> bool:
        """Check if STL file is binary format"""
        try:
            with open(filename, 'rb') as f:
                # Read first 80 bytes (header)
                header = f.read(80)
                
                # Check if it starts with 'solid' (might be ASCII)
                if header.startswith(b'solid'):
                    # Read a bit more to see if it looks like ASCII
                    sample = f.read(200).decode('ascii', errors='ignore')
                    return 'facet normal' not in sample.lower()
                else:
                    return True
        except:
            return False
    
    def read_stl(self, filename: str) -> bool:
        """Read STL file (auto-detect format)"""
        if not os.path.exists(filename):
            print(f"File not found: {filename}")
            return False
        
        if self.is_binary_stl(filename):
            print("Reading binary STL file...")
            return self.read_stl_binary(filename)
        else:
            print("Reading ASCII STL file...")
            return self.read_stl_ascii(filename)
    
    def get_bounds(self) -> Tuple[np.ndarray, np.ndarray]:
        """Get the bounding box of the current model"""
        if not self.triangles:
            return np.array([0, 0, 0]), np.array([0, 0, 0])
        
        all_vertices = []
        for triangle in self.triangles:
            all_vertices.extend(triangle)
        
        vertices_array = np.array(all_vertices)
        min_bounds = np.min(vertices_array, axis=0)
        max_bounds = np.max(vertices_array, axis=0)
        
        return min_bounds, max_bounds
    
    def point_in_bounds(self, point: List[float], min_bounds: np.ndarray, max_bounds: np.ndarray) -> bool:
        """Check if a point is within the clipping bounds"""
        p = np.array(point)
        return np.all(p >= min_bounds) and np.all(p <= max_bounds)
    
    def triangle_intersects_bounds(self, triangle: List[List[float]], min_bounds: np.ndarray, max_bounds: np.ndarray) -> bool:
        """Check if a triangle intersects with the clipping bounds"""
        # Simple check: if any vertex is inside bounds, keep the triangle
        # For more sophisticated clipping, would need to implement triangle-box intersection
        for vertex in triangle:
            if self.point_in_bounds(vertex, min_bounds, max_bounds):
                return True
        
        # Also check if the bounding box is entirely within the triangle's bounds
        triangle_array = np.array(triangle)
        tri_min = np.min(triangle_array, axis=0)
        tri_max = np.max(triangle_array, axis=0)
        
        # Check if clipping box is entirely within triangle bounds
        if (np.all(min_bounds >= tri_min) and np.all(max_bounds <= tri_max)):
            return True
        
        return False
    
    def clip_to_bounds(self, min_bounds: np.ndarray, max_bounds: np.ndarray) -> None:
        """Clip the model to the specified bounds"""
        clipped_triangles = []
        clipped_normals = []
        
        for i, triangle in enumerate(self.triangles):
            if self.triangle_intersects_bounds(triangle, min_bounds, max_bounds):
                clipped_triangles.append(triangle)
                clipped_normals.append(self.normals[i])
        
        self.triangles = clipped_triangles
        self.normals = clipped_normals
        
        print(f"Clipped to {len(self.triangles)} triangles")
    
    def add_boundary_walls(self, min_bounds: np.ndarray, max_bounds: np.ndarray, wall_thickness: float = 1.0, base_thickness: float = 2.0):
        """Add boundary walls and base around the clipped region"""
        
        # Get the actual bounds including wall thickness
        wall_min = min_bounds - wall_thickness
        wall_max = max_bounds + wall_thickness
        base_z = min_bounds[2] - base_thickness
        
        print(f"Adding boundary walls with thickness {wall_thickness}")
        print(f"Adding base with thickness {base_thickness}")
        
        # Add base (bottom face)
        self._add_base_face(wall_min, wall_max, base_z)
        
        # Add four side walls
        self._add_wall_face(wall_min, wall_max, min_bounds, max_bounds, 'front', base_z)   # Y-min wall
        self._add_wall_face(wall_min, wall_max, min_bounds, max_bounds, 'back', base_z)    # Y-max wall
        self._add_wall_face(wall_min, wall_max, min_bounds, max_bounds, 'left', base_z)    # X-min wall
        self._add_wall_face(wall_min, wall_max, min_bounds, max_bounds, 'right', base_z)   # X-max wall
    
    def _add_base_face(self, wall_min: np.ndarray, wall_max: np.ndarray, base_z: float):
        """Add base rectangle at the bottom"""
        # Create two triangles for the base
        # Triangle 1
        v1 = [wall_min[0], wall_min[1], base_z]
        v2 = [wall_max[0], wall_min[1], base_z]
        v3 = [wall_max[0], wall_max[1], base_z]
        normal = [0, 0, 1]  # Normal pointing up
        
        self.triangles.append([v1, v2, v3])
        self.normals.append(normal)
        
        # Triangle 2
        v4 = [wall_min[0], wall_max[1], base_z]
        self.triangles.append([v1, v3, v4])
        self.normals.append(normal)
    
    def _add_wall_face(self, wall_min: np.ndarray, wall_max: np.ndarray, 
                      inner_min: np.ndarray, inner_max: np.ndarray, 
                      wall_side: str, base_z: float):
        """Add a wall face on the specified side"""
        
        if wall_side == 'front':  # Y-min wall
            # Outer edge of wall
            outer_y = wall_min[1]
            inner_y = inner_min[1]
            
            # Bottom face of wall
            v1 = [wall_min[0], outer_y, base_z]
            v2 = [wall_max[0], outer_y, base_z]
            v3 = [wall_max[0], inner_y, base_z]
            v4 = [wall_min[0], inner_y, base_z]
            
            # Top face of wall
            v5 = [wall_min[0], outer_y, wall_max[2]]
            v6 = [wall_max[0], outer_y, wall_max[2]]
            v7 = [wall_max[0], inner_y, wall_max[2]]
            v8 = [wall_min[0], inner_y, wall_max[2]]
            
            # Outer face (facing outward)
            normal_outer = [0, -1, 0]
            self._add_rectangle_triangles(v1, v2, v6, v5, normal_outer)
            
            # Inner face (facing inward)
            normal_inner = [0, 1, 0]
            self._add_rectangle_triangles(v4, v8, v7, v3, normal_inner)
            
            # Top face
            normal_top = [0, 0, 1]
            self._add_rectangle_triangles(v5, v6, v7, v8, normal_top)
            
            # Left side face
            normal_left = [-1, 0, 0]
            self._add_rectangle_triangles(v1, v5, v8, v4, normal_left)
            
            # Right side face
            normal_right = [1, 0, 0]
            self._add_rectangle_triangles(v2, v3, v7, v6, normal_right)
            
        elif wall_side == 'back':  # Y-max wall
            outer_y = wall_max[1]
            inner_y = inner_max[1]
            
            v1 = [wall_min[0], inner_y, base_z]
            v2 = [wall_max[0], inner_y, base_z]
            v3 = [wall_max[0], outer_y, base_z]
            v4 = [wall_min[0], outer_y, base_z]
            
            v5 = [wall_min[0], inner_y, wall_max[2]]
            v6 = [wall_max[0], inner_y, wall_max[2]]
            v7 = [wall_max[0], outer_y, wall_max[2]]
            v8 = [wall_min[0], outer_y, wall_max[2]]
            
            # Outer face
            normal_outer = [0, 1, 0]
            self._add_rectangle_triangles(v3, v4, v8, v7, normal_outer)
            
            # Inner face
            normal_inner = [0, -1, 0]
            self._add_rectangle_triangles(v1, v5, v6, v2, normal_inner)
            
            # Top face
            normal_top = [0, 0, 1]
            self._add_rectangle_triangles(v5, v6, v7, v8, normal_top)
            
            # Left side face
            normal_left = [-1, 0, 0]
            self._add_rectangle_triangles(v4, v8, v5, v1, normal_left)
            
            # Right side face
            normal_right = [1, 0, 0]
            self._add_rectangle_triangles(v2, v6, v7, v3, normal_right)
            
        elif wall_side == 'left':  # X-min wall
            outer_x = wall_min[0]
            inner_x = inner_min[0]
            
            v1 = [outer_x, wall_min[1], base_z]
            v2 = [inner_x, wall_min[1], base_z]
            v3 = [inner_x, wall_max[1], base_z]
            v4 = [outer_x, wall_max[1], base_z]
            
            v5 = [outer_x, wall_min[1], wall_max[2]]
            v6 = [inner_x, wall_min[1], wall_max[2]]
            v7 = [inner_x, wall_max[1], wall_max[2]]
            v8 = [outer_x, wall_max[1], wall_max[2]]
            
            # Outer face
            normal_outer = [-1, 0, 0]
            self._add_rectangle_triangles(v1, v4, v8, v5, normal_outer)
            
            # Inner face
            normal_inner = [1, 0, 0]
            self._add_rectangle_triangles(v2, v6, v7, v3, normal_inner)
            
            # Top face
            normal_top = [0, 0, 1]
            self._add_rectangle_triangles(v5, v6, v7, v8, normal_top)
            
            # Front side face
            normal_front = [0, -1, 0]
            self._add_rectangle_triangles(v1, v5, v6, v2, normal_front)
            
            # Back side face
            normal_back = [0, 1, 0]
            self._add_rectangle_triangles(v3, v7, v8, v4, normal_back)
            
        elif wall_side == 'right':  # X-max wall
            outer_x = wall_max[0]
            inner_x = inner_max[0]
            
            v1 = [inner_x, wall_min[1], base_z]
            v2 = [outer_x, wall_min[1], base_z]
            v3 = [outer_x, wall_max[1], base_z]
            v4 = [inner_x, wall_max[1], base_z]
            
            v5 = [inner_x, wall_min[1], wall_max[2]]
            v6 = [outer_x, wall_min[1], wall_max[2]]
            v7 = [outer_x, wall_max[1], wall_max[2]]
            v8 = [inner_x, wall_max[1], wall_max[2]]
            
            # Outer face
            normal_outer = [1, 0, 0]
            self._add_rectangle_triangles(v2, v6, v7, v3, normal_outer)
            
            # Inner face
            normal_inner = [-1, 0, 0]
            self._add_rectangle_triangles(v1, v4, v8, v5, normal_inner)
            
            # Top face
            normal_top = [0, 0, 1]
            self._add_rectangle_triangles(v5, v6, v7, v8, normal_top)
            
            # Front side face
            normal_front = [0, -1, 0]
            self._add_rectangle_triangles(v2, v6, v5, v1, normal_front)
            
            # Back side face
            normal_back = [0, 1, 0]
            self._add_rectangle_triangles(v4, v8, v7, v3, normal_back)
    
    def _add_rectangle_triangles(self, v1: List[float], v2: List[float], 
                               v3: List[float], v4: List[float], normal: List[float]):
        """Add two triangles to form a rectangle"""
        # Triangle 1: v1, v2, v3
        self.triangles.append([v1, v2, v3])
        self.normals.append(normal)
        
        # Triangle 2: v1, v3, v4
        self.triangles.append([v1, v3, v4])
        self.normals.append(normal)
    
    def write_stl_binary(self, filename: str) -> bool:
        """Write binary STL file"""
        try:
            with open(filename, 'wb') as f:
                # Write header (80 bytes)
                header = b'STL clipped file with walls' + b'\0' * (80 - 27)
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
            print(f"Error writing STL: {e}")
            return False
    
    def write_stl_ascii(self, filename: str) -> bool:
        """Write ASCII STL file"""
        try:
            with open(filename, 'w') as f:
                f.write("solid clipped_model_with_walls\n")
                
                for i, triangle in enumerate(self.triangles):
                    normal = self.normals[i]
                    f.write(f"  facet normal {normal[0]:.6f} {normal[1]:.6f} {normal[2]:.6f}\n")
                    f.write("    outer loop\n")
                    
                    for vertex in triangle:
                        f.write(f"      vertex {vertex[0]:.6f} {vertex[1]:.6f} {vertex[2]:.6f}\n")
                    
                    f.write("    endloop\n")
                    f.write("  endfacet\n")
                
                f.write("endsolid clipped_model_with_walls\n")
            
            return True
        except Exception as e:
            print(f"Error writing ASCII STL: {e}")
            return False

def main():
    # =============================================================================
    # CONFIGURATION - Edit these values as needed
    # =============================================================================
    
    # File paths
    # INPUT_FILE = "output/terrainKilbourn.stl"
    # OUTPUT_FILE = "output/basewTerrainClippedPrint.stl"
    

    # Clipping bounds: [xmin, ymin, zmin, xmax, ymax, zmax]
    # CLIP_BOUNDS = [-352.90, -302.33, 600, 350.99, 306.98, 670.98]

    INPUT_FILE = "/mnt/nas/vsCode/resources/urbanWindFlow/Tools/output/terrainSimplification/terrain_Marquette_conservative_fixed.stl"
    OUTPUT_FILE = "/mnt/nas/vsCode/resources/urbanWindFlow/Tools/output/terrain_Marquette_conservative_fixed_clipped_base.stl"

    CLIP_BOUNDS = [-500, -500, 300, 500, 500, 720]
    # Boundary wall options
    ADD_BOUNDARY_WALLS = True               # Set to True to add boundary walls and base
    WALL_THICKNESS = 5.0                    # Thickness of boundary walls
    BASE_THICKNESS = 10.0                   # Thickness of base underneath model
    
    # Output options
    OUTPUT_ASCII = False                    # Set to True for ASCII STL output
    SHOW_ORIGINAL_BOUNDS = True             # Set to True to display original model bounds
    
    # =============================================================================
    # END CONFIGURATION
    # =============================================================================
    
    # Create clipper instance
    clipper = STLClipper()
    
    # Check if input file exists
    if not os.path.exists(INPUT_FILE):
        print(f"Error: Input file not found: {INPUT_FILE}")
        print("Please update the INPUT_FILE path in the configuration section.")
        return 1
    
    # Read input file
    if not clipper.read_stl(INPUT_FILE):
        print("Failed to read input STL file")
        return 1
    
    print(f"Loaded {len(clipper.triangles)} triangles from {INPUT_FILE}")
    
    # Show original bounds if requested
    if SHOW_ORIGINAL_BOUNDS:
        min_bounds, max_bounds = clipper.get_bounds()
        print(f"Original model bounds:")
        print(f"  Min: [{min_bounds[0]:.3f}, {min_bounds[1]:.3f}, {min_bounds[2]:.3f}]")
        print(f"  Max: [{max_bounds[0]:.3f}, {max_bounds[1]:.3f}, {max_bounds[2]:.3f}]")
        print(f"  Size: [{max_bounds[0]-min_bounds[0]:.3f}, {max_bounds[1]-min_bounds[1]:.3f}, {max_bounds[2]-min_bounds[2]:.3f}]")
    
    # Set clipping bounds
    if len(CLIP_BOUNDS) != 6:
        print("Error: CLIP_BOUNDS must contain exactly 6 values [xmin, ymin, zmin, xmax, ymax, zmax]")
        return 1
    
    clip_min = np.array(CLIP_BOUNDS[:3])
    clip_max = np.array(CLIP_BOUNDS[3:])
    
    print(f"\nClipping to bounds:")
    print(f"  Min: [{clip_min[0]:.3f}, {clip_min[1]:.3f}, {clip_min[2]:.3f}]")
    print(f"  Max: [{clip_max[0]:.3f}, {clip_max[1]:.3f}, {clip_max[2]:.3f}]")
    print(f"  Size: [{clip_max[0]-clip_min[0]:.3f}, {clip_max[1]-clip_min[1]:.3f}, {clip_max[2]-clip_min[2]:.3f}]")
    
    # Perform clipping
    original_count = len(clipper.triangles)
    clipper.clip_to_bounds(clip_min, clip_max)
    
    if len(clipper.triangles) == 0:
        print("Warning: No triangles remain after clipping!")
        print("Check that your clipping bounds intersect with the model.")
        return 1
    
    print(f"Clipping complete: {original_count} -> {len(clipper.triangles)} triangles ({len(clipper.triangles)/original_count*100:.1f}% retained)")
    
    # Add boundary walls if requested
    if ADD_BOUNDARY_WALLS:
        triangles_before_walls = len(clipper.triangles)
        clipper.add_boundary_walls(clip_min, clip_max, WALL_THICKNESS, BASE_THICKNESS)
        wall_triangles = len(clipper.triangles) - triangles_before_walls
        print(f"Added {wall_triangles} triangles for boundary walls and base")
        print(f"Total triangles: {len(clipper.triangles)}")
    
    # Write output file
    if OUTPUT_ASCII:
        success = clipper.write_stl_ascii(OUTPUT_FILE)
        format_str = "ASCII"
    else:
        success = clipper.write_stl_binary(OUTPUT_FILE)
        format_str = "binary"
    
    if success:
        wall_str = " with boundary walls" if ADD_BOUNDARY_WALLS else ""
        print(f"Successfully wrote clipped {format_str} STL{wall_str} to {OUTPUT_FILE}")
        return 0
    else:
        print("Failed to write output file")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())