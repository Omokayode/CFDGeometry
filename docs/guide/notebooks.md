# Notebooks

Two entry notebooks—do not mix Colab and VS Code install steps in one file.

| Environment | Notebook |
|-------------|----------|
| **Google Colab** | [colab_quickstart.ipynb](https://colab.research.google.com/github/Omokayode/CFDGeometry/blob/main/notebooks/colab_quickstart.ipynb) |
| **VS Code / Jupyter** | `notebooks/cfd_geometry_quickstart.ipynb` |

See also [notebooks/README.md](https://github.com/Omokayode/CFDGeometry/blob/main/notebooks/README.md) in the repo.

## Local setup

```bash
pip install -e ".[notebook,download,dev]"
```

Open the repo **root** as the workspace (not only `notebooks/`) so imports resolve.

Select the `.venv` Python kernel in VS Code.

## Colab install note

Colab runs:

```text
pip install --no-deps git+https://github.com/Omokayode/CFDGeometry.git
```

then installs dependencies separately. This avoids upgrading numpy and breaking Colab.

## Pick a study extent

```python
from cfd_geometry.notebook import select_extent, setup_colab_widgets

setup_colab_widgets()  # no-op outside Colab
sel = select_extent(place="Milwaukee, Wisconsin, USA")
# Draw rectangle → "Use this extent" → sel.bbox  (WGS84, same as CLI --bbox)
```

## Preview STLs

Plotly 3D preview (HTML in VS Code; no `nbformat` required for `fig.show()`):

```python
from cfd_geometry.notebook import plot_domain_stls, plot_stl_files

plot_domain_stls(result, layers=("buildings", "trees"), max_triangles=8000)
# plot_stl_files({"buildings": "data/output/buildings.stl"})
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Import/module errors | Open the repo **root**, reinstall editable (`pip install -e .`), and select the correct kernel |
| Plot/preview not updating | Reinstall editable package and restart/reload the notebook kernel |
| Environment mismatch (local vs Colab) | Use the notebook’s provided install cell (e.g. `--no-deps` on Colab) and restart the runtime |
