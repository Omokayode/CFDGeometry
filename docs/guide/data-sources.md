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

## DSM / DTM for LiDAR building heights (OpenTopography)

Use the same `OPENTOPOGRAPHY_API_KEY` as SRTM. Downloads **Copernicus COP30** DSM by default (30 m, global). Optional **DTM** (`--dtm`, default SRTMGL1) supports CHM-style heights (DSM − DTM).

```bash
export OPENTOPOGRAPHY_API_KEY='your-key'
cfd-geometry download -o data/input --place "Milwaukee, Wisconsin, USA" --dsm --dtm
cfd-geometry domain -o data --place "Milwaukee, Wisconsin, USA" --dsm --dem --terrain
```

| Flag | Output | Notes |
|------|--------|--------|
| `--dsm` | `dsm.tif` | Surface model (buildings + vegetation) |
| `--dtm` | `dtm.tif` | Ground model for CHM; auto-enabled with `--dsm` on `domain` |
| `--dsm-product` | — | `COP30` (default), `COP90`, `CA_MRDEM_DSM`, `USGS10m` (CONUS) |
| `--dtm-product` | — | `SRTMGL1` (default), `USGS10m`, `EU_DTM`, … |
| `--stepped-facades` | — | DEM-following base on `buildings_lidar.stl` |

Python: `cfd_geometry.download.download_dsm_opentopography`, `download_lidar_rasters_opentopography`.

Area limits apply (e.g. COP30 ≤ ~450k km²; USGS10m ≤ ~25k km²). Use a tight bbox or `--dem-bbox`.

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
data/input/dem.tif          # optional (terrain / ground)
data/input/dsm.tif          # optional (LiDAR-style heights)
data/input/dtm.tif          # optional (CHM ground)
```

Then:

```bash
cfd-geometry domain -o data --place "..." --no-download --dem --terrain
```

`--place` or `--bbox` still defines the study metadata; existing files on disk are used for extrusion.
