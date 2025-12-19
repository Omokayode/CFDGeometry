import geopandas as gpd
import pandas as pd
import numpy as np
import requests
import json
from shapely.geometry import Point, Polygon
import rasterio
from rasterio.mask import mask
import warnings
warnings.filterwarnings('ignore')

def fix_shapefile_crs(shapefile_path):
    """
    Fix missing CRS by reading from .prj file
    """
    buildings = gpd.read_file(shapefile_path)
    
    if buildings.crs is None:
        print("⚠️ No CRS detected. Checking for .prj file...")
        prj_file = shapefile_path.replace('.shp', '.prj')
        try:
            with open(prj_file, 'r') as f:
                prj_content = f.read().strip()
                print(f"Found .prj file content: {prj_content[:100]}...")
                
                # Try to set CRS from .prj file
                buildings = buildings.set_crs(prj_content)
                print(f"✅ CRS set from .prj file: {buildings.crs}")
                
                # Save the shapefile with proper CRS
                buildings.to_file(shapefile_path)
                print(f"✅ Shapefile saved with CRS information")
                
        except FileNotFoundError:
            print(f"❌ No .prj file found at {prj_file}")
            print("🔧 Assuming EPSG:4326 (WGS84). Please verify this is correct.")
            buildings = buildings.set_crs('EPSG:4326')
        except Exception as e:
            print(f"❌ Error reading .prj file: {e}")
            print("🔧 Assuming EPSG:4326 (WGS84). Please verify this is correct.")
            buildings = buildings.set_crs('EPSG:4326')
    
    return buildings

def get_microsoft_building_heights(shapefile_path, output_path=None):
    """
    Download Microsoft Building Footprints with height data for Wisconsin
    Note: You'll need to download the Wisconsin dataset from:
    https://github.com/microsoft/USBuildingFootprints
    """
    
    print("📍 Microsoft Building Footprints Method:")
    print("1. Go to: https://github.com/microsoft/USBuildingFootprints")
    print("2. Download Wisconsin dataset: 'Wisconsin.geojson'")
    print("3. Use the function below to merge with your footprints")
    
    # Example of how to use Microsoft data once downloaded
    microsoft_buildings_path = "Wisconsin.geojson"  # You need to download this
    
    try:
        # Read your building footprints
        your_buildings = gpd.read_file(shapefile_path)
        
        # Read Microsoft building footprints (if available)
        ms_buildings = gpd.read_file(microsoft_buildings_path)
        
        # Ensure same CRS
        if your_buildings.crs != ms_buildings.crs:
            ms_buildings = ms_buildings.to_crs(your_buildings.crs)
        
        # Spatial join to get heights
        # Find Microsoft buildings that intersect with your buildings
        joined = gpd.sjoin_nearest(your_buildings, ms_buildings, 
                                  how='left', max_distance=10)  # 10m tolerance
        
        # Extract height if available in Microsoft data
        if 'height' in ms_buildings.columns:
            your_buildings['ms_height'] = joined['height']
        
        if output_path:
            your_buildings.to_file(output_path)
            
        return your_buildings
        
    except FileNotFoundError:
        print("❌ Microsoft building file not found. Please download from GitHub.")
        return None

def extract_heights_from_lidar_dsm(shapefile_path, dsm_path, output_path=None):
    """
    Extract building heights from LiDAR Digital Surface Model (DSM)
    
    Parameters:
    -----------
    shapefile_path : str
        Path to building footprints shapefile
    dsm_path : str  
        Path to Digital Surface Model raster (LiDAR-derived)
    """
    
    print("🌐 Extracting heights from LiDAR DSM...")
    
    # Read building footprints
    buildings = gpd.read_file(shapefile_path)
    
    # Handle missing CRS
    if buildings.crs is None:
        print("⚠️ No CRS detected. Checking for .prj file...")
        prj_file = shapefile_path.replace('.shp', '.prj')
        try:
            with open(prj_file, 'r') as f:
                prj_content = f.read().strip()
                buildings = buildings.set_crs(prj_content)
                print(f"✅ CRS set from .prj file: {buildings.crs}")
        except FileNotFoundError:
            print("🔧 Assuming EPSG:4326 (WGS84)")
            buildings = buildings.set_crs('EPSG:4326')
    
    # Read DSM raster
    with rasterio.open(dsm_path) as dsm:
        print(f"DSM CRS: {dsm.crs}")
        print(f"DSM bounds: {dsm.bounds}")
        
        # Ensure same CRS
        if buildings.crs != dsm.crs:
            buildings = buildings.to_crs(dsm.crs)
        
        heights = []
        
        for idx, building in buildings.iterrows():
            try:
                # Mask DSM with building polygon
                geom = [building.geometry.__geo_interface__]
                masked_dsm, _ = mask(dsm, geom, crop=True, nodata=np.nan)
                
                # Calculate building height statistics
                building_elevations = masked_dsm[~np.isnan(masked_dsm)]
                
                if len(building_elevations) > 0:
                    # Use various height metrics
                    max_height = np.max(building_elevations)
                    mean_height = np.mean(building_elevations) 
                    percentile_95 = np.percentile(building_elevations, 95)
                    
                    # Use 95th percentile to avoid outliers
                    estimated_height = percentile_95
                else:
                    estimated_height = 12.0  # Default
                    
                heights.append(estimated_height)
                
            except Exception as e:
                print(f"Error processing building {idx}: {e}")
                heights.append(12.0)  # Default height
        
        buildings['lidar_height'] = heights
        
        if output_path:
            buildings.to_file(output_path)
            
        print(f"✅ Extracted heights for {len(buildings)} buildings")
        print(f"Height range: {np.min(heights):.1f}m - {np.max(heights):.1f}m")
        
        return buildings

