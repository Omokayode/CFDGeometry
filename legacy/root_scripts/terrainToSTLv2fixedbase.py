
"""
DEM TIFF to STL Converter for OpenFOAM Terrain Modeling
This script converts Digital Elevation Model (DEM) data from TIFF format
to STL format suitable for use in OpenFOAM CFD simulations.
Dependencies:
    pip install rasterio numpy numpy-stl scipy pillow tifffile
Alternative method if rasterio fails:
    pip install gdal
"""
import numpy as np
import rasterio
from stl import mesh
import argparse
import os
from scipy.ndimage import gaussian_filter
import struct
import warnings
from rasterio.transform import from_bounds
from rasterio.warp import reproject, Resampling
warnings.filterwarnings('ignore')

# Optional imports for alternative TIFF reading methods
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import tifffile
    TIFFFILE_AVAILABLE = True
except ImportError:
    TIFFFILE_AVAILABLE = False

try:
    from osgeo import gdal
    GDAL_AVAILABLE = True
except ImportError:
    GDAL_AVAILABLE = False

def load_elevation_raster(tif_path, target_crs='EPSG:32616', resample_factor=1.0):
    """
    Load and process elevation raster from TIF file
    
    Args:
        tif_path: Path to the TIF file
        target_crs: Target coordinate reference system
        resample_factor: Factor to resample the raster (1.0 = original, 0.5 = half resolution)
    
    Returns:
        dict: Contains elevation data, bounds, transform, and other metadata
    """
    print(f"📊 Loading elevation raster: {tif_path}")
    
    try:
        return load_with_rasterio(tif_path, target_crs, resample_factor)
    except Exception as e:
        print(f"Rasterio failed: {e}")
        print("Trying alternative methods...")
        return load_dem_data_alternative(tif_path, target_crs, resample_factor)

