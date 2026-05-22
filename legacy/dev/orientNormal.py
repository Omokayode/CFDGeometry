import numpy as np
import trimesh
import os

def fix_stl_normals(input_file='input.stl', output_file='oriented_output.stl', target_direction=np.array([0, 0, 1])):
    """
    Fix STL file to have consistent normal orientations for OpenFOAM.
    
    Parameters:
    -----------
    input_file : str
        Path to input STL file
    output_file : str  
        Path to output STL file
    target_direction : np.array
        Target direction for normals (default: [0,0,1] = +Z direction)
    
    Returns:
    --------
    mesh : trimesh.Trimesh
        The processed mesh with fixed normals
    """
    
    print(f"Loading STL file: {input_file}")
    
    # Check if input file exists
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file '{input_file}' not found!")
    
    # Load the mesh
    mesh = trimesh.load(input_file)
    
    print(f"Original mesh info:")
    print(f"  - Vertices: {len(mesh.vertices)}")
    print(f"  - Faces: {len(mesh.faces)}")
    print(f"  - Is watertight: {mesh.is_watertight}")
    print(f"  - Is winding consistent: {mesh.is_winding_consistent}")
    
    # Step 1: Aggressive normal fixing for OpenFOAM
    print("Applying aggressive normal fixing...")
    
    # Remove duplicate vertices and merge close ones
    mesh.remove_duplicate_faces()
    mesh.merge_vertices()
    
    # Fix normals multiple times with different approaches
    for i in range(3):
        print(f"  Normal fixing pass {i+1}...")
        mesh.fix_normals()
        
        # Check if we have consistent winding now
        if mesh.is_winding_consistent:
            print(f"  ✓ Achieved consistent winding after pass {i+1}")
            break
    
    # Step 2: Force consistent orientation by analyzing connected components
    print("Analyzing connected components...")
    components = mesh.split(only_watertight=False)
    print(f"  Found {len(components)} components")
    
    # Process each component separately
    fixed_meshes = []
    for i, component in enumerate(components):
        print(f"  Processing component {i+1}/{len(components)}...")
        
        # Fix normals for this component
        component.fix_normals()
        
        # Get face normals and check consistency
        face_normals = component.face_normals
        
        # Calculate the dominant normal direction
        # Use the most common normal direction (clustering approach)
        normal_dots_with_z = np.dot(face_normals, target_direction)
        positive_normals = np.sum(normal_dots_with_z > 0)
        negative_normals = np.sum(normal_dots_with_z < 0)
        
        print(f"    Component {i+1}: +normals={positive_normals}, -normals={negative_normals}")
        
        # If majority of normals point in wrong direction, flip the entire component
        if negative_normals > positive_normals:
            print(f"    Flipping component {i+1} normals...")
            component.faces = np.fliplr(component.faces)
            component.fix_normals()
        
        fixed_meshes.append(component)
    
    # Step 3: Combine all fixed components
    if len(fixed_meshes) > 1:
        print("Combining fixed components...")
        vertices_list = []
        faces_list = []
        vertex_count = 0
        
        for component in fixed_meshes:
            vertices_list.append(component.vertices)
            faces_list.append(component.faces + vertex_count)
            vertex_count += len(component.vertices)
        
        combined_vertices = np.vstack(vertices_list)
        combined_faces = np.vstack(faces_list)
        
        mesh = trimesh.Trimesh(vertices=combined_vertices, faces=combined_faces)
        mesh.merge_vertices()  # Clean up any duplicate vertices
    else:
        mesh = fixed_meshes[0]
    
    # Step 4: Final aggressive normal consistency check
    print("Final normal consistency enforcement...")
    face_normals = mesh.face_normals
    target_direction = target_direction / np.linalg.norm(target_direction)
    
    # Calculate dot products with target direction
    normal_dots = np.dot(face_normals, target_direction)
    
    # Find faces that point in the wrong direction
    wrong_direction_faces = normal_dots < 0
    num_wrong = np.sum(wrong_direction_faces)
    
    if num_wrong > 0:
        print(f"  Found {num_wrong} faces pointing in wrong direction, flipping...")
        
        # Flip individual faces that point in the wrong direction
        faces_to_flip = np.where(wrong_direction_faces)[0]
        for face_idx in faces_to_flip:
            # Reverse the vertex order for this face
            mesh.faces[face_idx] = mesh.faces[face_idx][::-1]
        
        # Recalculate normals after flipping
        mesh._face_normals = None
        face_normals = mesh.face_normals
    
    # Step 5: Rotate mesh to align with target direction if needed
    avg_normal = np.mean(face_normals, axis=0)
    avg_normal = avg_normal / np.linalg.norm(avg_normal)
    
    print(f"Average normal direction: {avg_normal}")
    print(f"Target direction: {target_direction}")
    
    # Calculate rotation if needed
    dot_product = np.dot(avg_normal, target_direction)
    if dot_product < 0.99:  # Not already aligned
        v = np.cross(avg_normal, target_direction)
        c = np.dot(avg_normal, target_direction)
        
        if not np.allclose(v, 0, atol=1e-6):
            # Create rotation matrix using Rodrigues' rotation formula
            v_norm = np.linalg.norm(v)
            if v_norm > 1e-6:
                v = v / v_norm
                vx = np.array([[0, -v[2], v[1]],
                              [v[2], 0, -v[0]],
                              [-v[1], v[0], 0]])
                
                rotation_matrix = (np.eye(3) + 
                                 np.sin(np.arccos(np.clip(c, -1, 1))) * vx + 
                                 (1 - c) * np.outer(v, v))
                
                # Apply rotation
                transform_matrix = np.eye(4)
                transform_matrix[:3, :3] = rotation_matrix
                mesh.apply_transform(transform_matrix)
                print("Applied rotation to align with target direction")
    
    # Step 6: Final validation
    final_normals = mesh.face_normals
    final_avg_normal = np.mean(final_normals, axis=0)
    final_avg_normal = final_avg_normal / np.linalg.norm(final_avg_normal)
    
    print(f"\nFinal mesh info:")
    print(f"  - Is watertight: {mesh.is_watertight}")
    print(f"  - Is winding consistent: {mesh.is_winding_consistent}")
    print(f"  - Final average normal: {final_avg_normal}")
    print(f"  - Alignment with target: {np.dot(final_avg_normal, target_direction):.4f}")
    
    # Check normal consistency one more time
    target_dots = np.dot(final_normals, target_direction)
    positive_normals = np.sum(target_dots > 0)
    negative_normals = np.sum(target_dots < 0)
    print(f"  - Normals pointing toward target: {positive_normals}")
    print(f"  - Normals pointing away from target: {negative_normals}")
    
    # Step 7: Save the processed mesh
    print(f"\nSaving processed STL to: {output_file}")
    mesh.export(output_file)
    
    # Step 8: Verify the saved file
    if os.path.exists(output_file):
        print(f"Successfully saved! File size: {os.path.getsize(output_file)} bytes")
    else:
        print("Warning: Output file was not created!")
    
    return mesh

