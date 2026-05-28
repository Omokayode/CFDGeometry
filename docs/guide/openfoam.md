# OpenFOAM export

CFD Geometry can emit **starter** OpenFOAM dictionaries—not a full case—so you can copy files into `system/` and tune patches, turbulence, and solver settings.

## Where the flags live

`--openfoam` is a **subcommand** flag, not global:

```bash
cfd-geometry domain --help
cfd-geometry buildings --help
```

## Output files

Written to the STL output directory (e.g. `data/output/`):

| File | Description |
|------|-------------|
| `blockMeshDict` | Rectangular background mesh; patches `inlet`, `outlet`, `ground`, `top`, `sides` |
| `snappyHexMeshDict` | Surface refinement template referencing your STLs |
| `snappyHexMeshConfig.command` | Example `snappyHexMesh` command line |

Legacy sidecar files (`blockMeshDict_vertices.txt`, `blockMeshDict.vertices.txt`) are **removed** when a new `blockMeshDict` is written.

## Domain pipeline

```bash
cfd-geometry domain -o data \
  --place "Kilbourn Avenue, Milwaukee, Wisconsin, USA" \
  --dem --terrain \
  --openfoam \
  --ground-buffer 500 \
  --refinement-buffer-m 10 \
  --openfoam-cell-size 5
```

Behavior:

1. Building extrusion runs **without** writing blockMesh mid-pipeline.
2. At the end, `export_openfoam_case()` writes all three files using bounds from `buildings_on_dem` or `buildings` stats.

## Buildings-only

```bash
cfd-geometry buildings buildings.shp -o data/output/buildings.stl \
  --align-with buildings.shp \
  --openfoam \
  --ground-buffer 500
```

Without `--openfoam`, `--ground-buffer` still writes `blockMeshDict` during extrusion (unless `--no-ground-buffer` on domain).

## Parameters

| Flag | Default | Meaning |
|------|---------|---------|
| `--ground-buffer` | 500 (domain) | Outer box padding around building XY bounds (m) |
| `--refinement-buffer-m` | 10 | `searchableBox` padding around buildings in snappy |
| `--openfoam-cell-size` | 5 | Target blockMesh cell size (m) |

Domain height in Z uses roughly `max(6 × max_building_height, 100 m)` unless you adjust the case manually after export.

## Using in OpenFOAM

1. Copy `blockMeshDict` → `system/blockMeshDict`
2. Run `blockMesh`
3. Copy STLs to `constant/triSurface/` (names must match snappy `geo` entries)
4. Copy and edit `snappyHexMeshDict` → `system/snappyHexMeshDict`
5. Verify `locationInMesh` and patch names match your flow setup
6. Run `snappyHexMesh` (see `snappyHexMeshConfig.command` for a starting point)

!!! warning "Templates only"
    Inlet/outlet orientation, `locationInMesh`, and refinement levels are starting points. Always review before production runs.

## Python

```python
from pathlib import Path
from cfd_geometry.openfoam.export import export_openfoam_case

export_openfoam_case(
    Path("data/output"),
    building_bounds={"x_min": 0, "x_max": 100, "y_min": 0, "y_max": 80, "z_min": 0, "z_max": 25},
    max_building_height=25.0,
    ground_buffer_m=500.0,
    stl_files={
        "buildings_on_dem": Path("data/output/buildings_on_dem.stl"),
        "terrain": Path("data/output/terrain.stl"),
    },
    refinement_buffer_m=10.0,
    cell_size=5.0,
)
```