def load_with_rasterio(tif_path, target_crs, resample_factor):
    """Load DEM data using rasterio."""
    with rasterio.open(tif_path) as src:
        # Print basic file information
        print(f"TIFF Info:")
        print(f"  - Driver: {src.driver}")
        print(f"  - Data type: {src.dtypes[0]}")
        print(f"  - Band count: {src.count}")
        print(f"  - Width: {src.width}, Height: {src.height}")
        print(f"Original CRS: {src.crs}")
        print(f"Original bounds: {src.bounds}")
        print(f"Original shape: {src.shape}")
        print(f"Original resolution: {src.res}")
        
        # Read elevation data
        elevation = src.read(1)
        original_transform = src.transform
        original_crs = src.crs
        
        # Handle nodata values
        if src.nodata is not None:
            print(f"Handling nodata values: {src.nodata}")
            elevation = np.where(elevation == src.nodata, np.nan, elevation)
        
        # Store original elevation statistics
        orig_min = np.nanmin(elevation)
        orig_max = np.nanmax(elevation)
        orig_range = orig_max - orig_min
        
        print(f"Original elevation range: {orig_min:.2f} to {orig_max:.2f} meters (range: {orig_range:.2f}m)")
        
        # Reproject if necessary
        if str(original_crs) != target_crs:
            print(f"🔄 Reprojecting raster from {original_crs} to {target_crs}")
            
            # Calculate new bounds in target CRS
            from rasterio.warp import transform_bounds
            new_bounds = transform_bounds(original_crs, target_crs, *src.bounds)
            
            # Calculate new dimensions maintaining aspect ratio
            width_m = new_bounds[2] - new_bounds[0]
            height_m = new_bounds[3] - new_bounds[1]
            
            # Use original resolution as reference
            orig_res_x, orig_res_y = src.res
            new_width = int(width_m / (orig_res_x * resample_factor))
            new_height = int(height_m / (orig_res_y * resample_factor))
            
            # Create new transform
            new_transform = from_bounds(*new_bounds, new_width, new_height)
            
            # Reproject the data
            elevation_reproj = np.empty((new_height, new_width), dtype=elevation.dtype)
            
            reproject(
                source=elevation,
                destination=elevation_reproj,
                src_transform=original_transform,
                src_crs=original_crs,
                dst_transform=new_transform,
                dst_crs=target_crs,
                resampling=Resampling.bilinear
            )
            
            # Check if reprojection corrupted elevation values
            reproj_min = np.nanmin(elevation_reproj)
            reproj_max = np.nanmax(elevation_reproj)
            reproj_range = reproj_max - reproj_min
            
            print(f"Reprojected elevation range: {reproj_min:.2f} to {reproj_max:.2f} (range: {reproj_range:.2f}m)")
            
            # Fix elevation range if reprojection corrupted it
            if reproj_min < (orig_min - 50) or abs(reproj_range - orig_range) > (orig_range * 0.1):
                print(f"⚠️  Reprojection corrupted elevation values!")
                print(f"   Restoring original elevation range...")
                
                # Normalize reprojected data to 0-1 range
                reproj_normalized = (elevation_reproj - reproj_min) / reproj_range
                
                # Scale to original range
                elevation_reproj = reproj_normalized * orig_range + orig_min
                
                corrected_min = np.nanmin(elevation_reproj)
                corrected_max = np.nanmax(elevation_reproj)
                print(f"   Corrected range: {corrected_min:.2f} to {corrected_max:.2f}m")
            
            elevation = elevation_reproj
            transform = new_transform
            bounds = new_bounds
            
        else:
            # Same CRS, just resample if requested
            if resample_factor != 1.0:
                new_width = int(src.width * resample_factor)
                new_height = int(src.height * resample_factor)
                
                bounds = src.bounds
                transform = from_bounds(*bounds, new_width, new_height)
                
                elevation_resampled = np.empty((new_height, new_width), dtype=elevation.dtype)
                
                reproject(
                    source=elevation,
                    destination=elevation_resampled,
                    src_transform=original_transform,
                    src_crs=original_crs,
                    dst_transform=transform,
                    dst_crs=target_crs,
                    resampling=Resampling.bilinear
                )
                
                elevation = elevation_resampled
            else:
                transform = original_transform
                bounds = src.bounds
        
        # Get spatial resolution
        pixel_width = abs(transform.a) if transform.a != 0 else 1.0
        pixel_height = abs(transform.e) if transform.e != 0 else 1.0
        
        print(f"Final raster shape: {elevation.shape}")
        print(f"Final bounds: {bounds}")
        print(f"Final elevation range: {np.nanmin(elevation):.2f} to {np.nanmax(elevation):.2f} meters")
        print(f"Pixel resolution: {pixel_width:.6f} x {pixel_height:.6f}")
        
        return {
            'elevation': elevation,
            'bounds': bounds,
            'transform': transform,
            'pixel_width': pixel_width,
            'pixel_height': pixel_height,
            'width': elevation.shape[1],
            'height': elevation.shape[0],
            'crs': target_crs,
            'shape': elevation.shape
        }

