# Notebooks

## Colab quick start (use this link)

| | |
|---|---|
| **Google Colab** | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Omokayode/CFDGeometry/blob/main/notebooks/colab_quickstart.ipynb) |
| **VS Code** | Clone the repo, open `notebooks/colab_quickstart.ipynb`, `.venv` kernel |

### Colab: wrong notebook?

If the **second cell is a map** (not `STEP 1 — Install`), you are **not** on the current notebook:

1. Do **not** open a copy from **Google Drive**.
2. Use the Colab link above (file: `colab_quickstart.ipynb`).
3. Check the title cell shows **NOTEBOOK_ID: `cfd-colab-v5-stable-deps`**.

### VS Code: `No module named 'cfd_geometry.domain'`

1. **Open Folder** → repo root (contains `src/`, not only `notebooks/`).
2. Install from terminal:

```bash
cd /path/to/CFDGeometry
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip setuptools wheel
python -m pip install -e ".[notebook,download,dev]"
```

3. Select kernel **`.venv`** (not system Python).
4. Re-run **STEP 1** — should print `Repo root: .../CFDGeometry` and import `domain` OK.

## Other notebooks

| Notebook | Purpose |
|----------|---------|
| `colab_quickstart.ipynb` | **Main demo** — install, map, STLs, Plotly |
| `cfd_geometry_quickstart.ipynb` | Same content as `colab_quickstart` (alias) |
| `select_extent.ipynb` | Extent picker + install only; points to Colab quick start |
