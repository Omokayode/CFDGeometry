# Package layout

```
src/cfd_geometry/
├── geo/          # CRS repair, combined offsets
├── mesh/         # STL I/O, polygon extrusion (trimesh)
├── raster/       # DEM loading and elevation sampling
├── buildings/    # Heights, repair, overlaps, extrusion
├── sources/      # HeightSource, GroundSource, TreeModel strategies
├── domain/       # build_domain() orchestrator
├── download/     # OSM / optional DEM download
├── openfoam/     # blockMeshDict, snappyHexMeshDict export
├── trees/        # Point trees (+ DEM extrusion)
├── highways/     # Road linework
├── terrain/      # DEM → terrain STL
├── clipper/      # Bounding-box STL clip
├── base/         # Terrain-fitted solid base
├── notebook/     # Extent picker, Plotly preview
└── cli/          # cfd-geometry entry point
```

## Tests

```
tests/
```

Run: `pytest` from repo root with `pip install -e ".[dev]"`.

## Legacy code

Older standalone scripts live under `legacy/`. Prefer the package and CLI for new work. See [legacy/README.md](https://github.com/Omokayode/CFDGeometry/blob/main/legacy/README.md).