def load_dem_data_alternative(tif_path, target_crs, resample_factor):
    """Alternative methods to load DEM data when rasterio fails."""
    print("Trying alternative TIFF reading methods...")
    
    elevation = None
    
    # Method A: Using tifffile
    if TIFFFILE_AVAILABLE and elevation is None:
        try:
            print("Trying tifffile...")
            elevation = tifffile.imread(tif_path)
            print(f"tifffile read successful: shape={elevation.shape}")
            
            # Handle multi-band or 3D data
            if elevation.ndim == 3:
                if elevation.shape[0] == 1:  # Single band
                    elevation = elevation[0]
                else:  # Multiple bands, take first
                    elevation = elevation[:, :, 0] if elevation.shape[2] < elevation.shape[0] else elevation[0]
                print(f"Extracted 2D data: shape={elevation.shape}")
            
        except Exception as e:
            print(f"tifffile failed: {e}")
            elevation = None
    
    # Method B: Using PIL (Pillow)
    if PIL_AVAILABLE and elevation is None:
        try:
            print("Trying PIL/Pillow...")
            with Image.open(tif_path) as img:
                elevation = np.array(img)
                print(f"PIL read successful: shape={elevation.shape}")
                
                # Handle multi-band data
                if elevation.ndim == 3:
                    elevation = elevation[:, :, 0]  # Take first band
                    print(f"Using first band: shape={elevation.shape}")
                
        except Exception as e:
            print(f"PIL failed: {e}")
            elevation = None
    
    # Method C: Using GDAL
    if GDAL_AVAILABLE and elevation is None:
        try:
            print("Trying GDAL...")
            dataset = gdal.Open(tif_path)
            if dataset is not None:
                band = dataset.GetRasterBand(1)
                elevation = band.ReadAsArray()
                print(f"GDAL read successful: shape={elevation.shape}")
                
                # Get geospatial information from GDAL
                geotransform = dataset.GetGeoTransform()
                if geotransform:
                    pixel_width = abs(geotransform[1])
                    pixel_height = abs(geotransform[5])
                else:
                    pixel_width = 1.0
                    pixel_height = 1.0
                    
                dataset = None  # Close dataset
                
        except Exception as e:
            print(f"GDAL failed: {e}")
            elevation = None
    
    if elevation is None:
        raise ValueError("All alternative TIFF reading methods failed. "
                       "Please ensure your TIFF file is valid and try converting it with GDAL first.")
    
    # Set default spatial properties when using alternative methods
    pixel_width = 1.0
    pixel_height = 1.0
    
    # Create approximate bounds (will need to be adjusted with offset)
    bounds = (0, 0, elevation.shape[1] * pixel_width, elevation.shape[0] * pixel_height)
    
    return {
        'elevation': elevation,
        'bounds': bounds,
        'transform': None,
        'pixel_width': pixel_width,
        'pixel_height': pixel_height,
        'width': elevation.shape[1],
        'height': elevation.shape[0],
        'crs': target_crs,
        'shape': elevation.shape
    }

def preprocess_elevation(elevation_data, smooth_sigma=0, max_resolution=None, vertical_scale=1.0):
    """Preprocess elevation data (smoothing, downsampling, etc.)."""
    print("Preprocessing elevation data...")
    
    elevation = elevation_data['elevation'].copy()
    
    # Handle NaN values by interpolation or filling
    if np.any(np.isnan(elevation)):
        print("Handling NaN values in elevation data...")
        # Simple approach: replace NaN with mean elevation
        mean_elevation = np.nanmean(elevation)
        elevation = np.where(np.isnan(elevation), mean_elevation, elevation)
    
    # Downsample if requested
    if max_resolution and max(elevation.shape) > max_resolution:
        factor = max(elevation.shape) // max_resolution
        elevation = elevation[::factor, ::factor]
        print(f"Downsampled to shape: {elevation.shape}")
        
        # Update elevation data
        elevation_data = elevation_data.copy()
        elevation_data['elevation'] = elevation
        elevation_data['shape'] = elevation.shape
        elevation_data['height'] = elevation.shape[0]
        elevation_data['width'] = elevation.shape[1]
        elevation_data['pixel_width'] *= factor
        elevation_data['pixel_height'] *= factor
    
    # Apply smoothing if requested
    if smooth_sigma > 0:
        print(f"Applying Gaussian smoothing (sigma={smooth_sigma})...")
        elevation = gaussian_filter(elevation, sigma=smooth_sigma)
    
    # Apply vertical scaling
    if vertical_scale != 1.0:
        print(f"Applying vertical scaling factor: {vertical_scale}")
        elevation = elevation * vertical_scale
    
    elevation_data['elevation'] = elevation
    return elevation_data

