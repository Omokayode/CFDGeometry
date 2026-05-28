import numpy as np
from collections import defaultdict
import struct
import os
from scipy.spatial import cKDTree
import time

class FastSTLCleaner:
    def __init__(self, tolerance=1e-6):
        """
        Initialize the fast STL cleaner with specified tolerance for vertex merging.
        
        Args:
            tolerance (float): Distance threshold for considering vertices as duplicates
        """
        self.tolerance = tolerance
        self.vertices = None
        self.faces = None
        self.normals = None
        
    def read_stl(self, filename):
        """
        Fast STL file reader (supports both ASCII and binary formats).
        
        Args:
            filename (str): Path to the input STL file
        """
        start_time = time.time()
        
        try:
            # Try binary format first (much faster)
            with open(filename, 'rb') as f:
                # Skip header (80 bytes)
                header = f.read(80)
                
                # Read number of triangles
                triangle_count_data = f.read(4)
                if len(triangle_count_data) != 4:
                    raise ValueError("Invalid binary STL file")
                
                triangle_count = struct.unpack('<I', triangle_count_data)[0]
                print(f"Reading {triangle_count} triangles from binary STL...")
                
                # Pre-allocate arrays for better performance
                faces = np.zeros((triangle_count, 3, 3), dtype=np.float32)
                
                # Read all triangle data at once
                triangle_size = 50  # 12 (normal) + 36 (vertices) + 2 (attribute)
                remaining_data = f.read(triangle_count * triangle_size)
                
                if len(remaining_data) != triangle_count * triangle_size:
                    raise ValueError("Incomplete STL file")
                
                # Parse triangles using vectorized operations
                for i in range(triangle_count):
                    offset = i * triangle_size
                    
                    # Skip normal (12 bytes)
                    vertex_start = offset + 12
                    
                    # Read vertices (36 bytes)
                    vertex_data = remaining_data[vertex_start:vertex_start + 36]
                    coords = struct.unpack('<9f', vertex_data)
                    
                    faces[i] = np.array([
                        [coords[0], coords[1], coords[2]],
                        [coords[3], coords[4], coords[5]],
                        [coords[6], coords[7], coords[8]]
                    ])
                
                print(f"Successfully read binary STL in {time.time() - start_time:.2f} seconds")
                
        except (struct.error, ValueError) as e:
            print(f"Binary format failed ({e}), trying ASCII format...")
            faces = self._read_ascii_stl_fast(filename)
            
        self.faces = faces.astype(np.float32)  # Use float32 for memory efficiency
        print(f"Loaded {len(self.faces)} triangles")
        
    def _read_ascii_stl_fast(self, filename):
        """Fast ASCII STL reader using numpy."""
        print("Reading ASCII STL file...")
        vertices_list = []
        
        with open(filename, 'r') as f:
            lines = f.readlines()
        
        # Pre-filter vertex lines for speed
        vertex_lines = [line for line in lines if line.strip().lower().startswith('vertex')]
        
        # Parse coordinates in batches
        coords = []
        for line in vertex_lines:
            parts = line.strip().split()
            coords.extend([float(parts[1]), float(parts[2]), float(parts[3])])
        
        # Reshape into triangles
        coords_array = np.array(coords, dtype=np.float32)
        faces = coords_array.reshape(-1, 3, 3)
        
        return faces
    
    def remove_duplicate_vertices_fast(self):
        """
        Fast duplicate vertex removal using KDTree for nearest neighbor search.
        """
        print("Removing duplicate vertices using KDTree...")
        start_time = time.time()
        
        # Flatten all vertices
        all_vertices = self.faces.reshape(-1, 3)
        n_vertices = len(all_vertices)
        print(f"Processing {n_vertices} vertices...")
        
        # Build KDTree for fast spatial queries
        tree = cKDTree(all_vertices)
        
        # Find groups of nearby vertices
        groups = tree.query_ball_tree(tree, r=self.tolerance)
        
        # Create mapping from original to unique vertices
        vertex_map = np.arange(n_vertices)
        unique_vertices = []
        processed = np.zeros(n_vertices, dtype=bool)
        
        for i in range(n_vertices):
            if processed[i]:
                continue
                
            # Get all vertices in this group
            group = groups[i]
            group = [j for j in group if not processed[j]]
            
            if group:
                # Use the first vertex as the representative
                representative_idx = len(unique_vertices)
                unique_vertices.append(all_vertices[i])
                
                # Map all vertices in group to this representative
                for j in group:
                    vertex_map[j] = representative_idx
                    processed[j] = True
        
        # Convert to numpy array
        self.vertices = np.array(unique_vertices, dtype=np.float32)
        
        # Rebuild face indices
        n_faces = len(self.faces)
        self.face_indices = vertex_map.reshape(n_faces, 3)
        
        print(f"Reduced from {n_vertices} to {len(self.vertices)} vertices in {time.time() - start_time:.2f} seconds")
    
    def remove_degenerate_faces_fast(self):
        """Fast removal of degenerate faces using vectorized operations."""
        print("Removing degenerate faces...")
        start_time = time.time()
        
        # Check for faces with duplicate vertex indices
        face_indices = self.face_indices
        
        # Find faces where all three vertices are different
        unique_mask = (face_indices[:, 0] != face_indices[:, 1]) & \
                     (face_indices[:, 1] != face_indices[:, 2]) & \
                     (face_indices[:, 0] != face_indices[:, 2])
        
        # Calculate areas for remaining faces
        vertices = self.vertices[face_indices[unique_mask]]
        v1, v2, v3 = vertices[:, 0], vertices[:, 1], vertices[:, 2]
        
        # Vectorized cross product for area calculation
        edge1 = v2 - v1
        edge2 = v3 - v1
        cross_products = np.cross(edge1, edge2)
        areas = np.linalg.norm(cross_products, axis=1) / 2
        
        # Keep faces with significant area
        area_mask = areas > self.tolerance
        final_mask = np.zeros(len(face_indices), dtype=bool)
        final_mask[unique_mask] = area_mask
        
        original_count = len(self.face_indices)
        self.face_indices = self.face_indices[final_mask]
        
        print(f"Removed {original_count - len(self.face_indices)} degenerate faces in {time.time() - start_time:.2f} seconds")
    
    def fix_normals_fast(self):
        """Fast normal calculation using vectorized operations."""
        print("Calculating face normals...")
        start_time = time.time()
        
        # Get vertices for all faces at once
        vertices = self.vertices[self.face_indices]  # Shape: (n_faces, 3, 3)
        v1, v2, v3 = vertices[:, 0], vertices[:, 1], vertices[:, 2]
        
        # Vectorized cross product
        edge1 = v2 - v1
        edge2 = v3 - v1
        normals = np.cross(edge1, edge2)
        
        # Vectorized normalization
        norms = np.linalg.norm(normals, axis=1, keepdims=True)
        norms = np.where(norms > 0, norms, 1)  # Avoid division by zero
        self.normals = normals / norms
        
        # Set default normal for zero-area faces
        zero_area_mask = np.linalg.norm(normals, axis=1) == 0
        self.normals[zero_area_mask] = [0, 0, 1]
        
        print(f"Calculated {len(self.normals)} normals in {time.time() - start_time:.2f} seconds")
    
    def ensure_manifold_mesh_fast(self):
        """Fast manifold checking using hash maps."""
        print("Checking mesh manifold properties...")
        start_time = time.time()
        
        # Create edges efficiently
        faces = self.face_indices
        edges = np.concatenate([
            np.sort(faces[:, [0, 1]], axis=1),
            np.sort(faces[:, [1, 2]], axis=1),
            np.sort(faces[:, [2, 0]], axis=1)
        ])
        
        # Count edge occurrences using unique
        unique_edges, counts = np.unique(edges, axis=0, return_counts=True)
        
        non_manifold_count = np.sum(counts > 2)
        boundary_count = np.sum(counts == 1)
        
        print(f"Found {non_manifold_count} non-manifold edges and {boundary_count} boundary edges in {time.time() - start_time:.2f} seconds")
    
    def write_stl_fast(self, output_filename, binary=True):
        """
        Fast STL writer.
        
        Args:
            output_filename (str): Path for the output STL file
            binary (bool): Whether to write in binary format (default) or ASCII
        """
        print(f"Writing STL file: {output_filename}")
        start_time = time.time()
        
        if binary:
            self._write_binary_stl_fast(output_filename)
        else:
            self._write_ascii_stl_fast(output_filename)
        
        print(f"File written in {time.time() - start_time:.2f} seconds")
    
    def _write_binary_stl_fast(self, filename):
        """Fast binary STL writer."""
        n_faces = len(self.face_indices)
        
        with open(filename, 'wb') as f:
            # Write header (80 bytes)
            header = b'Fast cleaned STL file' + b'\0' * 59
            f.write(header)
            
            # Write number of triangles
            f.write(struct.pack('<I', n_faces))
            
            # Prepare all data at once for faster writing
            vertices = self.vertices[self.face_indices]  # Shape: (n_faces, 3, 3)
            
            # Write all triangles in batches for better performance
            batch_size = 10000
            for i in range(0, n_faces, batch_size):
                end_idx = min(i + batch_size, n_faces)
                batch_vertices = vertices[i:end_idx]
                batch_normals = self.normals[i:end_idx]
                
                for j, (face_verts, normal) in enumerate(zip(batch_vertices, batch_normals)):
                    # Write normal
                    f.write(struct.pack('<3f', *normal))
                    
                    # Write vertices
                    v1, v2, v3 = face_verts
                    f.write(struct.pack('<9f', *v1, *v2, *v3))
                    
                    # Write attribute byte count
                    f.write(struct.pack('<H', 0))
        
        print(f"Written {n_faces} triangles to binary STL")
    
    def _write_ascii_stl_fast(self, filename):
        """Fast ASCII STL writer."""
        vertices = self.vertices[self.face_indices]
        
        with open(filename, 'w') as f:
            f.write("solid FastCleanedMesh\n")
            
            # Write in batches for better performance
            lines = []
            for face_verts, normal in zip(vertices, self.normals):
                lines.append(f"  facet normal {normal[0]:.6f} {normal[1]:.6f} {normal[2]:.6f}\n")
                lines.append("    outer loop\n")
                for vertex in face_verts:
                    lines.append(f"      vertex {vertex[0]:.6f} {vertex[1]:.6f} {vertex[2]:.6f}\n")
                lines.append("    endloop\n")
                lines.append("  endfacet\n")
                
                # Write in batches to reduce I/O calls
                if len(lines) > 10000:
                    f.writelines(lines)
                    lines = []
            
            # Write remaining lines
            if lines:
                f.writelines(lines)
            
            f.write("endsolid FastCleanedMesh\n")
        
        print(f"Written {len(self.face_indices)} triangles to ASCII STL")
    
    def get_mesh_info(self):
        """Print information about the current mesh."""
        if self.vertices is None or len(self.vertices) == 0:
            print("No mesh loaded")
            return
        
        # Calculate bounding box
        min_coords = np.min(self.vertices, axis=0)
        max_coords = np.max(self.vertices, axis=0)
        dimensions = max_coords - min_coords
        
        print("\n=== Mesh Information ===")
        print(f"Vertices: {len(self.vertices):,}")
        print(f"Faces: {len(self.face_indices):,}")
        print(f"Memory usage: ~{(self.vertices.nbytes + self.face_indices.nbytes) / 1024 / 1024:.1f} MB")
        print(f"Bounding box:")
        print(f"  Min: ({min_coords[0]:.3f}, {min_coords[1]:.3f}, {min_coords[2]:.3f})")
        print(f"  Max: ({max_coords[0]:.3f}, {max_coords[1]:.3f}, {max_coords[2]:.3f})")
        print(f"  Dimensions: {dimensions[0]:.3f} x {dimensions[1]:.3f} x {dimensions[2]:.3f}")
    
    def clean_mesh_fast(self):
        """Perform all cleaning operations with optimized algorithms."""
        print("\n=== Starting FAST mesh cleaning process ===")
        total_start = time.time()
        
        # Step 1: Remove duplicate vertices (now uses KDTree)
        self.remove_duplicate_vertices_fast()
        
        # Step 2: Remove degenerate faces (now vectorized)
        self.remove_degenerate_faces_fast()
        
        # Step 3: Fix normals (now vectorized)
        self.fix_normals_fast()
        
        # Step 4: Check manifold properties (now uses numpy unique)
        self.ensure_manifold_mesh_fast()
        
        total_time = time.time() - total_start
        print(f"=== FAST mesh cleaning completed in {total_time:.2f} seconds ===\n")


