import numpy as np
from stl import mesh
import os

#aligns STL with reference STL without stretching to extents

def get_mesh_bounds(mesh_obj):
    """Get the bounding box of an STL mesh"""
    vertices = mesh_obj.vectors.reshape(-1, 3)
    min_coords = np.min(vertices, axis=0)
    max_coords = np.max(vertices, axis=0)
    return min_coords, max_coords

def get_mesh_size(min_coords, max_coords):
    """Calculate the size (dimensions) of the mesh"""
    return max_coords - min_coords

def align_stl_position_only(reference_stl_path, target_stl_path, output_stl_path, 
                           reference_units="m", target_units="inches"):
    """
    Align target STL position to match reference STL, but preserve target's size
    (useful when target is a section/portion of the reference)
    
    Args:
        reference_stl_path: Path to the reference STL file (in meters)
        target_stl_path: Path to the STL file to be aligned (in inches)
        output_stl_path: Path for the output aligned STL file
        reference_units: Units of reference STL ("m", "mm", "inches")
        target_units: Units of target STL ("m", "mm", "inches")
    """
    # Unit conversion factors (to meters)
    unit_conversions = {
        "m": 1.0,
        "mm": 0.001,
        "inches": 0.0254,
        "in": 0.0254
    }
    
    print("Loading STL files...")
    print(f"Reference STL units: {reference_units}")
    print(f"Target STL units: {target_units}")
    
    reference_mesh = mesh.Mesh.from_file(reference_stl_path)
    target_mesh = mesh.Mesh.from_file(target_stl_path)
    
    # Convert both meshes to the same units (meters) for comparison
    ref_to_meters = unit_conversions[reference_units]
    target_to_meters = unit_conversions[target_units]
    
    # Apply unit conversion to get actual dimensions in meters
    reference_mesh_meters = mesh.Mesh(reference_mesh.data.copy())
    reference_mesh_meters.vectors *= ref_to_meters
    
    target_mesh_meters = mesh.Mesh(target_mesh.data.copy())
    target_mesh_meters.vectors *= target_to_meters
    
    # Get bounds for both meshes (now in meters)
    ref_min, ref_max = get_mesh_bounds(reference_mesh_meters)
    target_min, target_max = get_mesh_bounds(target_mesh_meters)
    
    print(f"Reference mesh bounds (meters): Min {ref_min}, Max {ref_max}")
    print(f"Target mesh bounds (meters): Min {target_min}, Max {target_max}")
    
    # Calculate sizes
    ref_size = get_mesh_size(ref_min, ref_max)
    target_size = get_mesh_size(target_min, target_max)
    
    print(f"Reference mesh size (meters): {ref_size}")
    print(f"Target mesh size (meters): {target_size}")
    print("NOTE: Target size will be preserved (no scaling applied)")
    
    # Create a copy of the target mesh for transformation
    aligned_mesh = mesh.Mesh(target_mesh.data.copy())
    
    # Step 1: Convert units only (from inches to meters, matching reference units)
    print(f"Step 1: Converting from {target_units} to {reference_units}...")
    unit_conversion_factor = target_to_meters / ref_to_meters
    aligned_mesh.vectors *= unit_conversion_factor
    
    # Get bounds after unit conversion
    converted_min, converted_max = get_mesh_bounds(aligned_mesh)
    print(f"After unit conversion - Min: {converted_min}, Max: {converted_max}")
    converted_size = get_mesh_size(converted_min, converted_max)
    print(f"After unit conversion - Size: {converted_size}")
    
    # Step 2: Align position (move target's min point to reference's min point)
    print("Step 2: Aligning position...")
    position_offset = ref_min - converted_min
    aligned_mesh.vectors += position_offset
    
    # Verify alignment
    new_min, new_max = get_mesh_bounds(aligned_mesh)
    new_size = get_mesh_size(new_min, new_max)
    print(f"Final aligned mesh bounds: Min {new_min}, Max {new_max}")
    print(f"Final aligned mesh size: {new_size}")
    print(f"Position alignment error: {np.abs(new_min - ref_min)}")
    
    # Save the aligned mesh
    print(f"Saving aligned mesh to: {output_stl_path}")
    aligned_mesh.save(output_stl_path)
    
    return aligned_mesh

