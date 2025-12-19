# Tools

This directory contains various tools and utilities for wind around buildings research.

## Overview

The tools in this folder assist with analysis, data processing, and visualization related to wind flow patterns around building structures. They support converting GIS and raster data to STL files, generating terrain and building models, and processing height and offset data.

## Available Tools

### Main Scripts
#### Example Folder Structure

```plaintext
Tools/
├── baseGenerator.py
├── basewTerrainFast.py
├── buildingstoSTLTestHeightCombinedOffset.py
├── highwaytoSTLHardoffset.py
├── highwaywRaster.py
├── offsets.py
├── stlClipper.py
├── stlClipperwBase.py
├── terraintoSTL.py
├── terraintoSTL2fixedbase.py
├── treestoSTLCombinedOffset.py
├── workingVersion/
│   ├── basewTerrainFast.py
│   ├── buildingstoSTL.py
│   ├── highwaytoSTL.py
│   ├── stlClipper.py
│   └── treestoSTL.py
└── wRaster/
    ├── buildingwRaster.py
    ├── highwaywRaster.py
    ├── terrainatoSTL.py
    └── treeswRaster.py
└── deprecated/
    ├── basewTerrainSlow.py
    ├── buildingstoSTLFanTwEstHeights.py
    ├── buildingstoSTLFanTriangulation.py
    ├── highwaytoSTL.py
    ├── treestoSTL.py
```


### Main Dir
- [**baseGenerator.py**](baseGenerator.py)  
    - Generates a rectangular base in STL format that can be added to existing terrain.
    - Output: STL file with a rectangular base.

- [**basewTerrainFast.py**](basewTerrainFast.py)  
    - Quickly generates base terrain data using raster inputs.
    - Accepts a clipped terrain as input.
    - Creates a base for the terrain using a retriangulation method for faster processing.

- [**basewTerrainSlow.py**](basewTerrainSlow.py)  
    - Accepts a clipped terrain as input.
    - Computes all triangles for the base, resulting in slower processing but potentially higher accuracy.

- [**buildingstoSTL.py**](buildingstoSTL.py)  
    - Converts building data into STL files for 3D modeling.
    - Accepts a shapefile (`.shp`) as input.
    - Projects building footprints for export.

- [**buildingstoSTLTestHeightCombinedOffset.py**](buildingstoSTLTestHeightCombinedOffset.py)  
    - Converts building data to STL format.
    - Tests combined height and offset calculations.
    - Accepts a shapefile (`.shp`) as input.
    - Projects building footprints for export.

- [**getBuildingHeight.py**](getBuildingHeight.py)  
    - Extracts or calculates building heights from input data.

- [**highwaywRaster.py**](highwaywRaster.py)  
    - Processes highway data using raster inputs.


- [**offsets.py**](offsets.py)  
    - Handles offset calculations for terrain, buildings, or highways.

- [**stlClipper.py**](stlClipper.py)  
    - Clips or modifies STL files, possibly for fitting or trimming models.

- [**stlClipperwBase.py**](stlClipperwBase.py)  
    - Clips STL files with reference and adds a base to it.
    - It takes in the terrain STL as input and creates a clipped terrain with a fitted base.

- [**terrainatoSTL.py**](terrainatoSTL.py)  
    - Converts terrain raster data into STL files.
    - Accepts 1 meter elevation DEM as input.
    - Returns an STL format for the terrain as output.


- [**terraintoSTL2fixedbase.py**](terraintoSTL2fixedbase.py)  
    - Converts terrain raster data to STL with a fixed base.

- [**treestoSTLCombinedOffset.py**](treestoSTLCombinedOffset.py)  
    - Converts tree data to STL with combined offset handling.

### wRaster Subdirectory
 
 <strong>All the code in this sub dir is terrain aware. It offsets by the height of the terrain from sea level and adds relative elevation for buildings, trees or highways present in the domain.</strong>

 
- [**wRaster/buildingwRaster.py**](wRaster/buildingwRaster.py)  
    Processes building data using raster inputs.

- [**wRaster/highwaywRaster.py**](wRaster/highwaywRaster.py)  
    Processes highway data using raster inputs.

- [**wRaster/terrainatoSTL.py**](wRaster/terrainatoSTL.py)  
    Converts raster terrain data to STL format.

- [**wRaster/treeswRaster.py**](wRaster/treeswRaster.py)  
    Processes tree data using raster inputs.

### workingVersion Subdirectory
 
 <strong>All the code in this sub dir is a working clone of what is available in the main dir. It serves as backup for what works.</strong>

- [**basewTerrainFast.py**](workingVersion/basewTerrainFast.py)  
    - Quickly generates base terrain data using raster inputs.

- [**buildingstoSTL.py**](workingVersion/buildingstoSTL.py)  
    - Converts building data into STL files for 3D modeling.

- [**highwaytoSTL.py**](workingVersion/highwaytoSTL.py)  
    - Converts highway or road data into STL files.

- [**stlClipper.py**](workingVersion/stlClipper.py)  
    - Clips or modifies STL files.

- [**treestoSTL.py**](workingVersion/treestoSTL.py)  
    - Converts tree or vegetation data into STL files.


### Deprecated

   
- [**buildingstoSTLFanTwEstHeights.py**](buildingstoSTLFanTwEstHeights.py)  
    - Converts building data to STL using a fan triangulation method with estimated heights.<br>
    -  <span style="color:red"> **_Deprecated: Consider this script outdated and use alternatives if possible._**

- [**buildingstoSTLFanTriangulation.py**](buildingstoSTLFanTriangulation.py)  
    - Converts building data to STL using fan triangulation.
    - Basic level, does not get the height of buildings and no offset due to terrain
    - <span style="color:red">**_Deprecated: Consider this script outdated and use alternatives if possible._**

- [**highwaytoSTL.py**](highwaytoSTL.py)  
    - Converts highway or road data into STL files.
    - <span style="color:red">**_Deprecated: Consider this script outdated and use alternatives if possible._**

- [**highwaytoSTLHardoffset.py**](highwaytoSTLHardoffset.py)  
    - Converts highway data to STL with hardcoded offsets.
    - this is not terrain aware
    - <span style="color:red">**_Deprecated: Consider this script outdated and use alternatives if possible._**

- [**highwaywSTL.py**](highwaywSTL.py)  
    - Converts highway raster data to STL format.
    - <span style="color:red">**_Deprecated: Consider this script outdated and use alternatives if possible._**

- [**treestoSTL.py**](treestoSTL.py)  
    - Converts tree or vegetation data into STL files.
    - <span style="color:red">**_Deprecated: Consider this script outdated and use alternatives if possible._**
    
## Usage

Each tool may have its own specific usage instructions. Refer to individual tool documentation or comments within the source code for detailed usage information.

## Requirements

- Check individual tool files for specific dependencies and requirements.
- Ensure proper environment setup before running tools.

## Contributing

When adding new tools to this directory:
1. Include clear documentation.
2. Add appropriate comments in code.
3. Update this README with tool descriptions.
4. Test thoroughly before committing.

