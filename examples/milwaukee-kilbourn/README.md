# Milwaukee — Kilbourn Avenue example

Urban wind geometry study using the CFDGeometry domain pipeline.

## Prerequisites

```bash
cd CFDGeometry
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[download]"
export OPENTOPOGRAPHY_API_KEY='your-key'   # required for --dem
```

## Run

```bash
./examples/milwaukee-kilbourn/run.sh
```

Or manually:

```bash
cfd-geometry domain -o examples/milwaukee-kilbourn/data \
  --place "Kilbourn Avenue, Milwaukee, Wisconsin, USA" \
  --dem --terrain
```

## Outputs

| Path | Description |
|------|-------------|
| `data/input/buildings.shp` | OSM footprints |
| `data/input/dem.tif` | SRTM DEM (200 m padding) |
| `data/output/buildings.stl` | Flat footprints at z=0 |
| `data/output/terrain.stl` | Terrain surface |
| `data/output/buildings_on_dem.stl` | Buildings on terrain |
| `data/output/domain_summary.json` | CRS, offset, file list |
| `data/output/blockMeshDict` | Starter OpenFOAM background mesh |

## Tips

- Use `--study-buffer-m 300` to widen OSM and DEM together.
- Use `--no-download` after the first run to reuse `data/input/`.
- Open `terrain.stl` in MeshLab; the build verifies finite vertices automatically.