def create_terrain_mesh_with_offset(elevation_data, offset_x, offset_y, scale_factor=1.0):
    """Create 3D mesh coordinates from elevation data with coordinate offset."""
    elevation = elevation_data['elevation']
    pixel_width = elevation_data['pixel_width']
    pixel_height = elevation_data['pixel_height']
    bounds = elevation_data['bounds']
    
    rows, cols = elevation.shape
    
    # Create coordinate grids using the bounds and applying offset
    x_coords = np.linspace(bounds[0] - offset_x, bounds[2] - offset_x, cols) * scale_factor
    y_coords = np.linspace(bounds[3] - offset_y, bounds[1] - offset_y, rows) * scale_factor
    
    # Create meshgrid
    X, Y = np.meshgrid(x_coords, y_coords)
    Z = elevation
    
    print(f"Created terrain mesh:")
    print(f"  X range: [{X.min():.2f}, {X.max():.2f}]")
    print(f"  Y range: [{Y.min():.2f}, {Y.max():.2f}]")
    print(f"  Z range: [{Z.min():.2f}, {Z.max():.2f}]")
    
    return X, Y, Z

def create_triangular_mesh(X, Y, Z):
    """Create triangular mesh from grid coordinates."""
    print("Creating triangular mesh...")
    
    rows, cols = X.shape
    triangles = []
    
    # Create triangular faces
    for i in range(rows - 1):
        for j in range(cols - 1):
            # Current vertices
            v1 = [X[i, j], Y[i, j], Z[i, j]]
            v2 = [X[i, j + 1], Y[i, j + 1], Z[i, j + 1]]
            v3 = [X[i + 1, j], Y[i + 1, j], Z[i + 1, j]]
            v4 = [X[i + 1, j + 1], Y[i + 1, j + 1], Z[i + 1, j + 1]]
            
            # Create two triangles per grid cell (counter-clockwise for upward normal)
            triangles.append([v1, v3, v2])  # Upper triangle
            triangles.append([v2, v3, v4])  # Lower triangle
    
    print(f"Created mesh with {len(triangles)} triangles")
    
    return triangles

def add_base_and_sides(triangles, base_thickness=1.0):
    """Add base and side walls to create a solid terrain block with fixed 1m base thickness."""
    print(f"Adding base and side walls with {base_thickness}m base thickness...")
    
    if not triangles:
        return triangles
    
    # Get all unique vertices and find bounds
    all_vertices = []
    for triangle in triangles:
        all_vertices.extend(triangle)
    
    all_vertices = np.array(all_vertices)
    
    min_x, max_x = np.min(all_vertices[:, 0]), np.max(all_vertices[:, 0])
    min_y, max_y = np.min(all_vertices[:, 1]), np.max(all_vertices[:, 1])
    min_z = np.min(all_vertices[:, 2])
    
    # Base at terrain minimum minus base thickness
    base_z = min_z - base_thickness
    
    print(f"Base will be at Z = {base_z:.2f} (terrain minimum: {min_z:.2f})")
    
    # Create base vertices (corners of the terrain)
    base_vertices = [
        [min_x, min_y, base_z],
        [max_x, min_y, base_z],
        [max_x, max_y, base_z],
        [min_x, max_y, base_z]
    ]
    
    # Create base triangles (bottom surface)
    base_triangles = [
        [base_vertices[0], base_vertices[2], base_vertices[1]],  # Triangle 1
        [base_vertices[0], base_vertices[3], base_vertices[2]]   # Triangle 2
    ]
    
    # Add base triangles
    triangles.extend(base_triangles)
    
    print(f"Added base with {len(base_triangles)} triangles")
    
    return triangles

def calculate_normal(triangle):
    """Calculate unit normal vector for triangle"""
    p1, p2, p3 = triangle
    v1 = np.array(p2) - np.array(p1)
    v2 = np.array(p3) - np.array(p1)
    normal = np.cross(v1, v2)
    norm = np.linalg.norm(normal)
    return normal / norm if norm > 1e-10 else np.array([0, 0, 1])