def main():
    """Main function with your specific file paths."""
    import sys
    
    # Your specific paths
    input_file = "/Users/omokayj/Library/CloudStorage/OneDrive-MarquetteUniversity/vsCode/Research/windAroundBuildings/Tools/output/inUse/geometry/buildingsKilbourn.stl"
    output_file = "/Users/omokayj/Library/CloudStorage/OneDrive-MarquetteUniversity/vsCode/Research/windAroundBuildings/Tools/output/inUse/geometry/cleaned_buildingsKilbourn.stl"
    
    # Allow command line override if arguments are provided
    if len(sys.argv) >= 2:
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else "cleaned_" + os.path.basename(input_file)
        tolerance = float(sys.argv[3]) if len(sys.argv) > 3 else 1e-6
    else:
        tolerance = 1e-6  # Default tolerance for your specific files
    
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found")
        return
    
    # Create fast cleaner instance
    cleaner = FastSTLCleaner(tolerance=tolerance)
    
    try:
        print(f"Processing large STL file: {input_file}")
        print(f"Using optimized algorithms for better performance...")
        
        # Read the input STL file
        cleaner.read_stl(input_file)
        
        # Show original mesh info
        print("\n=== Original Mesh ===")
        cleaner.get_mesh_info()
        
        # Clean the mesh with fast algorithms
        cleaner.clean_mesh_fast()
        
        # Show cleaned mesh info
        print("=== Cleaned Mesh ===")
        cleaner.get_mesh_info()
        
        # Write the cleaned STL file
        cleaner.write_stl_fast(output_file, binary=True)
        
        print(f"\nFast cleaning completed successfully!")
        print(f"Output written to: {output_file}")
        
    except Exception as e:
        print(f"Error during processing: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()