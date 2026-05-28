# API keys & data sources

## OpenStreetMap (buildings, trees, highways)

- Fetched via **OSMnx** when you use `download` or `domain` (without `--no-download`).
- **No API key** required for public OSM data.
- Respect [OSM usage policy](https://operations.osmfoundation.org/policies/); keep reasonable `--buffer-m` / `--timeout`.

```bash
cfd-geometry download -o data/input --place "Milwaukee, Wisconsin, USA"
cfd-geometry download -o data/input --bbox -88.0 43.0 -87.5 43.5 --layers buildings trees
```

## SRTM DEM (OpenTopography)

Required for `--dem` on `domain` / `download`.

1. Register at [OpenTopography](https://portal.opentopography.org/)
2. Create an API key
3. Export:

```bash
export OPENTOPOGRAPHY_API_KEY='your-key-here'
```

Or pass `api_key=` in Python (`cfd_geometry.download.dem`).

The key is **never** stored in the repository—each user supplies their own.

## Canopy / building height rasters

Optional user-supplied GeoTIFFs:

- `--canopy-raster` — tree canopy heights at OSM tree points
- `--complement-raster` — fill missing building heights (`composite` / `raster`)

Place files under `data/input/` or pass absolute paths. No automatic ETH/VoxCity download is built in.

## Local shapefiles

Use `--no-download` and populate `input/` yourself:

```
data/input/buildings.shp
data/input/trees.shp
data/input/dem.tif          # optional
```

Then:

```bash
cfd-geometry domain -o data --place "..." --no-download --dem --terrain
```

`--place` or `--bbox` still defines the study metadata; existing files on disk are used for extrusion.