def write_stl_binary(filename, triangles):
    """Write triangles to binary STL file"""
    print(f"Writing STL file: {filename}")
    
    with open(filename, 'wb') as f:
        header = b'Terrain STL with Elevation for OpenFOAM'
        f.write(header + b'\0' * (80 - len(header)))
        
        f.write(struct.pack('<I', len(triangles)))
        
        for triangle in triangles:
            normal = calculate_normal(triangle)
            f.write(struct.pack('<fff', float(normal[0]), float(normal[1]), float(normal[2])))
            
            for vertex in triangle:
                f.write(struct.pack('<fff', float(vertex[0]), float(vertex[1]), float(vertex[2])))
            
            f.write(struct.pack('<H', 0))

def dem_to_stl_with_offset(input_file, output_file, offset_x, offset_y,
                          scale_factor=1.0, vertical_scale=1.0, smooth_sigma=0, 
                          max_resolution=None, add_base=True, target_crs='EPSG:32616'):
    """
    Convert DEM TIFF to STL with coordinate offset for alignment
    
    Args:
        input_file: Path to input DEM TIFF file
        output_file: Path to output STL file
        offset_x, offset_y: Coordinate offset for alignment
        scale_factor: Horizontal scaling factor
        vertical_scale: Vertical scaling factor for elevation
        smooth_sigma: Gaussian smoothing sigma (0 = no smoothing)
        max_resolution: Maximum resolution to downsample to
        add_base: Whether to add base and side walls
        target_crs: Target coordinate reference system
    
    Returns:
        dict: Processing statistics and results
    """
    
    print(f"🏔️ Converting DEM to STL with offset")
    print(f"Input file: {input_file}")
    print(f"Output file: {output_file}")
    print(f"Offset: ({offset_x}, {offset_y})")
    
    # Load elevation data
    elevation_data = load_elevation_raster(input_file, target_crs)
    
    # Preprocess elevation
    elevation_data = preprocess_elevation(
        elevation_data, 
        smooth_sigma=smooth_sigma, 
        max_resolution=max_resolution, 
        vertical_scale=vertical_scale
    )
    
    # Create mesh grid with offset
    X, Y, Z = create_terrain_mesh_with_offset(elevation_data, offset_x, offset_y, scale_factor)
    
    # Create triangular mesh
    triangles = create_triangular_mesh(X, Y, Z)
    
    # Add base and sides if requested
    if add_base:
        triangles = add_base_and_sides(triangles)
    
    # Write STL file
    write_stl_binary(output_file, triangles)
    
    # Calculate final bounds
    if triangles:
        all_points = np.array([point for triangle in triangles for point in triangle])
        bounds = {
            'x_min': all_points[:, 0].min(),
            'x_max': all_points[:, 0].max(),
            'y_min': all_points[:, 1].min(), 
            'y_max': all_points[:, 1].max(),
            'z_min': all_points[:, 2].min(),
            'z_max': all_points[:, 2].max()
        }
    else:
        bounds = {}
    
    # Prepare results
    result = {
        'triangles_generated': len(triangles),
        'bounds': bounds,
        'coordinate_system': elevation_data['crs'],
        'offset_used': (offset_x, offset_y),
        'original_shape': elevation_data['shape'],
        'pixel_resolution': (elevation_data['pixel_width'], elevation_data['pixel_height']),
        'elevation_range': {
            'min': float(np.min(Z)),
            'max': float(np.max(Z)),
            'range': float(np.max(Z) - np.min(Z))
        }
    }
    
    print(f"\n✅ Terrain processing complete!")
    print(f"✅ Generated {len(triangles)} triangles")
    print(f"✅ STL file written to: {output_file}")
    
    # Print statistics
    print(f"\nTerrain Statistics:")
    print(f"Original raster shape: {elevation_data['shape']}")
    print(f"Elevation range: {result['elevation_range']['min']:.1f} to {result['elevation_range']['max']:.1f} meters ({result['elevation_range']['range']:.1f}m range)")
    
    # Print bounds
    if bounds:
        print(f"\nTerrain mesh bounds:")
        print(f"X: [{bounds['x_min']:.2f}, {bounds['x_max']:.2f}]")
        print(f"Y: [{bounds['y_min']:.2f}, {bounds['y_max']:.2f}]") 
        print(f"Z: [{bounds['z_min']:.2f}, {bounds['z_max']:.2f}]")
    
    return result