def download_wisconsin_lidar_info():
    """
    Get information about available LiDAR data for Wisconsin
    """
    
    print("🗺️  Wisconsin LiDAR Data Sources:")
    print("\n1. GeoData@Wisconsin Portal:")
    print("   https://geodata.wisc.edu/")
    print("   - Search for 'LiDAR' or 'elevation'")
    print("   - Download county-specific datasets")
    
    print("\n2. OpenTopography:")
    print("   https://opentopography.org/")
    print("   - Search for Wisconsin datasets")
    print("   - High-resolution point clouds available")
    
    print("\n3. USGS 3D Elevation Program:")
    print("   https://www.usgs.gov/3d-elevation-program")
    print("   - National elevation datasets")
    
    print("\n4. Milwaukee County GIS:")
    print("   https://gis-mclio.opendata.arcgis.com/")
    print("   - Local elevation and LiDAR data")

def estimate_heights_from_footprint_area(shapefile_path, output_path=None):
    """
    Estimate building heights based on footprint area and urban planning rules
    """
    
    print("📐 Estimating heights from building footprint areas...")
    
    buildings = gpd.read_file(shapefile_path)
    
    # Handle missing CRS
    if buildings.crs is None:
        print("⚠️ No CRS detected. Checking for .prj file...")
        prj_file = shapefile_path.replace('.shp', '.prj')
        try:
            with open(prj_file, 'r') as f:
                prj_content = f.read().strip()
                print(f"Found .prj file content: {prj_content[:100]}...")
                
                # Try to set CRS from .prj file
                buildings = buildings.set_crs(prj_content)
                print(f"✅ CRS set from .prj file: {buildings.crs}")
        except FileNotFoundError:
            print(f"❌ No .prj file found at {prj_file}")
            print("🔧 Assuming EPSG:4326 (WGS84). Please verify this is correct.")
            buildings = buildings.set_crs('EPSG:4326')
        except Exception as e:
            print(f"❌ Error reading .prj file: {e}")
            print("🔧 Assuming EPSG:4326 (WGS84). Please verify this is correct.")
            buildings = buildings.set_crs('EPSG:4326')
    
    print(f"Current CRS: {buildings.crs}")
    
    # Calculate footprint area
    if buildings.crs.to_epsg() == 4326:
        # Convert to metric CRS for area calculation
        print("🔄 Converting to UTM Zone 16N for accurate area calculation...")
        buildings_metric = buildings.to_crs('EPSG:32616')  # UTM Zone 16N for Milwaukee
        buildings['area_sqm'] = buildings_metric.geometry.area
    else:
        # Already in a projected CRS, calculate area directly
        buildings['area_sqm'] = buildings.geometry.area
    
    # Height estimation rules (rough approximations)
    def estimate_height(area):
        if area < 100:  # Small buildings (< 100 sqm)
            return 6.0  # Single story
        elif area < 300:  # Medium buildings
            return 9.0  # 1-2 stories
        elif area < 800:  # Large buildings  
            return 15.0  # 2-3 stories
        elif area < 2000:  # Very large buildings
            return 25.0  # 4-6 stories
        else:  # Massive buildings
            return 40.0  # 7+ stories
    
    buildings['estimated_height'] = buildings['area_sqm'].apply(estimate_height)
    
    if output_path:
        buildings.to_file(output_path)
    
    print(f"✅ Estimated heights for {len(buildings)} buildings")
    print("Height distribution:")
    print(buildings['estimated_height'].value_counts().sort_index())
    
    return buildings

