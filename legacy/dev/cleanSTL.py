import numpy as np
from collections import defaultdict, Counter
import struct
import os
from typing import Tuple, List, Dict, Set
import time

class STLCleaner:
    def __init__(self, tolerance=1e-6):
        """
        Initialize STL cleaner with specified tolerance for vertex matching.
        
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
            for j in range(3):
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
    
    def get_original_stats(self):
        """Calculate statistics for original mesh."""
        return {
            'vertices': len(self.vertices),
            'faces': len(self.faces),
            'edges': len(self._get_edges()),
            'bounding_box': self._get_bounding_box()
        }
    
    def _get_edges(self):
        """Get all edges in the mesh."""
        edges = set()
        for face in self.faces:
            for i in range(3):
                edge = tuple(sorted([face[i], face[(i+1)%3]]))
                edges.add(edge)
        return edges
    
    def _get_bounding_box(self):
        """Get bounding box of the mesh."""
        min_coords = np.min(self.vertices, axis=0)
        max_coords = np.max(self.vertices, axis=0)
        return {
            'min': min_coords.tolist(),
            'max': max_coords.tolist(),
            'size': (max_coords - min_coords).tolist()
        }
    
    def remove_duplicate_vertices(self):
        """Remove duplicate vertices and update face indices."""
        print("Removing duplicate vertices...")
        
        # Find unique vertices using tolerance
        unique_vertices = []
        vertex_map = {}
        
        for i, vertex in enumerate(self.vertices):
            # Check if this vertex is close to any existing unique vertex
            found_match = False
            for j, unique_vertex in enumerate(unique_vertices):
                if np.linalg.norm(vertex - unique_vertex) < self.tolerance:
                    vertex_map[i] = j
                    found_match = True
                    break
            
            if not found_match:
                vertex_map[i] = len(unique_vertices)
                unique_vertices.append(vertex)
        
        # Update faces with new vertex indices
        new_faces = []
        for face in self.faces:
            new_face = [vertex_map[vertex_idx] for vertex_idx in face]
            # Check if face is degenerate (all vertices are the same)
            if len(set(new_face)) == 3:
                new_faces.append(new_face)
        
        duplicates_removed = len(self.vertices) - len(unique_vertices)
        degenerate_faces_removed = len(self.faces) - len(new_faces)
        
        self.vertices = np.array(unique_vertices)
        self.faces = np.array(new_faces)
        
        if duplicates_removed > 0:
            self.fixes_applied.append(f"Removed {duplicates_removed} duplicate vertices")
        if degenerate_faces_removed > 0:
            self.fixes_applied.append(f"Removed {degenerate_faces_removed} degenerate faces")
    
    def fix_inconsistent_normals(self):
        """Fix inconsistent face normals using connected component analysis."""
        print("Fixing inconsistent normals...")
        
        if len(self.faces) == 0:
            return
        
        # Build adjacency graph
        edge_to_faces = defaultdict(list)
        for face_idx, face in enumerate(self.faces):
            for i in range(3):
                edge = tuple(sorted([face[i], face[(i+1)%3]]))
                edge_to_faces[edge].append((face_idx, i))
        
        # Find connected components and fix orientations
        visited = set()
        flipped_count = 0
        
        for start_face in range(len(self.faces)):
            if start_face in visited:
                continue
            
            # BFS to traverse connected component
            queue = [start_face]
            visited.add(start_face)
            
            while queue:
                current_face = queue.pop(0)
                current_face_vertices = self.faces[current_face]
                
                # Check all edges of current face
                for edge_idx in range(3):
                    v1 = current_face_vertices[edge_idx]
                    v2 = current_face_vertices[(edge_idx + 1) % 3]
                    edge = tuple(sorted([v1, v2]))
                    
                    # Find adjacent faces sharing this edge
                    for face_idx, _ in edge_to_faces[edge]:
                        if face_idx in visited or face_idx == current_face:
                            continue
                        
                        adjacent_face_vertices = self.faces[face_idx]
                        
                        # Check if orientations are consistent
                        if self._are_orientations_inconsistent(
                            current_face_vertices, adjacent_face_vertices, v1, v2
                        ):
                            # Flip the adjacent face
                            self.faces[face_idx] = adjacent_face_vertices[[0, 2, 1]]
                            flipped_count += 1
                        
                        visited.add(face_idx)
                        queue.append(face_idx)
        
        if flipped_count > 0:
            self.fixes_applied.append(f"Fixed orientation of {flipped_count} faces")
    
    def _are_orientations_inconsistent(self, face1, face2, shared_v1, shared_v2):
        """Check if two adjacent faces have inconsistent orientations."""
        # Find the shared edge direction in each face
        face1_list = face1.tolist()
        face2_list = face2.tolist()
        
        # Find edge direction in face1
        try:
            idx1_v1 = face1_list.index(shared_v1)
            idx1_v2 = face1_list.index(shared_v2)
        except ValueError:
            return False
        
        # Find edge direction in face2
        try:
            idx2_v1 = face2_list.index(shared_v1)
            idx2_v2 = face2_list.index(shared_v2)
        except ValueError:
            return False
        
        # Check if the shared edge goes in the same direction in both faces
        # If so, orientations are inconsistent (should be opposite)
        face1_direction = (idx1_v2 - idx1_v1) % 3 == 1
        face2_direction = (idx2_v2 - idx2_v1) % 3 == 1
        
        return face1_direction == face2_direction
    
    def analyze_connected_components(self):
        """Analyze and report connected components (unconnected parts)."""
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
        
        # Find connected components
        visited = set()
        components = []
        
        for face_idx in range(len(self.faces)):
            if face_idx in visited:
                continue
            
            # BFS to find component
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
    
    def remove_floating_fragments(self, min_fragment_size=10):
        """Remove small disconnected fragments."""
        print(f"Removing floating fragments smaller than {min_fragment_size} faces...")
        
        components = self.analyze_connected_components()
        if len(components) <= 1:
            return
        
        print(f"Found {len(components)} unconnected parts")
        
        # Sort components by size (largest first)
        components.sort(key=len, reverse=True)
        
        # Report component sizes
        for i, component in enumerate(components[:10]):  # Show top 10
            print(f"  Part {i+1}: {len(component)} faces")
        
        # Keep only large components
        faces_to_keep = []
        removed_fragments = 0
        
        for component in components:
            if len(component) >= min_fragment_size:
                faces_to_keep.extend(component)
            else:
                removed_fragments += 1
        
        if removed_fragments > 0:
            # Update faces and remove unused vertices
            self.faces = self.faces[faces_to_keep]
            self._remove_unused_vertices()
            self.fixes_applied.append(f"Removed {removed_fragments} floating fragments (kept {len(components) - removed_fragments} large parts)")
    
    def analyze_normal_zones(self):
        """Analyze normal orientation zones in the mesh."""
        if len(self.faces) == 0:
            return 0
        
        # Calculate face normals
        face_normals = []
        for face in self.faces:
            v0, v1, v2 = self.vertices[face]
            normal = np.cross(v1 - v0, v2 - v0)
            if np.linalg.norm(normal) > 0:
                normal = normal / np.linalg.norm(normal)
            else:
                normal = np.array([0, 0, 1])
            face_normals.append(normal)
        
        face_normals = np.array(face_normals)
        
        # Build adjacency graph for faces
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
        
        # Find zones with consistent normals
        visited = set()
        zones = []
        normal_threshold = 0.9  # cos(~25 degrees)
        
        for face_idx in range(len(self.faces)):
            if face_idx in visited:
                continue
            
            # BFS to find zone with consistent normal orientation
            zone = []
            queue = [face_idx]
            visited.add(face_idx)
            reference_normal = face_normals[face_idx]
            
            while queue:
                current_face = queue.pop(0)
                zone.append(current_face)
                
                for adjacent_face in face_adjacency[current_face]:
                    if adjacent_face in visited:
                        continue
                    
                    # Check if normal is consistent with reference
                    dot_product = np.dot(face_normals[adjacent_face], reference_normal)
                    if dot_product > normal_threshold:
                        visited.add(adjacent_face)
                        queue.append(adjacent_face)
            
            zones.append(zone)
        
        return len(zones)
    
    def fix_conflicting_faces(self):
        """Remove or fix faces with conflicting orientations."""
        if not hasattr(self, 'conflicting_faces') or not self.conflicting_faces:
            return
        
        print(f"Fixing {len(self.conflicting_faces)} conflicting faces...")
        
        # Remove conflicting faces (simple approach)
        faces_to_keep = []
        for i, face in enumerate(self.faces):
            if i not in self.conflicting_faces:
                faces_to_keep.append(i)
        
        if len(faces_to_keep) < len(self.faces):
            self.faces = self.faces[faces_to_keep]
            self._remove_unused_vertices()
            removed_count = len(self.faces) - len(faces_to_keep)
            self.fixes_applied.append(f"Removed {removed_count} conflicting faces")
    
    def export_problem_faces(self, filepath="problem_faces.txt"):
        """Export problematic face indices for debugging."""
        if hasattr(self, 'conflicting_faces') and self.conflicting_faces:
            with open(filepath, 'w') as f:
                f.write("Conflicting face indices:\n")
                for face_idx in self.conflicting_faces:
                    f.write(f"{face_idx}\n")
            print(f"Problem faces exported to {filepath}")
            return True
        return False
    def _remove_unused_vertices(self):
        """Remove vertices that are not referenced by any face."""
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
        
        removed_vertices = len(self.vertices) - len(new_vertices)
        
        self.vertices = np.array(new_vertices)
        self.faces = np.array(new_faces)
        
        if removed_vertices > 0:
            self.fixes_applied.append(f"Removed {removed_vertices} unused vertices")
    
    def detect_and_report_issues(self):
        """Detect various mesh issues and report them with detailed diagnostics."""
        issues = []
        
        # Check for non-manifold edges and detailed edge analysis
        edge_count = Counter()
        edge_lengths = {}
        
        for face in self.faces:
            for i in range(3):
                v1, v2 = face[i], face[(i+1)%3]
                edge = tuple(sorted([v1, v2]))
                edge_count[edge] += 1
                
                # Calculate edge length
                if edge not in edge_lengths:
                    length = np.linalg.norm(self.vertices[v1] - self.vertices[v2])
                    edge_lengths[edge] = length
        
        # Analyze edge connectivity
        boundary_edges = sum(1 for count in edge_count.values() if count == 1)
        non_manifold_edges = sum(1 for count in edge_count.values() if count > 2)
        manifold_edges = sum(1 for count in edge_count.values() if count == 2)
        
        # Find edge length statistics
        if edge_lengths:
            lengths = list(edge_lengths.values())
            min_length = min(lengths)
            max_length = max(lengths)
            min_edge = min(edge_lengths, key=edge_lengths.get)
            max_edge = max(edge_lengths, key=edge_lengths.get)
            
            issues.append(f"Edge length statistics:")
            issues.append(f"  Min: {min_length:.6f} for edge {min_edge} points {self.vertices[min_edge[0]]} {self.vertices[min_edge[1]]}")
            issues.append(f"  Max: {max_length:.6f} for edge {max_edge} points {self.vertices[max_edge[0]]} {self.vertices[max_edge[1]]}")
        
        # Check for nearby points (potential duplicates)
        bbox_size = np.max(self.vertices, axis=0) - np.min(self.vertices, axis=0)
        bbox_diagonal = np.linalg.norm(bbox_size)
        threshold = bbox_diagonal * 1e-6
        
        nearby_count = 0
        for i in range(len(self.vertices)):
            for j in range(i+1, len(self.vertices)):
                if np.linalg.norm(self.vertices[i] - self.vertices[j]) < threshold:
                    nearby_count += 1
        
        issues.append(f"Checking for points less than 1e-6 of bounding box ({bbox_size}) apart.")
        issues.append(f"Found {nearby_count} nearby points.")
        
        # Surface closure analysis
        if boundary_edges > 0 or non_manifold_edges > 0:
            issues.append(f"Surface is not closed since not all edges connected to two faces:")
            issues.append(f"  connected to one face : {boundary_edges}")
            issues.append(f"  connected to >2 faces : {non_manifold_edges}")
            issues.append(f"  properly connected (manifold) : {manifold_edges}")
        
        # Check for conflicting faces (more detailed analysis)
        face_normals = {}
        conflicting_faces = []
        
        for i, face in enumerate(self.faces):
            # Sort vertices to create canonical representation
            sorted_face = tuple(sorted(face))
            
            # Calculate face normal
            v0, v1, v2 = self.vertices[face]
            normal = np.cross(v1 - v0, v2 - v0)
            if np.linalg.norm(normal) > 0:
                normal = normal / np.linalg.norm(normal)
            
            if sorted_face in face_normals:
                # Check if normals are conflicting (opposite directions)
                existing_normal = face_normals[sorted_face]
                dot_product = np.dot(normal, existing_normal)
                if dot_product < -0.5:  # Roughly opposite directions
                    conflicting_faces.append(i)
            else:
                face_normals[sorted_face] = normal
        
        if conflicting_faces:
            issues.append(f"Conflicting face labels: {len(conflicting_faces)}")
            # Save conflicting face indices for debugging
            self.conflicting_faces = conflicting_faces
        
        return issues
    
    def clean_stl(self, input_filepath, output_filepath=None, 
                  remove_fragments=True, min_fragment_size=10, output_format='binary',
                  fix_conflicting=True, export_debug=True):
        """
        Main function to clean STL file.
        
        Args:
            input_filepath: Path to input STL file
            output_filepath: Path to output STL file (optional)
            remove_fragments: Whether to remove floating fragments
            min_fragment_size: Minimum size for fragments to keep
            output_format: 'binary' or 'ascii'
            fix_conflicting: Whether to remove conflicting faces
            export_debug: Whether to export debug information
        """
        print(f"Starting STL cleaning process for: {input_filepath}")
        print("-" * 50)
        
        start_time = time.time()
        
        # Read STL file
        self.vertices, self.faces = self.read_stl(input_filepath)
        self.original_stats = self.get_original_stats()
        
        print(f"Original mesh statistics:")
        print(f"  Vertices: {self.original_stats['vertices']}")
        print(f"  Faces: {self.original_stats['faces']}")
        print(f"  Edges: {self.original_stats['edges']}")
        print()
        
        # Analyze connected components
        components = self.analyze_connected_components()
        print(f"Number of unconnected parts: {len(components)}")
        
        # Analyze normal zones
        num_zones = self.analyze_normal_zones()
        print(f"Number of zones (connected areas with consistent normals): {num_zones}")
        if num_zones > len(components):
            print("More than one normal orientation detected.")
        print()
        
        # Detect initial issues
        initial_issues = self.detect_and_report_issues()
        if initial_issues:
            print("Detailed mesh analysis:")
            for issue in initial_issues:
                print(f"  {issue}")
            print()
        
        # Export debug info if requested
        if export_debug:
            self.export_problem_faces()
        
        # Apply fixes
        self.fixes_applied = []
        
        # 1. Remove duplicate vertices
        self.remove_duplicate_vertices()
        
        # 2. Fix conflicting faces (optional)
        if fix_conflicting:
            self.fix_conflicting_faces()
        
        # 3. Fix inconsistent normals
        self.fix_inconsistent_normals()
        
        # 4. Remove floating fragments (optional)
        if remove_fragments:
            self.remove_floating_fragments(min_fragment_size)
        
        # Get final statistics
        self.cleaned_stats = self.get_original_stats()
        
        # Final issue check
        final_issues = self.detect_and_report_issues()
        
        # Final component analysis
        final_components = self.analyze_connected_components()
        final_zones = self.analyze_normal_zones()
        
        # Write cleaned file
        if output_filepath:
            self.write_stl(output_filepath, output_format)
            print(f"Cleaned STL saved to: {output_filepath}")
        
        # Generate report
        self._generate_report(input_filepath, output_filepath, initial_issues, 
                            final_issues, time.time() - start_time,
                            len(components), len(final_components),
                            num_zones, final_zones)
        
        return output_filepath
    
    def _generate_report(self, input_file, output_file, initial_issues, final_issues, 
                        processing_time, initial_components=0, final_components=0,
                        initial_zones=0, final_zones=0):
        """Generate detailed cleaning report."""
        print("\n" + "="*70)
        print("STL CLEANING REPORT")
        print("="*70)
        
        print(f"\nInput file: {input_file}")
        if output_file:
            print(f"Output file: {output_file}")
        print(f"Processing time: {processing_time:.2f} seconds")
        
        print(f"\nMESH STATISTICS:")
        print(f"{'Metric':<25} {'Original':<12} {'Cleaned':<12} {'Change':<12}")
        print("-" * 61)
        
        for metric in ['vertices', 'faces', 'edges']:
            original = self.original_stats[metric]
            cleaned = self.cleaned_stats[metric]
            change = cleaned - original
            change_str = f"{change:+d}" if change != 0 else "0"
            print(f"{metric.capitalize():<25} {original:<12} {cleaned:<12} {change_str:<12}")
        
        if initial_components > 0:
            print(f"{'Connected components':<25} {initial_components:<12} {final_components:<12} {final_components-initial_components:+d}")
        
        if initial_zones > 0:
            print(f"{'Normal zones':<25} {initial_zones:<12} {final_zones:<12} {final_zones-initial_zones:+d}")
        
        print(f"\nFIXES APPLIED:")
        if self.fixes_applied:
            for fix in self.fixes_applied:
                print(f"  ✓ {fix}")
        else:
            print("  No fixes were necessary")
        
        print(f"\nDETAILED ANALYSIS:")
        print("Before cleaning:")
        if initial_issues:
            for issue in initial_issues:
                if not issue.startswith(" "):
                    print(f"  {issue}")
        
        print(f"\nAfter cleaning:")
        if final_issues:
            remaining_problems = []
            for issue in final_issues:
                if not issue.startswith(" "):
                    remaining_problems.append(issue)
            
            if remaining_problems:
                for issue in remaining_problems:
                    print(f"  {issue}")
            else:
                print("  All major issues resolved!")
        else:
            print("  No issues remaining!")
        
        print(f"\nBOUNDING BOX:")
        bbox = self.cleaned_stats['bounding_box']
        print(f"  Min: ({bbox['min'][0]:.3f}, {bbox['min'][1]:.3f}, {bbox['min'][2]:.3f})")
        print(f"  Max: ({bbox['max'][0]:.3f}, {bbox['max'][1]:.3f}, {bbox['max'][2]:.3f})")
        print(f"  Size: ({bbox['size'][0]:.3f}, {bbox['size'][1]:.3f}, {bbox['size'][2]:.3f}) units")
        
        print("="*70)

# Example usage
def main():
    """Example usage of the STL cleaner."""
    # Initialize cleaner
    cleaner = STLCleaner(tolerance=1e-6)
    
    # Clean STL file
    input_file = "/Users/omokayj/Library/CloudStorage/OneDrive-MarquetteUniversity/vsCode/Research/windAroundBuildings/Tools/output/inUse/geometry/buildingsKilbourn.stl"  # Replace with your input file path
    output_file = "/Users/omokayj/Library/CloudStorage/OneDrive-MarquetteUniversity/vsCode/Research/windAroundBuildings/Tools/output/inUse/geometry/cleaned_buildingsKilbourn.stl"
    
    try:
        cleaner.clean_stl(
            input_filepath=input_file,
            output_filepath=output_file,
            remove_fragments=True,
            min_fragment_size=10,
            output_format='binary'
        )
    except FileNotFoundError:
        print(f"Error: Could not find input file '{input_file}'")
        print("Please upload your STL file and update the input_file path.")
    except Exception as e:
        print(f"Error during cleaning: {str(e)}")

if __name__ == "__main__":
    main()
