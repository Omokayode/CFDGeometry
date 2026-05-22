# Notebooks

## Colab quick start (use this link)

| | |
|---|---|
| **Google Colab** | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Omokayode/CFDGeometry/blob/main/notebooks/colab_quickstart.ipynb) |
| **VS Code / Cursor** | Clone the repo, open `notebooks/colab_quickstart.ipynb`, `.venv` kernel |

### Colab: wrong notebook?

If the **second cell is a map** (not `STEP 1 — Install`), you are **not** on the current notebook:

1. Do **not** open a copy from **Google Drive**.
2. Use the Colab link above (file: `colab_quickstart.ipynb`).
3. Check the title cell shows **NOTEBOOK_ID: `cfd-colab-v3-20250522`**.

### VS Code setup

```bash
cd CFDGeometry
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip setuptools wheel
python -m pip install -e ".[notebook,download,dev]"
```

## Other notebooks

| Notebook | Purpose |
|----------|---------|
| `colab_quickstart.ipynb` | **Main demo** — install, map, STLs, Plotly |
| `cfd_geometry_quickstart.ipynb` | Same content as `colab_quickstart` (alias) |
| `select_extent.ipynb` | Extent picker + install only; points to Colab quick start |
