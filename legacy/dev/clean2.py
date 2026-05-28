import numpy as np
from collections import defaultdict
import struct

class STLCleaner:
    def __init__(self, tolerance=1e-6):
        """
        Initialize STL cleaner with specified tolerance for vertex merging.
        
        Args:
            tolerance (float): Distance threshold for considering vertices as duplicates
        """
        self.tolerance = tolerance
        self.vertices = []
        self.triangles = []
        self.normals = []
    
    def read_stl_ascii(self, filename):
        """Read ASCII STL file and extract vertices and triangles."""
        vertices = []
        triangles = []
        normals = []
        
        with open(filename, 'r') as f:
            lines = f.readlines()
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if line.startswith('facet normal'):
                # Extract normal vector
                normal = [float(x) for x in line.split()[2:5]]
                normals.append(normal)
                
                # Skip 'outer loop' line
                i += 2
                
                # Read three vertices
                triangle_vertices = []
                for j in range(3):
                    vertex_line = lines[i].strip()
                    if vertex_line.startswith('vertex'):
                        vertex = [float(x) for x in vertex_line.split()[1:4]]
                        vertices.append(vertex)
                        triangle_vertices.append(len(vertices) - 1)
                    i += 1
                
                triangles.append(triangle_vertices)
                # Skip 'endloop' and 'endfacet'
                i += 2
            else:
                i += 1
        
        self.vertices = np.array(vertices)
        self.triangles = np.array(triangles)
        self.normals = np.array(normals)
    
    def read_stl_binary(self, filename):
        """Read binary STL file and extract vertices and triangles."""
        vertices = []
        triangles = []
        normals = []
        
        with open(filename, 'rb') as f:
            # Skip header (80 bytes)
            header = f.read(80)
            
            # Read number of triangles
            num_triangles = struct.unpack('<I', f.read(4))[0]
            
            for i in range(num_triangles):
                # Read normal (3 floats)
                normal = struct.unpack('<3f', f.read(12))
                normals.append(normal)
                
                # Read vertices (9 floats)
                triangle_vertices = []
                for j in range(3):
                    vertex = struct.unpack('<3f', f.read(12))
                    vertices.append(vertex)
                    triangle_vertices.append(len(vertices) - 1)
                
                triangles.append(triangle_vertices)
                
                # Skip attribute byte count (2 bytes)
                f.read(2)
        
        self.vertices = np.array(vertices)
        self.triangles = np.array(triangles)
        self.normals = np.array(normals)
    
    def read_stl(self, filename):
        """Automatically detect and read STL file format."""
        try:
            # Try to read as ASCII first
            with open(filename, 'r') as f:
                first_line = f.readline().strip().lower()
                if first_line.startswith('solid'):
                    self.read_stl_ascii(filename)
                    return
        except:
            pass
        
        # If ASCII failed, try binary
        self.read_stl_binary(filename)
    
    def merge_duplicate_vertices(self):
        """Merge vertices that are closer than tolerance."""
        if len(self.vertices) == 0:
            return
        
        # Build spatial hash for efficient duplicate detection
        vertex_map = {}
        new_vertices = []
        vertex_remap = {}
        
        for i, vertex in enumerate(self.vertices):
            # Create a hash key based on rounded coordinates
            key = tuple(np.round(vertex / self.tolerance).astype(int))
            
            found_duplicate = False
            if key in vertex_map:
                for existing_idx in vertex_map[key]:
                    if np.linalg.norm(vertex - new_vertices[existing_idx]) < self.tolerance:
                        vertex_remap[i] = existing_idx
                        found_duplicate = True
                        break
            
            if not found_duplicate:
                new_idx = len(new_vertices)
                new_vertices.append(vertex)
                vertex_remap[i] = new_idx
                
                if key not in vertex_map:
                    vertex_map[key] = []
                vertex_map[key].append(new_idx)
        
        # Update triangles with new vertex indices
        new_triangles = []
        for triangle in self.triangles:
            new_triangle = [vertex_remap[idx] for idx in triangle]
            new_triangles.append(new_triangle)
        
        self.vertices = np.array(new_vertices)
        self.triangles = np.array(new_triangles)
        
        print(f"Merged {len(self.vertices)} duplicate vertices")
    
    def remove_degenerate_triangles(self):
        """Remove triangles with duplicate vertices or zero area."""
        valid_triangles = []
        valid_normals = []
        
        for i, triangle in enumerate(self.triangles):
            # Check for duplicate vertices in triangle
            if len(set(triangle)) < 3:
                continue
            
            # Get triangle vertices
            v0, v1, v2 = self.vertices[triangle]
            
            # Calculate triangle area using cross product
            edge1 = v1 - v0
            edge2 = v2 - v0
            cross = np.cross(edge1, edge2)
            area = np.linalg.norm(cross) / 2
            
            # Keep triangle if area is above threshold
            if area > self.tolerance:
                valid_triangles.append(triangle)
                if i < len(self.normals):
                    valid_normals.append(self.normals[i])
        
        removed_count = len(self.triangles) - len(valid_triangles)
        self.triangles = np.array(valid_triangles)
        self.normals = np.array(valid_normals)
        
        print(f"Removed {removed_count} degenerate triangles")
    
    def recalculate_normals(self):
        """Recalculate all face normals to ensure consistency."""
        new_normals = []
        
        for triangle in self.triangles:
            v0, v1, v2 = self.vertices[triangle]
            
            # Calculate normal using right-hand rule
            edge1 = v1 - v0
            edge2 = v2 - v0
            normal = np.cross(edge1, edge2)
            
            # Normalize
            norm = np.linalg.norm(normal)
            if norm > 0:
                normal = normal / norm
            else:
                normal = np.array([0, 0, 1])  # Default normal
            
            new_normals.append(normal)
        
        self.normals = np.array(new_normals)
        print("Recalculated all face normals")
    
    def remove_unused_vertices(self):
        """Remove vertices that are not referenced by any triangle."""
        used_vertices = set()
        for triangle in self.triangles:
            used_vertices.update(triangle)
        
        # Create mapping from old to new vertex indices
        vertex_remap = {}
        new_vertices = []
        
        for old_idx in sorted(used_vertices):
            new_idx = len(new_vertices)
            vertex_remap[old_idx] = new_idx
            new_vertices.append(self.vertices[old_idx])
        
        # Update triangle indices
        new_triangles = []
        for triangle in self.triangles:
            new_triangle = [vertex_remap[idx] for idx in triangle]
            new_triangles.append(new_triangle)
        
        removed_count = len(self.vertices) - len(new_vertices)
        self.vertices = np.array(new_vertices)
        self.triangles = np.array(new_triangles)
        
        print(f"Removed {removed_count} unused vertices")
    
    def clean_mesh(self):
        """Apply all cleaning operations in sequence."""
        print("Starting mesh cleaning...")
        print(f"Initial: {len(self.vertices)} vertices, {len(self.triangles)} triangles")
        
        self.merge_duplicate_vertices()
        self.remove_degenerate_triangles()
        self.remove_unused_vertices()
        self.recalculate_normals()
        
        print(f"Final: {len(self.vertices)} vertices, {len(self.triangles)} triangles")
        print("Mesh cleaning completed!")
    
    def write_stl_ascii(self, filename):
        """Write cleaned mesh as ASCII STL file."""
        with open(filename, 'w') as f:
            f.write("solid cleaned_mesh\n")
            
            for i, triangle in enumerate(self.triangles):
                normal = self.normals[i] if i < len(self.normals) else [0, 0, 1]
                f.write(f"  facet normal {normal[0]:.6e} {normal[1]:.6e} {normal[2]:.6e}\n")
                f.write("    outer loop\n")
                
                for vertex_idx in triangle:
                    vertex = self.vertices[vertex_idx]
                    f.write(f"      vertex {vertex[0]:.6e} {vertex[1]:.6e} {vertex[2]:.6e}\n")
                
                f.write("    endloop\n")
                f.write("  endfacet\n")
            
            f.write("endsolid cleaned_mesh\n")
    
    def write_stl_binary(self, filename):
        """Write cleaned mesh as binary STL file."""
        with open(filename, 'wb') as f:
            # Write header (80 bytes)
            header = b"Binary STL created by STL Cleaner" + b"\0" * (80 - 34)
            f.write(header)
            
            # Write number of triangles
            f.write(struct.pack('<I', len(self.triangles)))
            
            for i, triangle in enumerate(self.triangles):
                # Write normal
                normal = self.normals[i] if i < len(self.normals) else [0, 0, 1]
                f.write(struct.pack('<3f', *normal))
                
                # Write vertices
                for vertex_idx in triangle:
                    vertex = self.vertices[vertex_idx]
                    f.write(struct.pack('<3f', *vertex))
                
                # Write attribute byte count (unused, always 0)
                f.write(struct.pack('<H', 0))


