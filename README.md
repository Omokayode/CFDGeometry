# CFD Geometry

Python package for building **STL geometry** from GIS and elevation data, aimed at **urban wind / OpenFOAM** workflows.

## Install

```bash
cd CFDGeometry
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Optional extras:

- `pip install -e ".[download]"` — auto-download OSM shapefiles (and optional DEM) via OSMnx
- `pip install -e ".[gdal]"` — alternate DEM readers when rasterio cannot open a file

Without installing, run modules with `PYTHONPATH=src python3 -m cfd_geometry.cli.main --help`.

## Quick start (CLI)

### Full domain pipeline (download + STL)

One command: fetch OSM data under `data/input/`, extrude aligned STLs to `data/output/`:

```bash
pip install -e ".[download]"

cfd-geometry domain -o data --place "Kilbourn Avenue, Milwaukee, Wisconsin, USA"
```

Default download extent for streets/points is about **500 m × 500 m** (`--buffer-m 250`). Widen with `--buffer-m 500` if needed.

Use **`--study-buffer-m`** to set the same padding for both OSM and DEM (e.g. `--study-buffer-m 300`). Otherwise OSM uses `--buffer-m` (default 250) and DEM uses `--dem-buffer-m` (default 200).

Options: `--no-trees`, `--highways`, `--dem`, `--terrain`, `--no-download` (use existing `data/input/`).

Tree heights: OSM `height` tags when present, else sample a user-supplied canopy GeoTIFF (`--canopy-raster data/input/canopy_height.tif`), else 10 m default per tree. No automatic ETH download.

With `--dem`: also writes `buildings_on_dem.stl`, `trees_on_dem.stl`, and (with `--highways`) `highways_on_dem.stl`. DEM extent defaults to **200 m padding** around buildings. Override with `--dem-buffer-m` or `--dem-bbox WEST SOUTH EAST NORTH`.

After a domain build, see `output/domain_summary.json` for offsets, CRS, and file paths.

Use DEM-aligned STLs with `terrain.stl` in ParaView/OpenFOAM; flat `buildings.stl` / `trees.stl` stay at z=0 for simple setups.

### Auto-download inputs only (optional)

Fetch OpenStreetMap buildings, trees, and roads for a place or bounding box:

```bash
pip install -e ".[download]"

# By place name (geocoded; cities use admin boundaries)
cfd-geometry download -o data/input --place "Milwaukee, Wisconsin, USA"

# Streets/points: ~500 m x 500 m box by default (--buffer-m 250)
cfd-geometry download -o data/input --place "Kilbourn Avenue, Milwaukee, Wisconsin, USA"

# By WGS84 bbox: west south east north
cfd-geometry download -o data/input --bbox -88.0 43.0 -87.5 43.5 --layers buildings trees

# Optional SRTM DEM (free OpenTopography API key required)
export OPENTOPOGRAPHY_API_KEY='your-key'
cfd-geometry download -o data/input --place "Oklahoma City, OK" --dem
```

Writes `buildings.shp`, `trees.shp`, `highways.shp`, and optionally `dem.tif` under the output directory.

### Extrude to STL

Compute a shared origin so terrain, buildings, and trees align:

```bash
cfd-geometry offset path/to/buildings.shp path/to/trees.shp
```

Build layers (use the same shapefile list for `--align-with`):

```bash
# OSM-style heights + auto UTM for WGS84 shapefiles (default)
cfd-geometry buildings buildings.shp -o buildings.stl --align-with buildings.shp trees.shp
# --align-with must be vector layers (.shp), not STL outputs

# Footprint-area heights (legacy) and OpenFOAM blockMesh hints
cfd-geometry buildings buildings.shp -o buildings.stl --height-source area --ground-buffer 500

cfd-geometry buildings-dem buildings.shp dem.tif -o buildings.stl --align-with buildings.shp
cfd-geometry trees trees.shp -o trees.stl --align-with buildings.shp trees.shp
cfd-geometry trees-dem trees.shp dem.tif -o trees.stl --align-with buildings.shp
cfd-geometry highways roads.shp -o roads.stl --align-with buildings.shp --clip-to buildings.shp
cfd-geometry terrain dem.tif -o terrain.stl --offset-x 424265.04 --offset-y 4765565.05
# Use the same offset as buildings; terrain Z defaults to "center" so ground ≈ z=0
cfd-geometry clip terrain.stl -o terrain_clipped.stl --bounds -500 -500 300 500 500 720
```

## Python API

```python
import geopandas as gpd
from cfd_geometry import (
    get_combined_offset,
    extrude_buildings_to_stl,
    prepare_buildings_gdf,
    dem_to_stl_with_offset,
    STLClipper,
    OptimizedRectangularBaseGenerator,
)

# From shapefile
ox, oy = get_combined_offset(["buildings.shp", "trees.shp"])
extrude_buildings_to_stl("buildings.shp", "buildings.stl", combined_offset=(ox, oy))

# From GeoDataFrame (QGIS / notebook / VoxCity-style columns: height, min_height, id)
gdf = gpd.read_file("buildings.shp")  # or your own GeoDataFrame
gdf["height"] = 12.0  # per-building heights in meters
extrude_buildings_to_stl(
    gdf,
    "buildings.stl",
    height_source="column",
    height_col="height",
    combined_offset=(ox, oy),
)

dem_to_stl_with_offset("dem.tif", "terrain.stl", ox, oy)
```

## Pluggable sources (strategies)

Height, ground, and tree geometry use small strategy objects instead of scattered flags:

| Strategy | Names | Role |
|----------|-------|------|
| **Height** | `osm`, `area`, `column`, `composite`, `raster`, `default` | Building extrusion heights |
| **Ground** | `flat`, `dem` | Base Z (flat or DEM sampler) |
| **Tree** | `canopy`, `cylinder`, `sphere`, `skip` | Tree mesh shape |

Recommended for CFD studies: **`--height-source composite`** — uses column heights when present, then OSM rules, area tiers, and optional **`--complement-raster`** for gaps. Use **`--resolve-overlaps fast`** to drop duplicate footprints.

```python
from cfd_geometry.sources import height_source_from_name, HeightAssignOptions

strategy = height_source_from_name(
    "composite",
    options=HeightAssignOptions(complement_raster="building_heights.tif"),
)
gdf, col = strategy.apply(buildings_gdf)
```

## Package layout

```
src/cfd_geometry/
├── geo/          # CRS repair, combined offsets
├── mesh/         # STL I/O, polygon extrusion
├── raster/       # DEM loading and elevation sampling
├── buildings/    # OSM heights, geometry repair, overlaps, trimesh extrusion
├── sources/      # HeightSource, GroundSource, TreeModel strategies
├── domain/       # build_domain() orchestrator (download + extrude)
├── download/     # OSM / optional DEM auto-download
├── openfoam/     # blockMeshDict vertex snippets
├── trees/        # Point trees (+ DEM-aware extrude_dem)
├── highways/     # Road linework extrusion
├── terrain/      # DEM → terrain STL
├── clipper/      # Bounding-box STL clip
├── base/         # Terrain-fitted solid base
└── cli/          # ``cfd-geometry`` commands
```

## Legacy scripts

Older standalone `.py` files at the repo root and under `legacy/` still exist for reference. Prefer the package and CLI for new work. See [legacy/README.md](legacy/README.md).

## Requirements

- Python 3.9+
- geopandas, shapely, trimesh, mapbox-earcut, rasterio, numpy, scipy, pandas, pyproj
