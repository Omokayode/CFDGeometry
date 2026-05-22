# Python API

Install the package first (`pip install -e .`). Optional: `[download]`, `[notebook]`.

## Offsets and buildings

```python
import geopandas as gpd
from cfd_geometry import (
    get_combined_offset,
    extrude_buildings_to_stl,
    prepare_buildings_gdf,
    dem_to_stl_with_offset,
    STLClipper,
)

ox, oy = get_combined_offset(["data/input/buildings.shp", "data/input/trees.shp"])

extrude_buildings_to_stl(
    "data/input/buildings.shp",
    "data/output/buildings.stl",
    combined_offset=(ox, oy),
    height_source="composite",
    ground_buffer=500.0,
)

dem_to_stl_with_offset(
    "data/input/dem.tif",
    "data/output/terrain.stl",
    ox,
    oy,
)
```

## Domain orchestrator

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
    refinement_buffer_m=10.0,
    openfoam_cell_size=5.0,
)
result = build_domain(config)
print(result.stl_files)
```

## OpenFOAM export

```python
from pathlib import Path
from cfd_geometry.openfoam.export import export_openfoam_case

export_openfoam_case(
    Path("data/output"),
    building_bounds=stats["bounds"],
    max_building_height=25.0,
    ground_buffer_m=500.0,
    stl_files={"buildings_on_dem": Path("data/output/buildings_on_dem.stl")},
)
```

## Notebook helpers

```python
from cfd_geometry.notebook import (
    select_extent,
    plot_domain_stls,
    plot_stl_files,
    setup_colab_widgets,
)
```

## STL clipping

```python
from cfd_geometry import STLClipper

clipper = STLClipper("terrain.stl")
clipper.clip_to_bounds(xmin=-500, ymin=-500, zmin=300, xmax=500, ymax=500, zmax=720)
clipper.write("terrain_clipped.stl")
```

See package docstrings under `src/cfd_geometry/` for module-level detail.
