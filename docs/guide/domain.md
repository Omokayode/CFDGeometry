# Domain pipeline

`cfd-geometry domain` downloads inputs (optional) and extrudes aligned STLs into one project folder.

## Layout

```bash
cfd-geometry domain -o data --place "Milwaukee, Wisconsin, USA"
```

```
data/
├── input/
│   ├── buildings.shp
│   ├── trees.shp
│   └── highways.shp   # with --highways
└── output/
    ├── buildings.stl
    ├── trees.stl
    ├── domain_summary.json
    └── …
```

`-o` / `--output-dir` is the **project root** (not `output/` itself).

## Location (required)

One of:

- `--place "Street or city name"` — geocoded; streets use a buffered box
- `--bbox WEST SOUTH EAST NORTH` — WGS84 degrees

## Download control

| Flag | Effect |
|------|--------|
| `--no-download` | Use existing `input/` files |
| `--no-trees` | Skip trees |
| `--highways` | Include roads |
| `--dem` | Download SRTM via OpenTopography (API key) |
| `--terrain` | Build `terrain.stl` (needs DEM) |

## Extent buffers

| Flag | Default | Role |
|------|---------|------|
| `--buffer-m` | 250 | OSM box half-width for street geocodes (~500 m span) |
| `--dem-buffer-m` | 200 | DEM padding around buildings |
| `--study-buffer-m` | — | Sets **both** OSM and DEM padding |
| `--dem-bbox` | — | Explicit WGS84 DEM bounds (overrides dem buffer) |

## Building heights & quality

| Flag | Default | Role |
|------|---------|------|
| `--height-source` | `composite` | Height assignment strategy |
| `--default-height` | 9 m | Fallback footprint height |
| `--resolve-overlaps` | off | `fast` or `precise` dedup |
| `--complement-raster` | — | GeoTIFF to fill height gaps |
| `--simplify-tolerance` | — | Douglas–Peucker simplify (m) |
| `--workers` | 1 | Parallel extrusion workers |

## Trees

| Flag | Default | Role |
|------|---------|------|
| `--tree-model` | `canopy` | `canopy`, `cylinder`, `sphere`, `skip` |
| `--canopy-raster` | — | User canopy height GeoTIFF at tree points |

Heights: OSM `height` tag → canopy raster sample → 10 m default.

## OpenFOAM / domain box

| Flag | Default | Role |
|------|---------|------|
| `--ground-buffer` | 500 m | Outer blockMesh padding |
| `--no-ground-buffer` | — | Disable extrude-time blockMesh |
| `--openfoam` | off | Write blockMesh + snappy at end |
| `--refinement-buffer-m` | 10 m | snappy searchableBox pad |
| `--openfoam-cell-size` | 5 m | blockMesh cell size |

With `--openfoam`, blockMesh is written **once** at pipeline end (not during building extrusion).

## DEM-aligned outputs

When `--dem` is set:

- `buildings_on_dem.stl`
- `trees_on_dem.stl`
- `highways_on_dem.stl` (with `--highways`)

Use these with `terrain.stl` in ParaView/OpenFOAM. Flat `buildings.stl` / `trees.stl` remain at z ≈ 0 for simple setups.

## Summary file

`output/domain_summary.json` records CRS, combined offset, STL paths, extrusion stats, and OpenFOAM metadata when used.

## Example: study with OpenFOAM

```bash
export OPENTOPOGRAPHY_API_KEY='your-key'

cfd-geometry domain -o data \
  --place "Kilbourn Avenue, Milwaukee, Wisconsin, USA" \
  --dem --terrain --highways \
  --openfoam \
  --ground-buffer 500 \
  --refinement-buffer-m 15 \
  --openfoam-cell-size 5
```

## Python API

```python
from pathlib import Path
from cfd_geometry.domain.config import DomainConfig
from cfd_geometry.domain.pipeline import build_domain

config = DomainConfig(
    output_dir=Path("data"),
    place="Milwaukee, Wisconsin, USA",
    download_dem=True,
    build_terrain=True,
    export_openfoam=True,
)
result = build_domain(config)
```