def align_stl_with_custom_scaling(reference_stl_path, target_stl_path, output_stl_path, 
                                 custom_scale_factors=None, reference_units="m", target_units="inches"):
    """
    Align target STL with custom scaling factors
    
    Args:
        reference_stl_path: Path to the reference STL file
        target_stl_path: Path to the STL file to be aligned
        output_stl_path: Path for the output aligned STL file
        custom_scale_factors: [x_scale, y_scale, z_scale] or single value for uniform scaling
        reference_units: Units of reference STL
        target_units: Units of target STL
    """
    # Unit conversion factors (to meters)
    unit_conversions = {
        "m": 1.0,
        "mm": 0.001,
        "inches": 0.0254,
        "in": 0.0254
    }
    
    print("Loading STL files...")
    reference_mesh = mesh.Mesh.from_file(reference_stl_path)
    target_mesh = mesh.Mesh.from_file(target_stl_path)
    
    # Convert units
    ref_to_meters = unit_conversions[reference_units]
    target_to_meters = unit_conversions[target_units]
    
    # Get reference bounds
    ref_min, ref_max = get_mesh_bounds(reference_mesh)
    ref_min *= ref_to_meters
    ref_max *= ref_to_meters
    
    # Create aligned mesh
    aligned_mesh = mesh.Mesh(target_mesh.data.copy())
    
    # Step 1: Unit conversion
    unit_conversion_factor = target_to_meters / ref_to_meters
    aligned_mesh.vectors *= unit_conversion_factor
    
    # Step 2: Apply custom scaling if provided
    if custom_scale_factors is not None:
        if np.isscalar(custom_scale_factors):
            custom_scale_factors = [custom_scale_factors] * 3
        print(f"Applying custom scale factors: {custom_scale_factors}")
        aligned_mesh.vectors *= custom_scale_factors
    
    # Step 3: Position alignment
    target_min, target_max = get_mesh_bounds(aligned_mesh)
    position_offset = ref_min - target_min
    aligned_mesh.vectors += position_offset
    
    # Save and return
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
    size_difference = aligned_size - ref_size
    
    print(f"Position error: {position_error}")
    print(f"Size difference: {size_difference}")
    print(f"Max position error: {np.max(position_error)}")

def main():
    # Define file paths
    reference_stl = "/Users/omokayj/Library/CloudStorage/OneDrive-MarquetteUniversity/vsCode/Research/windAroundBuildings/Tools/output/inUse/geometry/buildingsKilbourn.stl"      # Your original imported building STL
    target_stl = "/Users/omokayj/Library/CloudStorage/OneDrive-MarquetteUniversity/Documents/Inventor/pythonMod/buildingsKilbourn-16th.stl"  # Replace with your input file path
    output_stl = "/Users/omokayj/Library/CloudStorage/OneDrive-MarquetteUniversity/Documents/Inventor/pythonMod/buildingsKilbourn-16thAlign2.stl"

    print("STL Alignment Tool - Multiple Options")
    print("=" * 40)
    print(f"Reference STL: {reference_stl}")
    print(f"Target STL: {target_stl}")
    print(f"Output STL: {output_stl}")
    print()
    
    # Check if files exist
    if not os.path.exists(reference_stl):
        print(f"Error: Reference file '{reference_stl}' not found")
        return
    
    if not os.path.exists(target_stl):
        print(f"Error: Target file '{target_stl}' not found")
        return
    
    try:
        print("Choose alignment option:")
        print("1. Position-only alignment (preserve target size - recommended for partial buildings)")
        print("2. Custom scaling + position alignment")
        print("3. Original full scaling (your current approach)")
        
        # For now, defaulting to option 1 (position-only)
        # You can modify this or add input() to make it interactive
        
        print("\nUsing Option 1: Position-only alignment")
        print("This will preserve your section's size but align it with the reference position.")
        
        aligned_mesh = align_stl_position_only(reference_stl, target_stl, output_stl, 
                                             reference_units="m", target_units="inches")
        
        print(f"\nSuccess! Aligned STL saved to: {output_stl}")
        
        # Show comparison
        compare_meshes(reference_stl, output_stl)
        
        print(f"\nYour aligned STL file is ready!")
        print("The building section now has the correct position and units, but preserves its original size.")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()