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
pip install -e ".[notebook,download,dev]"
```

Then **File → Open Folder** on the repo root, open `notebooks/cfd_geometry_quickstart.ipynb`, and select the `.venv` Python interpreter when prompted.

## Other notebooks

| Notebook | Purpose |
|----------|---------|
| `cfd_geometry_quickstart.ipynb` | Install, draw extent, download OSM, extrude sample STLs |
| `select_extent.ipynb` | Minimal extent picker + download only |

Colab opens notebooks from `main` on GitHub; pin a release tag in the Colab URL if you need a fixed version (`.../blob/v0.1.0/...`).
