import numpy as np
from collections import defaultdict, Counter
import struct
# import os  # Unused import removed
# from typing import Tuple, List, Dict, Set  # Unused imports removed
import time

class AdvancedSTLCleaner:
    def __init__(self, tolerance=1e-6):
        """
        Advanced STL cleaner with aggressive mesh repair capabilities.
        
        Args:
            tolerance: Tolerance for considering vertices as identical
        """
        self.tolerance = tolerance
        self.vertices = None
        self.faces = None
        self.original_stats = {}
        self.cleaned_stats = {}
        self.fixes_applied = []
        
    def read_stl(self, filepath):
        """Read STL file (binary or ASCII format)."""
        try:
            with open(filepath, 'rb') as f:
                # Try binary format first
                header = f.read(80)
                if header.startswith(b'solid ') and b'\n' in header:
                    # Likely ASCII format
                    f.seek(0)
                    return self._read_ascii_stl(f)
                else:
                    # Binary format
                    f.seek(80)  # Skip header
                    num_triangles = struct.unpack('<I', f.read(4))[0]
                    return self._read_binary_stl(f, num_triangles)
        except Exception as e:
            raise Exception(f"Error reading STL file: {str(e)}")
    
    def _read_binary_stl(self, file, num_triangles):
        """Read binary STL format."""
        vertices = []
        faces = []
        
        for i in range(num_triangles):
            # Skip normal vector (12 bytes)
            file.read(12)
            
            # Read 3 vertices (9 floats)
            triangle_vertices = []
            for _ in range(3):
                vertex = struct.unpack('<fff', file.read(12))
                triangle_vertices.append(vertex)
            
            vertices.extend(triangle_vertices)
            faces.append([i*3, i*3+1, i*3+2])
            
            # Skip attribute byte count
            file.read(2)
        
        return np.array(vertices), np.array(faces)
    
    def _read_ascii_stl(self, file):
        """Read ASCII STL format."""
        vertices = []
        faces = []
        face_count = 0
        
        for line in file:
            line = line.decode('utf-8').strip()
            if line.startswith('vertex'):
                coords = [float(x) for x in line.split()[1:]]
                vertices.append(coords)
            elif line.startswith('endfacet'):
                if len(vertices) >= 3:
                    start_idx = face_count * 3
                    faces.append([start_idx, start_idx+1, start_idx+2])
                    face_count += 1
        
        return np.array(vertices), np.array(faces)
    
    def write_stl(self, filepath, format='binary'):
        """Write cleaned STL file."""
        if format.lower() == 'binary':
            self._write_binary_stl(filepath)
        else:
            self._write_ascii_stl(filepath)
    
    def _write_binary_stl(self, filepath):
        """Write binary STL format."""
        with open(filepath, 'wb') as f:
            # Header (80 bytes)
            header = b'Cleaned STL file' + b'\0' * 64
            f.write(header)
            
            # Number of triangles
            f.write(struct.pack('<I', len(self.faces)))
            
            # Write triangles
            for face in self.faces:
                # Calculate normal
                v0, v1, v2 = self.vertices[face]
                normal = np.cross(v1 - v0, v2 - v0)
                if np.linalg.norm(normal) > 0:
                    normal = normal / np.linalg.norm(normal)
                else:
                    normal = np.array([0, 0, 1])
                
                # Write normal
                f.write(struct.pack('<fff', *normal))
                
                # Write vertices
                for vertex_idx in face:
                    vertex = self.vertices[vertex_idx]
                    f.write(struct.pack('<fff', *vertex))
                
                # Attribute byte count
                f.write(struct.pack('<H', 0))
    
    def _write_ascii_stl(self, filepath):
        """Write ASCII STL format."""
        with open(filepath, 'w') as f:
            f.write('solid cleaned_object\n')
            
            for face in self.faces:
                # Calculate normal
                v0, v1, v2 = self.vertices[face]
                normal = np.cross(v1 - v0, v2 - v0)
                if np.linalg.norm(normal) > 0:
                    normal = normal / np.linalg.norm(normal)
                else:
                    normal = np.array([0, 0, 1])
                
                f.write(f'  facet normal {normal[0]:.6e} {normal[1]:.6e} {normal[2]:.6e}\n')
                f.write('    outer loop\n')
                
                for vertex_idx in face:
                    vertex = self.vertices[vertex_idx]
                    f.write(f'      vertex {vertex[0]:.6e} {vertex[1]:.6e} {vertex[2]:.6e}\n')
                
                f.write('    endloop\n')
                f.write('  endfacet\n')
            
            f.write('endsolid cleaned_object\n')
    
    def aggressive_vertex_merge(self, tolerance_multiplier=10.0):
        """Aggressively merge vertices using larger tolerance, but avoid merging distinct vertices that are just close."""
        print(f"Aggressively merging vertices (tolerance × {tolerance_multiplier})...")

        merge_tolerance = self.tolerance * tolerance_multiplier

        # Use KDTree for efficient neighbor search
        try:
            from scipy.spatial import cKDTree as KDTree
        except ImportError:
            from scipy.spatial import KDTree

        if len(self.vertices) == 0:
            return

        tree = KDTree(self.vertices)
        groups = [-1] * len(self.vertices)
        group_id = 0

        for i in range(len(self.vertices)):
            if groups[i] != -1:
                continue
            idxs = tree.query_ball_point(self.vertices[i], merge_tolerance)
            # Only merge truly identical or extremely close points
            idxs = [idx for idx in idxs if np.linalg.norm(self.vertices[i] - self.vertices[idx]) < merge_tolerance * 0.5]
            for idx in idxs:
                groups[idx] = group_id
            group_id += 1

        unique_vertices = []
        vertex_map = {}
        for gid in range(group_id):
            indices = [i for i, g in enumerate(groups) if g == gid]
            if indices:
                avg = np.mean(self.vertices[indices], axis=0)
                unique_vertices.append(avg)
                for idx in indices:
                    vertex_map[idx] = len(unique_vertices) - 1

        # Update faces
        new_faces = []
        for face in self.faces:
            new_face = [vertex_map[vertex_idx] for vertex_idx in face]
            if len(set(new_face)) == 3:
                new_faces.append(new_face)

        merged_count = len(self.vertices) - len(unique_vertices)
        removed_faces = len(self.faces) - len(new_faces)

        self.vertices = np.array(unique_vertices)
        self.faces = np.array(new_faces)

        if merged_count > 0:
            self.fixes_applied.append(f"Aggressively merged {merged_count} vertices")
        if removed_faces > 0:
            self.fixes_applied.append(f"Removed {removed_faces} degenerate faces from merging")
    
    def remove_non_manifold_edges(self):
        """Remove faces that create non-manifold edges."""
        print("Removing faces with non-manifold edges...")
        
        # Count edge usage
        edge_count = Counter()
        edge_to_faces = defaultdict(list)
        
        for face_idx, face in enumerate(self.faces):
            for i in range(3):
                edge = tuple(sorted([face[i], face[(i+1)%3]]))
                edge_count[edge] += 1
                edge_to_faces[edge].append(face_idx)
        
        # Identify faces to remove (those with non-manifold edges)
        faces_to_remove = set()
        non_manifold_edges = 0
        
        for edge, count in edge_count.items():
            if count > 2:  # Non-manifold edge
                non_manifold_edges += 1
                # Remove excess faces (keep only 2)
                face_list = edge_to_faces[edge]
                # Remove faces with smaller area first
                face_areas = []
                for face_idx in face_list:
                    face = self.faces[face_idx]
                    v0, v1, v2 = self.vertices[face]
                    area = 0.5 * np.linalg.norm(np.cross(v1 - v0, v2 - v0))
                    face_areas.append((area, face_idx))
                
                face_areas.sort()  # Smallest area first
                for _, face_idx in face_areas[2:]:  # Remove all but largest 2
                    faces_to_remove.add(face_idx)
        
        if faces_to_remove:
            # Keep only manifold faces
            faces_to_keep = []
            for i, face in enumerate(self.faces):
                if i not in faces_to_remove:
                    faces_to_keep.append(face)
            
            self.faces = np.array(faces_to_keep)
            self._remove_unused_vertices()
            self.fixes_applied.append(f"Removed {len(faces_to_remove)} faces creating {non_manifold_edges} non-manifold edges")
    
    def remove_conflicting_faces(self):
        """Remove faces that have the same vertices but different orientations."""
        print("Removing conflicting faces...")
        
        face_dict = {}
        faces_to_remove = set()
        
        for face_idx, face in enumerate(self.faces):
            # Create canonical face representation
            sorted_face = tuple(sorted(face))
            
            if sorted_face in face_dict:
                # Check if orientations are different
                existing_face_idx = face_dict[sorted_face]
                existing_face = self.faces[existing_face_idx]
                
                # Calculate normals to check orientation
                def face_normal(f):
                    v0, v1, v2 = self.vertices[f]
                    normal = np.cross(v1 - v0, v2 - v0)
                    if np.linalg.norm(normal) > 1e-10:
                        return normal / np.linalg.norm(normal)
                    return np.array([0, 0, 1])
                
                normal1 = face_normal(existing_face)
                normal2 = face_normal(face)
                
                # If normals are opposite (conflicting), remove the smaller face
                if np.dot(normal1, normal2) < -0.5:
                    area1 = 0.5 * np.linalg.norm(np.cross(
                        self.vertices[existing_face[1]] - self.vertices[existing_face[0]], 
                        self.vertices[existing_face[2]] - self.vertices[existing_face[0]]
                    ))
                    area2 = 0.5 * np.linalg.norm(np.cross(
                        self.vertices[face[1]] - self.vertices[face[0]], 
                        self.vertices[face[2]] - self.vertices[face[0]]
                    ))
                    
                    if area1 >= area2:
                        faces_to_remove.add(face_idx)
                    else:
                        faces_to_remove.add(existing_face_idx)
                        face_dict[sorted_face] = face_idx
            else:
                face_dict[sorted_face] = face_idx
        
        if faces_to_remove:
            faces_to_keep = []
            for i, face in enumerate(self.faces):
                if i not in faces_to_remove:
                    faces_to_keep.append(face)
            
            self.faces = np.array(faces_to_keep)
            self._remove_unused_vertices()
            self.fixes_applied.append(f"Removed {len(faces_to_remove)} conflicting faces")
    
    def keep_largest_component_only(self):
        """Keep only the largest connected component."""
        print("Keeping only the largest connected component...")
        
        components = self._analyze_connected_components()
        if len(components) <= 1:
            return
        
        # Sort by size and keep largest
        components.sort(key=len, reverse=True)
        largest_component = components[0]
        
        # Update faces to keep only largest component
        self.faces = self.faces[largest_component]
        self._remove_unused_vertices()
        
        removed_parts = len(components) - 1
        self.fixes_applied.append(f"Kept largest component, removed {removed_parts} smaller parts ({len(self.faces)} faces remaining)")
    
    def _analyze_connected_components(self):
        """Analyze connected components of the mesh."""
        if len(self.faces) == 0:
            return []
        
        # Build face adjacency graph
        face_adjacency = defaultdict(set)
        edge_to_faces = defaultdict(list)
        
        for face_idx, face in enumerate(self.faces):
            for i in range(3):
                edge = tuple(sorted([face[i], face[(i+1)%3]]))
                edge_to_faces[edge].append(face_idx)
        
        for edge_faces in edge_to_faces.values():
            for i in range(len(edge_faces)):
                for j in range(i+1, len(edge_faces)):
                    face_adjacency[edge_faces[i]].add(edge_faces[j])
                    face_adjacency[edge_faces[j]].add(edge_faces[i])
        
        # Find connected components using BFS
        visited = set()
        components = []
        
        for face_idx in range(len(self.faces)):
            if face_idx in visited:
                continue
            
            component = []
            queue = [face_idx]
            visited.add(face_idx)
            
            while queue:
                current_face = queue.pop(0)
                component.append(current_face)
                
                for adjacent_face in face_adjacency[current_face]:
                    if adjacent_face not in visited:
                        visited.add(adjacent_face)
                        queue.append(adjacent_face)
            
            components.append(component)
        
        return components
    
    def _remove_unused_vertices(self):
        """Remove vertices that are not referenced by any face."""
        if len(self.faces) == 0:
            self.vertices = np.array([])
            return
            
        used_vertices = set()
        for face in self.faces:
            used_vertices.update(face)
        
        # Create mapping from old to new vertex indices
        old_to_new = {}
        new_vertices = []
        
        for i, old_idx in enumerate(sorted(used_vertices)):
            old_to_new[old_idx] = i
            new_vertices.append(self.vertices[old_idx])
        
        # Update faces with new indices
        new_faces = []
        for face in self.faces:
            new_face = [old_to_new[vertex_idx] for vertex_idx in face]
            new_faces.append(new_face)
        
        self.vertices = np.array(new_vertices)
        self.faces = np.array(new_faces)
    
    def perform_mesh_analysis(self):
        """Perform comprehensive mesh analysis matching your tool's output."""
        print("\n" + "="*70)
        print("COMPREHENSIVE MESH ANALYSIS")
        print("="*70)
        
        # Edge analysis
        edge_lengths = {}
        edge_count = Counter()
        
        for face in self.faces:
            for i in range(3):
                v1, v2 = face[i], face[(i+1)%3]
                edge = tuple(sorted([v1, v2]))
                edge_count[edge] += 1
                
                if edge not in edge_lengths:
                    length = np.linalg.norm(self.vertices[v1] - self.vertices[v2])
                    edge_lengths[edge] = length
        
        if edge_lengths:
            lengths = list(edge_lengths.values())
            min_length = min(lengths)
            max_length = max(lengths)
            min_edge = min(edge_lengths, key=edge_lengths.get)
            max_edge = max(edge_lengths, key=edge_lengths.get)
            
            print(f"\nEdges:")
            print(f"    min {min_length:.6f} for edge {list(edge_lengths.keys()).index(min_edge)} points {self.vertices[min_edge[0]]} {self.vertices[min_edge[1]]}")
            print(f"    max {max_length:.6f} for edge {list(edge_lengths.keys()).index(max_edge)} points {self.vertices[max_edge[0]]} {self.vertices[max_edge[1]]}")
        
        # Nearby points analysis
        bbox_size = np.max(self.vertices, axis=0) - np.min(self.vertices, axis=0)
        bbox_diagonal = np.linalg.norm(bbox_size)
        threshold = bbox_diagonal * 1e-6
        
        nearby_count = 0
        for i in range(len(self.vertices)):
            for j in range(i+1, min(i+100, len(self.vertices))):  # Limit for performance
                if np.linalg.norm(self.vertices[i] - self.vertices[j]) < threshold:
                    nearby_count += 1
        
        print(f"\nChecking for points less than 1e-6 of bounding box ({bbox_size}) apart.")
        print(f"Found {nearby_count} nearby points.")
        
        # Surface closure analysis
        boundary_edges = sum(1 for count in edge_count.values() if count == 1)
        non_manifold_edges = sum(1 for count in edge_count.values() if count > 2)
        manifold_edges = sum(1 for count in edge_count.values() if count == 2)
        
        if boundary_edges > 0 or non_manifold_edges > 0:
            print(f"\nSurface is not closed since not all edges connected to two faces:")
            print(f"    connected to one face : {boundary_edges}")
            print(f"    connected to >2 faces : {non_manifold_edges}")
        else:
            print(f"\nSurface appears to be closed (all edges properly connected)")
        
        # Connected components analysis
        components = self._analyze_connected_components()
        print(f"\nNumber of unconnected parts : {len(components)}")
        
        if len(components) > 1:
            print("Component sizes:")
            for i, comp in enumerate(sorted(components, key=len, reverse=True)[:10]):
                print(f"    Part {i+1}: {len(comp)} faces")
        # manifold_edges = sum(1 for count in edge_count.values() if count == 2)  # Unused variable removed
        return {
            'boundary_edges': boundary_edges,
            'non_manifold_edges': non_manifold_edges,
            'components': len(components),
            'nearby_points': nearby_count,
            'min_edge_length': min_length if edge_lengths else 0,
            'max_edge_length': max_length if edge_lengths else 0
        }
    
    def aggressive_clean_stl(self, input_filepath, output_filepath=None, 
                            keep_largest_only=False, tolerance_multiplier=5.0,
                            output_format='binary'):
        """
        Aggressively clean STL file to resolve complex mesh issues.
        
        Args:
            input_filepath: Path to input STL file
            output_filepath: Path to output STL file
            keep_largest_only: Keep only the largest connected component
            tolerance_multiplier: How much to increase merge tolerance
            output_format: 'binary' or 'ascii'
        """
        print(f"Starting AGGRESSIVE STL cleaning for: {input_filepath}")
        print("-" * 70)
        
        start_time = time.time()
        
        # Read STL file
        self.vertices, self.faces = self.read_stl(input_filepath)
        print(f"Loaded {len(self.vertices)} vertices, {len(self.faces)} faces")
        
        # Initial analysis
        print("\nBEFORE CLEANING:")
        initial_analysis = self.perform_mesh_analysis()
        
        # Apply aggressive fixes
        self.fixes_applied = []
        
        # 1. Aggressive vertex merging
        self.aggressive_vertex_merge(tolerance_multiplier)
        
        # 2. Remove conflicting faces
        self.remove_conflicting_faces()
        
        # 3. Remove non-manifold edges
        self.remove_non_manifold_edges()
        
        # 4. Optionally keep only largest component
        if keep_largest_only:
            self.keep_largest_component_only()
        
        # Final analysis
        print(f"\nAFTER CLEANING:")
        final_analysis = self.perform_mesh_analysis()
        
        # Write output
        if output_filepath:
            self.write_stl(output_filepath, output_format)
            print(f"\nCleaned STL saved to: {output_filepath}")
        
        # Summary report
        processing_time = time.time() - start_time
        print(f"\n" + "="*70)
        print(f"CLEANING SUMMARY")
        print(f"="*70)
        print(f"Processing time: {processing_time:.2f} seconds")
        print(f"Final mesh: {len(self.vertices)} vertices, {len(self.faces)} faces")
        
        print(f"\nFixes applied:")
        for fix in self.fixes_applied:
            print(f"  ✓ {fix}")
        
        print(f"\nImprovement summary:")
        print(f"  Boundary edges: {initial_analysis['boundary_edges']} → {final_analysis['boundary_edges']}")
        print(f"  Non-manifold edges: {initial_analysis['non_manifold_edges']} → {final_analysis['non_manifold_edges']}")
        print(f"  Connected parts: {initial_analysis['components']} → {final_analysis['components']}")
        
        return output_filepath

# Example usage for complex meshes
def main():
    """Example usage for cleaning complex STL files."""
    cleaner = AdvancedSTLCleaner(tolerance=1e-6)
    
    # Clean STL file
    input_file = "/Users/omokayj/Library/CloudStorage/OneDrive-MarquetteUniversity/vsCode/Research/windAroundBuildings/Tools/output/inUse/geometry/buildingsKilbourn.stl"  # Replace with your input file path
    output_file = "/Users/omokayj/Library/CloudStorage/OneDrive-MarquetteUniversity/vsCode/Research/windAroundBuildings/Tools/output/inUse/geometry/cleaned_buildingsKilbourn.stl"
    
    
    try:
        cleaner.aggressive_clean_stl(
            input_filepath=input_file,
            output_filepath=output_file,
            keep_largest_only=True,      # Keep only main building
            tolerance_multiplier=10.0,   # Aggressive vertex merging
            output_format='binary'
        )
    except FileNotFoundError:
        print(f"Error: Could not find input file '{input_file}'")
        print("Please update the input_file path to your STL file.")
    except Exception as e:
        print(f"Error during cleaning: {str(e)}")

if __name__ == "__main__":
    main()