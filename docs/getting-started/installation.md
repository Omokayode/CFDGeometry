# Installation

## Requirements

- Python **3.9+**
- Linux / macOS / Windows (WSL is often recommended on Windows for geospatial stacks)

Core dependencies: geopandas, shapely, trimesh, rasterio, numpy, scipy, pandas, pyproj.

## Editable install (recommended)

```bash
cd CFDGeometry
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install -U pip setuptools wheel
python -m pip install -e ".[dev]"
```

Use **`python -m pip`**, not bare `pip`, so you install into the active Python environment.

## Optional extras

| Extra | Command | Purpose |
|-------|---------|---------|
| `download` | `pip install -e ".[download]"` | OSM auto-download via OSMnx |
| `notebook` | `pip install -e ".[notebook]"` | Map extent picker, Plotly STL preview |
| `gdal` | `pip install -e ".[gdal]"` | Alternate DEM readers when rasterio fails |
| `dev` | included above | pytest |

Typical local workflow:

```bash
pip install -e ".[download,notebook,dev]"
```

## Verify the CLI

```bash
cfd-geometry --help
which cfd-geometry
python -c "import cfd_geometry; print(cfd_geometry.__file__)"
```

The import path should point at `.../CFDGeometry/src/cfd_geometry/`.

If flags like `--openfoam` are missing after `git pull`, reinstall:

```bash
pip install -e ".[download]"
```

## Without installing

```bash
PYTHONPATH=src python3 -m cfd_geometry.cli.main --help
```

## Colab

No local install required. Open [colab_quickstart.ipynb](https://colab.research.google.com/github/Omokayode/CFDGeometry/blob/main/notebooks/colab_quickstart.ipynb). The notebook installs from GitHub with `--no-deps` first to avoid breaking Colab’s numpy.

See [Notebooks](../guide/notebooks.md).
