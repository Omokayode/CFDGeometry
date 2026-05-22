# Notebooks

## Quick start (recommended)

| | |
|---|---|
| **Google Colab** | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Omokayode/CFDGeometry/blob/main/notebooks/cfd_geometry_quickstart.ipynb) |
| **VS Code / Cursor** | Clone the repo, open `notebooks/cfd_geometry_quickstart.ipynb`, choose the `.venv` kernel, run all cells |
| **GitHub in browser** | [Open notebook on GitHub](https://github.com/Omokayode/CFDGeometry/blob/main/notebooks/cfd_geometry_quickstart.ipynb) |

### VS Code setup

```bash
cd CFDGeometry
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip setuptools wheel
python -m pip install -e ".[notebook,download,dev]"
```

If `pip install -e` fails with “requires a setup.py”, upgrade pip or use `python -m pip` as above (a minimal `setup.py` shim is also in the repo root).

Then **File → Open Folder** on the repo root, open `notebooks/cfd_geometry_quickstart.ipynb`, and select the `.venv` Python interpreter when prompted.

## Other notebooks

| Notebook | Purpose |
|----------|---------|
| `cfd_geometry_quickstart.ipynb` | Install, draw extent, download OSM, extrude STLs, **Plotly 3D preview** |
| `select_extent.ipynb` | Minimal extent picker + download only |

Colab opens notebooks from `main` on GitHub; pin a release tag in the Colab URL if you need a fixed version (`.../blob/v0.1.0/...`).
