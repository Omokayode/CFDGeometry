# Quick start

## 1. Full domain (download + STL)

```bash
pip install -e ".[download]"

cfd-geometry domain -o data \
  --place "Kilbourn Avenue, Milwaukee, Wisconsin, USA"
```

Creates:

```
data/
├── input/    # buildings.shp, trees.shp, …
└── output/   # buildings.stl, trees.stl, domain_summary.json
```

Default OSM extent for streets is about **500 m × 500 m** (`--buffer-m 250`).

## 2. Add DEM and terrain

```bash
export OPENTOPOGRAPHY_API_KEY='your-key'   # free at opentopography.org

cfd-geometry domain -o data \
  --place "Kilbourn Avenue, Milwaukee, Wisconsin, USA" \
  --dem --terrain
```

Also writes `dem.tif`, `buildings_on_dem.stl`, `trees_on_dem.stl`, and `terrain.stl`.

## 3. OpenFOAM snippets

```bash
cfd-geometry domain -o data \
  --place "Kilbourn Avenue, Milwaukee, Wisconsin, USA" \
  --dem --terrain --openfoam
```

Under `data/output/`:

- `blockMeshDict` — background hex box
- `snappyHexMeshDict` — surface refinement template
- `snappyHexMeshConfig.command` — example CLI one-liner

Details: [OpenFOAM export](../guide/openfoam.md).

## 4. Use existing inputs (no download)

```bash
cfd-geometry domain -o data --place "..." --no-download
```

Expects shapefiles (and optional `dem.tif`) in `data/input/`.

## 5. WGS84 bounding box

```bash
cfd-geometry domain -o data --bbox -88.0 43.0 -87.5 43.5 --dem
```

Order: **west south east north** (same as CLI `download`).

## Next steps

- [Domain pipeline](../guide/domain.md) — all flags and output files
- [CLI overview](../guide/cli.md) — buildings, trees, clip, offset
- [Notebooks](../guide/notebooks.md) — interactive extent and preview