def validate_stl_for_openfoam(stl_file, target_direction=np.array([0, 0, 1])):
    """
    Validate STL file for OpenFOAM compatibility.
    
    Parameters:
    -----------
    stl_file : str
        Path to STL file to validate
    target_direction : np.array
        Target direction to check against
    """
    print(f"\nValidating {stl_file} for OpenFOAM compatibility:")
    
    if not os.path.exists(stl_file):
        print(f"File '{stl_file}' not found!")
        return False
    
    mesh = trimesh.load(stl_file)
    
    # Check various properties
    checks = {
        'File exists': os.path.exists(stl_file),
        'Is watertight': mesh.is_watertight,
        'Winding consistent': mesh.is_winding_consistent,
        'Has volume': mesh.volume > 0,
        'No degenerate faces': len(mesh.face_normals) == len(mesh.faces)
    }
    
    print("Validation results:")
    all_good = True
    for check, result in checks.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {check}: {status}")
        if not result:
            all_good = False
    
    # Enhanced normal consistency check
    face_normals = mesh.face_normals
    target_direction = target_direction / np.linalg.norm(target_direction)
    
    # Check alignment with target direction
    normal_dots = np.dot(face_normals, target_direction)
    positive_normals = np.sum(normal_dots > 0)
    negative_normals = np.sum(normal_dots < 0)
    zero_normals = np.sum(np.abs(normal_dots) < 1e-6)
    
    print(f"  Normal direction analysis:")
    print(f"    - Faces pointing toward target (+): {positive_normals}")
    print(f"    - Faces pointing away from target (-): {negative_normals}")
    print(f"    - Faces perpendicular to target (0): {zero_normals}")
    
    # Calculate consistency percentage
    total_faces = len(face_normals)
    if total_faces > 0:
        consistency_ratio = max(positive_normals, negative_normals) / total_faces
        print(f"    - Consistency ratio: {consistency_ratio:.3f}")
        
        if negative_normals == 0:
            print("  ✓ Perfect normal consistency - all normals point toward target")
            normal_consistent = True
        elif positive_normals == 0:
            print("  ✓ Perfect normal consistency - all normals point away from target")
            normal_consistent = True
        elif consistency_ratio > 0.95:
            print(f"  ~ Good normal consistency ({consistency_ratio*100:.1f}%)")
            normal_consistent = True
        else:
            print(f"  ✗ Poor normal consistency - mixed directions detected")
            normal_consistent = False
            all_good = False
    else:
        normal_consistent = False
        all_good = False
    
    return all_good

# Example usage and main execution
if __name__ == "__main__":
    # Define input and output files
    #input_stl = "/Users/omokayj/Library/CloudStorage/OneDrive-MarquetteUniversity/Documents/Inventor/pythonMod/buildingsKilbourn-16th.stl"  # Replace with your input file path
    output_stl = "/Users/omokayj/Library/CloudStorage/OneDrive-MarquetteUniversity/Documents/Inventor/pythonMod/buildingsKilbournCleaned.stl"
    input_stl = "/Users/omokayj/Library/CloudStorage/OneDrive-MarquetteUniversity/Documents/Inventor/pythonMod/buildingsKilbourn-16thAlign2.stl"
    try:
        # Process the STL file
        processed_mesh = fix_stl_normals(
            input_file=input_stl,
            output_file=output_stl,
            target_direction=np.array([0, 0, 1])  # Point normals in +Z direction
        )
        
        # Validate both original and processed files
        print("\n" + "="*60)
        print("VALIDATION SUMMARY")
        print("="*60)
        
        print("\nOriginal file:")
        validate_stl_for_openfoam(input_stl, np.array([0, 0, 1]))
        
        print("\nProcessed file:")
        validate_stl_for_openfoam(output_stl, np.array([0, 0, 1]))
        
        print("\n" + "="*60)
        print("Processing complete!")
        print(f"Use '{output_stl}' in your OpenFOAM case.")
        print("="*60)
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print(f"Please make sure '{input_stl}' exists in the current directory.")
    except Exception as e:
        print(f"An error occurred: {e}")


# Bounding Box: (-352.895 -302.33 630.338) (-213.993 -142.682 669.833)