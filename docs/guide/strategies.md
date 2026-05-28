# Height & geometry strategies

Building heights, ground placement, and tree shapes use small **strategy** objects instead of ad hoc flags.

## Height sources (`--height-source`)

| Name | Use when |
|------|----------|
| `osm` | OSM tags (`height`, `building:levels`, …) |
| `area` | Footprint-area tier estimates (legacy) |
| `column` | Shapefile column (e.g. VoxCity `height`) |
| `composite` | **Recommended** — column → OSM → area → optional raster |
| `raster` | Sample heights from a GeoTIFF |
| `default` | Constant `--default-height` |
| `none` | Skip height assignment |

Domain default: **`composite`**.

### Overlaps & simplification

```bash
cfd-geometry domain -o data --place "..." \
  --resolve-overlaps fast \
  --complement-raster data/input/building_heights.tif \
  --simplify-tolerance 0.5
```

- `--resolve-overlaps fast` — drop duplicate footprints
- `--resolve-overlaps precise` — clip overlaps (slower)
- `--complement-raster` — fill gaps when using `composite` or `raster`

## Ground sources

| Mode | CLI / API |
|------|-----------|
| Flat z = 0 | Default `buildings` / `trees` |
| DEM-based bases | `--dem` on domain, or `buildings-dem` / `trees-dem` |

Terrain Z reference: `center` (default) so local ground ≈ 0 after offset.

## Tree models (`--tree-model`)

| Name | Shape |
|------|-------|
| `canopy` | Flat canopy disc (default) |
| `cylinder` | Simple cylinder |
| `sphere` | Sphere |
| `skip` | No tree mesh |

## Python strategies

```python
from cfd_geometry.sources import height_source_from_name, HeightAssignOptions

strategy = height_source_from_name(
    "composite",
    options=HeightAssignOptions(complement_raster="building_heights.tif"),
)
gdf, col = strategy.apply(buildings_gdf)
```

## GeoDataFrame workflow

Pass a prepared GeoDataFrame with `height`, `min_height`, `id` columns:

```python
import geopandas as gpd
from cfd_geometry import extrude_buildings_to_stl, prepare_buildings_gdf

gdf = gpd.read_file("buildings.shp")
gdf, crs, col = prepare_buildings_gdf(gdf, height_source="column", height_col="height")
extrude_buildings_to_stl(gdf, "buildings.stl", combined_offset=(ox, oy))
```
