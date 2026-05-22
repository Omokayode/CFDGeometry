import numpy as np
from stl import mesh
import os

#Aligns STL to extents but stretches if not exact

def get_mesh_bounds(mesh_obj):
    """Get the bounding box of an STL mesh"""
    vertices = mesh_obj.vectors.reshape(-1, 3)
    min_coords = np.min(vertices, axis=0)
    max_coords = np.max(vertices, axis=0)
    return min_coords, max_coords

def get_mesh_size(min_coords, max_coords):
    """Calculate the size (dimensions) of the mesh"""
    return max_coords - min_coords

def align_and_scale_stl(reference_stl_path, target_stl_path, output_stl_path):
    """
    Align and scale target STL to match reference STL
    
    Args:
        reference_stl_path: Path to the reference STL file
        target_stl_path: Path to the STL file to be aligned and scaled
        output_stl_path: Path for the output aligned STL file
    """
    
    # Load the STL files
    print("Loading STL files...")
    reference_mesh = mesh.Mesh.from_file(reference_stl_path)
    target_mesh = mesh.Mesh.from_file(target_stl_path)
    
    # Get bounds for both meshes
    ref_min, ref_max = get_mesh_bounds(reference_mesh)
    target_min, target_max = get_mesh_bounds(target_mesh)
    
    print(f"Reference mesh bounds: Min {ref_min}, Max {ref_max}")
    print(f"Target mesh bounds: Min {target_min}, Max {target_max}")
    
    # Calculate sizes
    ref_size = get_mesh_size(ref_min, ref_max)
    target_size = get_mesh_size(target_min, target_max)
    
    print(f"Reference mesh size: {ref_size}")
    print(f"Target mesh size: {target_size}")
    
    # Calculate scaling factors for each axis
    # Avoid division by zero
    scale_factors = np.where(target_size != 0, ref_size / target_size, 1.0)
    print(f"Scale factors: {scale_factors}")
    
    # Create a copy of the target mesh for transformation
    aligned_mesh = mesh.Mesh(target_mesh.data.copy())
    
    # Step 1: Move target mesh so its min point is at origin
    print("Step 1: Moving target mesh to origin...")
    aligned_mesh.vectors -= target_min
    
    # Step 2: Scale the mesh
    print("Step 2: Scaling mesh...")
    aligned_mesh.vectors *= scale_factors
    
    # Step 3: Move to reference position (align min points)
    print("Step 3: Moving to reference position...")
    aligned_mesh.vectors += ref_min
    
    # Verify alignment
    new_min, new_max = get_mesh_bounds(aligned_mesh)
    print(f"Aligned mesh bounds: Min {new_min}, Max {new_max}")
    print(f"Alignment error: {np.abs(new_min - ref_min)}")
    
    # Save the aligned mesh
    print(f"Saving aligned mesh to: {output_stl_path}")
    aligned_mesh.save(output_stl_path)
    
    return aligned_mesh

def compare_meshes(reference_stl_path, aligned_stl_path):
    """Compare reference and aligned meshes"""
    print("\n" + "="*50)
    print("MESH COMPARISON")
    print("="*50)
    
    reference_mesh = mesh.Mesh.from_file(reference_stl_path)
    aligned_mesh = mesh.Mesh.from_file(aligned_stl_path)
    
    ref_min, ref_max = get_mesh_bounds(reference_mesh)
    aligned_min, aligned_max = get_mesh_bounds(aligned_mesh)
    
    ref_size = get_mesh_size(ref_min, ref_max)
    aligned_size = get_mesh_size(aligned_min, aligned_max)
    
    print(f"Reference - Min: {ref_min}, Max: {ref_max}, Size: {ref_size}")
    print(f"Aligned   - Min: {aligned_min}, Max: {aligned_max}, Size: {aligned_size}")
    
    position_error = np.abs(aligned_min - ref_min)
    size_error = np.abs(aligned_size - ref_size)
    
    print(f"Position error: {position_error}")
    print(f"Size error: {size_error}")
    print(f"Max position error: {np.max(position_error)}")
    print(f"Max size error: {np.max(size_error)}")

def main():
    # Define file paths directly in the code
    reference_stl = "/Users/omokayj/Library/CloudStorage/OneDrive-MarquetteUniversity/vsCode/Research/windAroundBuildings/Tools/output/inUse/geometry/buildingsKilbourn.stl"      # Your original imported building STL
    target_stl = "/Users/omokayj/Library/CloudStorage/OneDrive-MarquetteUniversity/Documents/Inventor/pythonMod/buildingsKilbourn-16th.stl"  # Replace with your input file path
    output_stl = "/Users/omokayj/Library/CloudStorage/OneDrive-MarquetteUniversity/Documents/Inventor/pythonMod/buildingsKilbourn-16thAlign.stl"

    
    print("STL Alignment and Scaling Tool")
    print("=" * 40)
    print(f"Reference STL: {reference_stl}")
    print(f"Target STL: {target_stl}")
    print(f"Output STL: {output_stl}")
    print()
    
    # Check if files exist
    if not os.path.exists(reference_stl):
        print(f"Error: Reference file '{reference_stl}' not found")
        print("Please ensure your original building STL is in the same directory as this script")
        return
    
    if not os.path.exists(target_stl):
        print(f"Error: Target file '{target_stl}' not found")
        print("Please ensure your exported STL from Inventor is in the same directory as this script")
        return
    
    try:
        # Perform alignment and scaling
        aligned_mesh = align_and_scale_stl(reference_stl, target_stl, output_stl)
        print(f"\nSuccess! Aligned STL saved to: {output_stl}")
        
        # Always show comparison
        compare_meshes(reference_stl, output_stl)
        
        print(f"\nYour aligned STL file '{output_stl}' is ready!")
        print("It should now have the exact same position and dimensions as your original building.")
            
    except Exception as e:
        print(f"Error: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure both STL files are valid and not corrupted")
        print("2. Check that you have write permissions in this directory")
        print("3. Ensure the numpy-stl library is installed: pip install numpy-stl")

if __name__ == "__main__":
    main()
  