def main():
    """Command line interface."""
    parser = argparse.ArgumentParser(description='Convert DEM TIFF to STL for OpenFOAM')
    parser.add_argument('input_file', help='Input DEM TIFF file')
    parser.add_argument('-o', '--output', help='Output STL file')
    parser.add_argument('--offset-x', type=float, required=True, help='X coordinate offset')
    parser.add_argument('--offset-y', type=float, required=True, help='Y coordinate offset')
    parser.add_argument('-s', '--scale', type=float, default=1.0, 
                       help='Horizontal scale factor (default: 1.0)')
    parser.add_argument('-v', '--vertical-scale', type=float, default=1.0,
                       help='Vertical scale factor (default: 1.0)')
    parser.add_argument('--smooth', type=float, default=0,
                       help='Gaussian smoothing sigma (default: 0)')
    parser.add_argument('--max-res', type=int,
                       help='Maximum resolution for downsampling')
    parser.add_argument('--no-base', action='store_true',
                       help='Do not add base and sides')
    parser.add_argument('--crs', default='EPSG:32616',
                       help='Target coordinate reference system (default: EPSG:32616)')
    
    args = parser.parse_args()
    
    # Generate output filename if not provided
    if not args.output:
        base = os.path.splitext(args.input_file)[0]
        args.output = f"{base}_terrain.stl"
    
    # Convert
    result = dem_to_stl_with_offset(
        input_file=args.input_file,
        output_file=args.output,
        offset_x=args.offset_x,
        offset_y=args.offset_y,
        scale_factor=args.scale,
        vertical_scale=args.vertical_scale,
        smooth_sigma=args.smooth,
        max_resolution=args.max_res,
        add_base=not args.no_base,
        target_crs=args.crs
    )
    
    print(f"\n📊 Final Summary:")
    for k, v in result.items():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    # Example usage matching the highway code pattern
    
    # Define paths
    # input_file = "/mnt/nas/vsCode/resources/urbanWindFlow/Tools/input/demdataforground/demdataforground.tif"  
    # output_file = "/mnt/nas/vsCode/resources/urbanWindFlow/Tools/output/terrainKilbourn.stl"  

    input_file ="/mnt/nas/vsCode/resources/urbanWindFlow/Tools/input/terrainwithclearance/terrainwithclearance.tif"
    output_file = "/mnt/nas/vsCode/resources/urbanWindFlow/Tools/output/terrainMarquettev2Fixedbase.stl"  

    # Offset values (use your hardcoded values to match highway alignment)
    HARDCODED_OFFSET = (424265.04, 4765565.05)  
    
    # Check if files exist
    if not os.path.exists(input_file):
        print(f"❌ Elevation TIF file not found: {input_file}")
        print("Please update the input_file path to your actual TIF file.")
        exit(1)
    
    # Generate terrain STL with offset
    result = dem_to_stl_with_offset(
        input_file=input_file,
        output_file=output_file,
        offset_x=HARDCODED_OFFSET[0],
        offset_y=HARDCODED_OFFSET[1],
        scale_factor=1.0,              # Horizontal scaling
        vertical_scale=1.0,            # Vertical scaling
        smooth_sigma=0,                # No smoothing
        max_resolution=None,           # No downsampling
        add_base=True,                 # Add base for solid geometry
        target_crs='EPSG:32616'        # Match highway CRS
    )
    
    print(f"\n📊 Final Summary:")
    for k, v in result.items():
        print(f"  {k}: {v}")