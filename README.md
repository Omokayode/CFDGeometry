# CFD Geometry

Python package for building **STL geometry** from GIS and elevation data, aimed at **urban wind / OpenFOAM** workflows.

## Install

```bash
cd CFDGeometry
pip install -e .
```

Optional extras: `pip install -e ".[dev]"` or `".[gdal]"` for alternate DEM readers.

## Quick start (CLI)

Compute a shared origin so terrain, buildings, and trees align:

```bash
cfd-geometry offset path/to/buildings.shp path/to/trees.shp
```

Build layers (use the same shapefile list for `--align-with`):

```bash
cfd-geometry buildings buildings.shp -o buildings.stl --align-with buildings.shp trees.shp
cfd-geometry trees trees.shp -o trees.stl --align-with buildings.shp trees.shp
cfd-geometry terrain dem.tif -o terrain.stl --offset-x 424265.04 --offset-y 4765565.05
cfd-geometry clip terrain.stl -o terrain_clipped.stl --bounds -500 -500 300 500 500 720
```

## Python API

```python
from cfd_geometry import (
    get_combined_offset,
    extrude_buildings_to_stl,
    dem_to_stl_with_offset,
    STLClipper,
    OptimizedRectangularBaseGenerator,
)

ox, oy = get_combined_offset(["buildings.shp", "trees.shp"])
extrude_buildings_to_stl("buildings.shp", "buildings.stl", combined_offset=(ox, oy))
dem_to_stl_with_offset("dem.tif", "terrain.stl", ox, oy)
```

## Package layout

```
src/cfd_geometry/
├── geo/          # CRS repair, combined offsets
├── mesh/         # STL I/O, polygon extrusion
├── raster/       # DEM loading and elevation sampling
├── buildings/    # Footprint extrusion + height estimation
├── trees/        # Point trees
├── terrain/      # DEM → terrain STL
├── clipper/      # Bounding-box STL clip
├── base/         # Terrain-fitted solid base
└── cli/          # ``cfd-geometry`` commands
```

## Legacy scripts

Older standalone `.py` files at the repo root and under `legacy/` still exist for reference. Prefer the package and CLI for new work. See [legacy/README.md](legacy/README.md).

## Requirements

- Python 3.9+
- geopandas, shapely, rasterio, numpy, scipy, pandas, pyproj
