#!/usr/bin/env python3
"""
Rectangular Base STL Generator with Offset Support
Creates a rectangular base/platform as an STL file with configurable dimensions and offset handling.
"""
import numpy as np
import struct
import os
from typing import List, Tuple, Optional

class RectangularBaseGenerator:
    def __init__(self):
        self.triangles = []
        self.normals = []
        self.offset = (0.0, 0.0)
    
    def set_offset(self, offset_x: float, offset_y: float):
        """Set the coordinate offset to match terrain data"""
        self.offset = (offset_x, offset_y)
        print(f"Set coordinate offset: ({offset_x}, {offset_y})")
    
    def create_rectangular_base(self, x_min: float, y_min: float, z_min: float,
                              x_max: float, y_max: float, z_max: float,
                              use_offset: bool = True):
        """
        Create a rectangular base (box) with the specified extents
        
        Parameters:
        - x_min, y_min, z_min: Minimum coordinates (in local coordinate system)
        - x_max, y_max, z_max: Maximum coordinates (in local coordinate system)
        - use_offset: Whether to apply the coordinate offset
        """
        
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
            
            # Use world coordinates for the actual geometry
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
        self._add_face([vertices[0], vertices[2], vertices[1]], [0, 0, -1])  # Triangle 1
        self._add_face([vertices[0], vertices[3], vertices[2]], [0, 0, -1])  # Triangle 2
        
        # Top face (Z = z_max)
        self._add_face([vertices[4], vertices[5], vertices[6]], [0, 0, 1])   # Triangle 1
        self._add_face([vertices[4], vertices[6], vertices[7]], [0, 0, 1])   # Triangle 2
        
        # Front face (Y = y_min)
        self._add_face([vertices[0], vertices[1], vertices[5]], [0, -1, 0])  # Triangle 1
        self._add_face([vertices[0], vertices[5], vertices[4]], [0, -1, 0])  # Triangle 2
        
        # Back face (Y = y_max)
        self._add_face([vertices[2], vertices[7], vertices[6]], [0, 1, 0])   # Triangle 1
        self._add_face([vertices[2], vertices[3], vertices[7]], [0, 1, 0])   # Triangle 2
        
        # Left face (X = x_min)
        self._add_face([vertices[0], vertices[4], vertices[7]], [-1, 0, 0])  # Triangle 1
        self._add_face([vertices[0], vertices[7], vertices[3]], [-1, 0, 0])  # Triangle 2
        
        # Right face (X = x_max)
        self._add_face([vertices[1], vertices[2], vertices[6]], [1, 0, 0])   # Triangle 1
        self._add_face([vertices[1], vertices[6], vertices[5]], [1, 0, 0])   # Triangle 2
        
        print(f"Generated {len(self.triangles)} triangles")
    
    def create_base_for_terrain_bounds(self, terrain_bounds: dict, base_thickness: float = 20.0, 
                                     margin: float = 50.0, base_offset_z: float = -10.0):
        """
        Create a rectangular base that fits terrain bounds
        
        Parameters:
        - terrain_bounds: Dict with keys 'x_min', 'x_max', 'y_min', 'y_max', 'z_min', 'z_max'
        - base_thickness: Thickness of the base in Z direction
        - margin: Extra margin around terrain bounds
        - base_offset_z: Offset below terrain minimum (negative for below)
        """
        
        # Calculate base extents with margin
        x_min = terrain_bounds['x_min'] - margin
        x_max = terrain_bounds['x_max'] + margin
        y_min = terrain_bounds['y_min'] - margin
        y_max = terrain_bounds['y_max'] + margin
        
        # Position base below terrain
        z_min = terrain_bounds['z_min'] + base_offset_z
        z_max = z_min + base_thickness
        
        print(f"Creating base for terrain bounds:")
        print(f"  Terrain bounds: X[{terrain_bounds['x_min']:.3f}, {terrain_bounds['x_max']:.3f}], "
              f"Y[{terrain_bounds['y_min']:.3f}, {terrain_bounds['y_max']:.3f}], "
              f"Z[{terrain_bounds['z_min']:.3f}, {terrain_bounds['z_max']:.3f}]")
        print(f"  Base margin: {margin:.3f}")
        print(f"  Base thickness: {base_thickness:.3f}")
        print(f"  Base Z offset: {base_offset_z:.3f}")
        
        # Create the base (offset is applied automatically if set)
        self.create_rectangular_base(x_min, y_min, z_min, x_max, y_max, z_max, use_offset=False)
    
    def _add_face(self, vertices: List[List[float]], normal: List[float]):
        """Add a triangular face to the mesh"""
        self.triangles.append(vertices)
        self.normals.append(normal)
    
    def write_stl_binary(self, filename: str) -> bool:
        """Write binary STL file"""
        try:
            with open(filename, 'wb') as f:
                # Write header (80 bytes)
                header = b'Rectangular base STL file' + b'\0' * (80 - 25)
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
                f.write("solid rectangular_base\n")
                
                for i, triangle in enumerate(self.triangles):
                    normal = self.normals[i]
                    f.write(f"  facet normal {normal[0]:.6f} {normal[1]:.6f} {normal[2]:.6f}\n")
                    f.write("    outer loop\n")
                    
                    for vertex in triangle:
                        f.write(f"      vertex {vertex[0]:.6f} {vertex[1]:.6f} {vertex[2]:.6f}\n")
                    
                    f.write("    endloop\n")
                    f.write("  endfacet\n")
                
                f.write("endsolid rectangular_base\n")
            
            return True
        except Exception as e:
            print(f"Error writing ASCII STL: {e}")
            return False