def get_osm_building_heights(shapefile_path, output_path=None):
    """
    Try to get building heights from OpenStreetMap data
    """
    try:
        import overpy
    except ImportError:
        print("❌ overpy library not installed. Run: pip install overpy")
        return None
    
    print("🗺️  Querying OpenStreetMap for building heights...")
    
    buildings = gpd.read_file(shapefile_path)
    
    # Handle missing CRS
    if buildings.crs is None:
        print("⚠️ No CRS detected. Checking for .prj file...")
        prj_file = shapefile_path.replace('.shp', '.prj')
        try:
            with open(prj_file, 'r') as f:
                prj_content = f.read().strip()
                buildings = buildings.set_crs(prj_content)
                print(f"✅ CRS set from .prj file: {buildings.crs}")
        except FileNotFoundError:
            print("🔧 Assuming EPSG:4326 (WGS84)")
            buildings = buildings.set_crs('EPSG:4326')
    
    # Convert to WGS84 for OSM query
    if buildings.crs.to_epsg() != 4326:
        buildings_wgs84 = buildings.to_crs('EPSG:4326')
    else:
        buildings_wgs84 = buildings.copy()
    
    # Get bounding box
    bounds = buildings_wgs84.total_bounds
    bbox = f"{bounds[1]},{bounds[0]},{bounds[3]},{bounds[2]}"  # S,W,N,E
    
    api = overpy.Overpass()
    
    try:
        # Query OSM for buildings with height information
        query = f"""
        [out:json][timeout:60];
        (
          way["building"]["height"]({bbox});
          relation["building"]["height"]({bbox});
        );
        out geom;
        """
        
        result = api.query(query)
        
        osm_heights = []
        osm_geoms = []
        
        # Process ways (building polygons)
        for way in result.ways:
            if 'height' in way.tags:
                try:
                    height_str = way.tags['height']
                    # Parse height (could be "15m", "15", "15.5 m", etc.)
                    height = float(''.join(filter(lambda x: x.isdigit() or x == '.', height_str)))
                    
                    # Create polygon from way
                    coords = [(float(node.lon), float(node.lat)) for node in way.nodes]
                    if len(coords) >= 3:
                        poly = Polygon(coords)
                        osm_geoms.append(poly)
                        osm_heights.append(height)
                        
                except (ValueError, AttributeError):
                    continue
        
        if osm_geoms:
            # Create GeoDataFrame of OSM buildings with heights
            osm_buildings = gpd.GeoDataFrame({
                'height': osm_heights,
                'geometry': osm_geoms
            }, crs='EPSG:4326')
            
            # Convert to same CRS as input
            osm_buildings = osm_buildings.to_crs(buildings.crs)
            
            # Spatial join to match OSM heights to your buildings
            joined = gpd.sjoin_nearest(buildings, osm_buildings, 
                                      how='left', max_distance=20)
            
            buildings['osm_height'] = joined['height']
            
            print(f"✅ Found OSM height data for {buildings['osm_height'].notna().sum()} buildings")
        else:
            print("⚠️  No OSM height data found in this area")
            buildings['osm_height'] = np.nan
            
    except Exception as e:
        print(f"❌ OSM query failed: {e}")
        buildings['osm_height'] = np.nan
    
    if output_path:
        buildings.to_file(output_path)
        
    return buildings

def combine_height_sources(shapefile_path, output_path=None):
    """
    Combine multiple height sources to get best estimate
    """
    
    print("🔄 Combining multiple height data sources...")
    
    buildings = gpd.read_file(shapefile_path)
    
    # Try different methods
    print("\n1. Estimating from footprint area...")
    buildings = estimate_heights_from_footprint_area(shapefile_path)
    
    print("\n2. Querying OpenStreetMap...")
    buildings = get_osm_building_heights(shapefile_path)
    
    # Combine sources with priority order
    def get_best_height(row):
        # Priority: OSM > LiDAR > Area estimation
        if pd.notna(row.get('osm_height', np.nan)):
            return row['osm_height']
        elif pd.notna(row.get('lidar_height', np.nan)):
            return row['lidar_height']
        elif pd.notna(row.get('estimated_height', np.nan)):
            return row['estimated_height']
        else:
            return 12.0  # Default
    
    buildings['final_height'] = buildings.apply(get_best_height, axis=1)
    
    if output_path:
        buildings.to_file(output_path)
        
    print(f"\n✅ Final height statistics:")
    print(buildings['final_height'].describe())
    
    return buildings

# Example usage
if __name__ == "__main__":
    
    shapefile = "windAroundBuildings/Tools/input/kilbourntoClybourn.shp"
    
    print("🏢 Building Height Extraction Methods\n")
    
    # Method 1: Download info for LiDAR data
    download_wisconsin_lidar_info()
    
    print("\n" + "="*50)
    
    # Method 2: Estimate from area (quickest method)
    buildings_with_heights = estimate_heights_from_footprint_area(
        shapefile, 
        "windAroundBuildings/Tools/output/buildings_with_estimated_heights.shp"
    )
    
    print("\n" + "="*50)
    
    # Method 3: Try OSM data
    buildings_with_osm = get_osm_building_heights(
        shapefile,
        "windAroundBuildings/Tools/output/buildings_with_osm_heights.shp" 
    )
    
    print("\n" + "="*50)
    
    # Method 4: Combine all sources
    final_buildings = combine_height_sources(
        shapefile,
        "windAroundBuildings/Tools/output/buildings_final_heights.shp"
    )