def clean_stl_file(input_filename, output_filename, binary_output=True, tolerance=1e-6):
    """
    Clean an STL file and write the result.
    
    Args:
        input_filename (str): Path to input STL file
        output_filename (str): Path to output STL file
        binary_output (bool): Whether to write binary STL (True) or ASCII (False)
        tolerance (float): Tolerance for vertex merging and degenerate triangle detection
    """
    cleaner = STLCleaner(tolerance=tolerance)
    
    try:
        # Read input file
        print(f"Reading STL file: {input_filename}")
        cleaner.read_stl(input_filename)
        
        # Clean the mesh
        cleaner.clean_mesh()
        
        # Write output file
        print(f"Writing cleaned STL file: {output_filename}")
        if binary_output:
            cleaner.write_stl_binary(output_filename)
        else:
            cleaner.write_stl_ascii(output_filename)
        
        print("STL cleaning completed successfully!")
        
    except Exception as e:
        print(f"Error processing STL file: {e}")


# Example usage
if __name__ == "__main__":
    # Example: Clean an STL file
    input_file = "/Users/omokayj/Library/CloudStorage/OneDrive-MarquetteUniversity/vsCode/Research/windAroundBuildings/Tools/output/inUse/geometry/buildingsKilbourn.stl"  # Replace with your input file path
    output_file = "/Users/omokayj/Library/CloudStorage/OneDrive-MarquetteUniversity/vsCode/Research/windAroundBuildings/Tools/output/inUse/geometry/cleaned_buildingsKilbourn.stl"
    
    
    # Clean with default settings (binary output, 1e-6 tolerance)
    clean_stl_file(input_file, output_file)
    
    # Or with custom settings
    # clean_stl_file(input_file, output_file, binary_output=False, tolerance=1e-5)
