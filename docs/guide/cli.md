# CLI overview

Entry point:

```bash
cfd-geometry --help
```

Global options:

| Flag | Default | Meaning |
|------|---------|---------|
| `--auto-utm` / `--no-auto-utm` | on | Pick UTM zone for geographic (EPSG:4326) inputs |
| `--epsg` | 32616 | Fixed CRS when `--no-auto-utm` |

## Subcommands

| Command | Purpose |
|---------|---------|
| `offset` | Combined translation origin from shapefiles |
| `buildings` | Building footprints → STL |
| `buildings-dem` | Buildings with bases on DEM |
| `trees` | Tree points → STL |
| `trees-dem` | Trees on DEM surface |
| `highways` | Road linework → STL |
| `terrain` | GeoTIFF DEM → terrain STL |
| `clip` | Clip STL to axis-aligned box |
| `download` | OSM (+ optional DEM) only |
| `domain` | Download + extrude full study (recommended) |

## Shared concepts

### `--align-with`

Vector shapefiles used to compute one **combined offset** so buildings, trees, and terrain share the same local origin. Pass `.shp` files, not STL paths.

```bash
cfd-geometry buildings buildings.shp -o out/buildings.stl \
  --align-with buildings.shp trees.shp
```

### Height source

`--height-source` choices: `osm`, `area`, `column`, `composite`, `raster`, `default`, `none`.

Domain default is **`composite`** (column → OSM → area → optional raster fill).

### Auto-UTM

WGS84 shapefiles are reprojected to a suitable UTM zone automatically unless you pass `--no-auto-utm --epsg <code>`.

## Examples

```bash
# Offset only
cfd-geometry offset data/input/buildings.shp data/input/trees.shp

# Single building STL
cfd-geometry buildings data/input/buildings.shp -o data/output/buildings.stl \
  --align-with data/input/buildings.shp

# Terrain (needs offset from domain summary or offset command)
cfd-geometry terrain data/input/dem.tif -o data/output/terrain.stl \
  --offset-x 424265.04 --offset-y 4765565.05

# Clip
cfd-geometry clip data/output/terrain.stl -o data/output/terrain_clipped.stl \
  --bounds -500 -500 300 500 500 720
```

## OpenFOAM flags

Only on **`domain`** and **`buildings`**:

```bash
cfd-geometry domain --help | grep -i openfoam
cfd-geometry buildings --help | grep -i openfoam
```

See [OpenFOAM export](openfoam.md).

## Related

- [Domain pipeline](domain.md)
- [Download & API keys](data-sources.md)
