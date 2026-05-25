# CFD Geometry

[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://omokayode.github.io/CFDGeometry/)
[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Omokayode/CFDGeometry/blob/main/notebooks/colab_quickstart.ipynb)

Python tools to turn **GIS and DEM data into aligned STL meshes** for urban wind CFD and OpenFOAM.

**Full documentation:** [omokayode.github.io/CFDGeometry](https://omokayode.github.io/CFDGeometry/)

## Install

```bash
git clone https://github.com/Omokayode/CFDGeometry.git && cd CFDGeometry
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -U pip setuptools wheel
python -m pip install -e ".[download]"
```

Use `python -m pip` (not bare `pip`) on macOS. Extras: `[notebook]`, `[gdal]`, `[dev]`, `[docs]` — see [Installation](https://omokayode.github.io/CFDGeometry/getting-started/installation/).

## Quick start

```bash
cfd-geometry domain -o data --place "Kilbourn Avenue, Milwaukee, Wisconsin, USA"
```

With DEM, terrain, and OpenFOAM snippets:

```bash
export OPENTOPOGRAPHY_API_KEY='your-key'   # for --dem
cfd-geometry domain -o data --place "Kilbourn Avenue, Milwaukee, Wisconsin, USA" \
  --dem --terrain --openfoam
```

Outputs under `data/input/` and `data/output/` (including `domain_summary.json`).  
`--openfoam` is on the `domain` and `buildings` subcommands — run `cfd-geometry domain --help`.

## Documentation

| Topic | Link |
|-------|------|
| Quick start & examples | [Guide](https://omokayode.github.io/CFDGeometry/getting-started/quickstart/) |
| CLI reference | [CLI overview](https://omokayode.github.io/CFDGeometry/guide/cli/) |
| Domain pipeline | [Domain](https://omokayode.github.io/CFDGeometry/guide/domain/) |
| OpenFOAM export | [OpenFOAM](https://omokayode.github.io/CFDGeometry/guide/openfoam/) |
| Colab & VS Code | [Notebooks](https://omokayode.github.io/CFDGeometry/guide/notebooks/) |
| API keys (OSM, DEM) | [Data sources](https://omokayode.github.io/CFDGeometry/guide/data-sources/) |
| Python API | [Reference](https://omokayode.github.io/CFDGeometry/reference/python-api/) |

**Notebooks:** [Colab](https://colab.research.google.com/github/Omokayode/CFDGeometry/blob/main/notebooks/colab_quickstart.ipynb) · local `notebooks/cfd_geometry_quickstart.ipynb` ([notebooks/README.md](notebooks/README.md))

## Requirements

Python 3.9+ · geopandas, shapely, trimesh, rasterio, and related stack (see `pyproject.toml`).

Legacy standalone scripts live under `legacy/`; use the package and CLI for new work.