def main():
    # =============================================================================
    # CONFIGURATION - Edit these values to define your rectangular base
    # =============================================================================
    
    # Method 1: Use terrain bounds (recommended for your use case)
    USE_TERRAIN_BOUNDS = True
    
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
    
    # Base settings for terrain bounds method
    BASE_THICKNESS = 5.0      # Thickness of base platform
    BASE_MARGIN = 50.0         # Extra margin around terrain
    BASE_Z_OFFSET = -10.0      # How far below terrain minimum (negative = below)
    
    # Method 2: Manual extents (alternative method)
    BASE_EXTENTS = [-400, -350, 560, 400, 350, 580]  # [x_min, y_min, z_min, x_max, y_max, z_max]
    
    # Method 3: Center point and dimensions
    USE_CENTER_AND_SIZE = False             # Set to True to use center/size method instead
    CENTER_POINT = [0, 0, 570]             # [x_center, y_center, z_center]
    DIMENSIONS = [800, 700, 20]             # [width, depth, height]
    
    # Output file settings
    OUTPUT_FILE = "windAroundBuildings/Tools/output/base.stl"   # Output STL filename
    OUTPUT_ASCII = False                                # Set to True for ASCII STL format
    
    # =============================================================================
    # END CONFIGURATION
    # =============================================================================
    
    # Create generator instance
    generator = RectangularBaseGenerator()
    
    # Set coordinate offset
    generator.set_offset(COORDINATE_OFFSET[0], COORDINATE_OFFSET[1])
    
    if USE_TERRAIN_BOUNDS:
        # Method 1: Create base to fit terrain bounds
        generator.create_base_for_terrain_bounds(
            TERRAIN_BOUNDS, 
            base_thickness=BASE_THICKNESS,
            margin=BASE_MARGIN,
            base_offset_z=BASE_Z_OFFSET
        )
        
        # Calculate actual extents for volume calculation
        x_min = TERRAIN_BOUNDS['x_min'] - BASE_MARGIN
        x_max = TERRAIN_BOUNDS['x_max'] + BASE_MARGIN  
        y_min = TERRAIN_BOUNDS['y_min'] - BASE_MARGIN
        y_max = TERRAIN_BOUNDS['y_max'] + BASE_MARGIN
        z_min = TERRAIN_BOUNDS['z_min'] + BASE_Z_OFFSET
        z_max = z_min + BASE_THICKNESS
        
    elif USE_CENTER_AND_SIZE:
        # Method 2: Calculate extents from center point and dimensions
        half_width = DIMENSIONS[0] / 2
        half_depth = DIMENSIONS[1] / 2
        half_height = DIMENSIONS[2] / 2
        
        x_min = CENTER_POINT[0] - half_width
        x_max = CENTER_POINT[0] + half_width
        y_min = CENTER_POINT[1] - half_depth
        y_max = CENTER_POINT[1] + half_depth
        z_min = CENTER_POINT[2] - half_height
        z_max = CENTER_POINT[2] + half_height
        
        print("Using center point and dimensions method:")
        print(f"  Center: [{CENTER_POINT[0]}, {CENTER_POINT[1]}, {CENTER_POINT[2]}]")
        print(f"  Dimensions: [{DIMENSIONS[0]}, {DIMENSIONS[1]}, {DIMENSIONS[2]}]")
        
        generator.create_rectangular_base(x_min, y_min, z_min, x_max, y_max, z_max)
        
    else:
        # Method 3: Use direct extents
        if len(BASE_EXTENTS) != 6:
            print("Error: BASE_EXTENTS must contain exactly 6 values [x_min, y_min, z_min, x_max, y_max, z_max]")
            return 1
        
        x_min, y_min, z_min, x_max, y_max, z_max = BASE_EXTENTS
        print("Using direct extents method:")
        
        generator.create_rectangular_base(x_min, y_min, z_min, x_max, y_max, z_max)
    
    # Validate extents
    if x_max <= x_min or y_max <= y_min or z_max <= z_min:
        print("Error: Invalid extents - max values must be greater than min values")
        return 1
    
    # Calculate volume and surface area for reference
    volume = (x_max - x_min) * (y_max - y_min) * (z_max - z_min)
    surface_area = 2 * ((x_max - x_min) * (y_max - y_min) + 
                       (x_max - x_min) * (z_max - z_min) + 
                       (y_max - y_min) * (z_max - z_min))
    
    print(f"  Volume: {volume:.3f} cubic units")
    print(f"  Surface area: {surface_area:.3f} square units")
    
    # Write output file
    if OUTPUT_ASCII:
        success = generator.write_stl_ascii(OUTPUT_FILE)
        format_str = "ASCII"
    else:
        success = generator.write_stl_binary(OUTPUT_FILE)
        format_str = "binary"
    
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
        
        print(f"\nBase positioned to support terrain:")
        print(f"  Terrain elevation range: {TERRAIN_BOUNDS['z_min']:.3f} to {TERRAIN_BOUNDS['z_max']:.3f}")
        print(f"  Base elevation range: {z_min:.3f} to {z_max:.3f}")
        print(f"  Coordinate system: EPSG:32616 with offset {COORDINATE_OFFSET}")
        
        return 0
    else:
        print("Failed to write output file")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())