# CFD Geometry

**GIS and elevation data → aligned STL meshes** for urban wind CFD and OpenFOAM.

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Omokayode/CFDGeometry/blob/main/notebooks/colab_quickstart.ipynb)

## What it does

- Download OpenStreetMap buildings, trees, and roads (optional SRTM DEM)
- Extrude footprints and linework to binary STL with a **shared origin**
- Optional **DEM-aligned** layers (`buildings_on_dem.stl`, `terrain.stl`, …)
- Optional **OpenFOAM** snippets: `blockMeshDict`, `snappyHexMeshDict`

## Install

```bash
git clone https://github.com/Omokayode/CFDGeometry.git
cd CFDGeometry
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -U pip setuptools wheel
python -m pip install -e ".[download]"
```

## One-command domain build

```bash
cfd-geometry domain -o data --place "Kilbourn Avenue, Milwaukee, Wisconsin, USA"
```

Add `--dem --terrain --openfoam` for terrain STLs and OpenFOAM case snippets.

## Documentation map

| Topic | Page |
|-------|------|
| Install & extras | [Installation](getting-started/installation.md) |
| First run | [Quick start](getting-started/quickstart.md) |
| All CLI commands | [CLI overview](guide/cli.md) |
| Full pipeline | [Domain pipeline](guide/domain.md) |
| OpenFOAM flags | [OpenFOAM export](guide/openfoam.md) |
| Colab / VS Code | [Notebooks](guide/notebooks.md) |
| Heights & overlaps | [Strategies](guide/strategies.md) |
| API keys | [Data sources](guide/data-sources.md) |

## OpenFOAM note

`--openfoam` is **not** on top-level `cfd-geometry --help`. Use:

```bash
cfd-geometry domain --help
cfd-geometry buildings --help
```

## Links

- [GitHub repository](https://github.com/Omokayode/CFDGeometry)
- [Colab quick start](https://colab.research.google.com/github/Omokayode/CFDGeometry/blob/main/notebooks/colab_quickstart.ipynb)
