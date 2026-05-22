"""3D STL preview for Jupyter / Colab (Plotly)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

_DEFAULT_COLORS: dict[str, str] = {
    "buildings": "#94a3b8",
    "buildings_on_dem": "#64748b",
    "trees": "#166534",
    "trees_on_dem": "#15803d",
    "terrain": "#a16207",
    "highways": "#1e40af",
    "highways_on_dem": "#1d4ed8",
}


def _require_plotly():
    try:
        import plotly.graph_objects as go
    except ImportError as exc:
        raise ImportError(
            "3D preview requires plotly:\n"
            "  pip install plotly\n"
            "  or: pip install -e '.[notebook]'"
        ) from exc
    return go


def _load_trimesh(path: Path):
    import trimesh

    loaded = trimesh.load(path, force="mesh")
    if isinstance(loaded, trimesh.Scene):
        parts = [
            g for g in loaded.geometry.values() if isinstance(g, trimesh.Trimesh)
        ]
        if not parts:
            raise ValueError(f"No triangle meshes in {path}")
        loaded = trimesh.util.concatenate(parts)
    if not isinstance(loaded, trimesh.Trimesh) or loaded.faces.size == 0:
        raise ValueError(f"Empty or invalid mesh: {path}")
    return loaded


def _subsample_faces(faces: np.ndarray, max_triangles: int) -> np.ndarray:
    if len(faces) <= max_triangles:
        return faces
    rng = np.random.default_rng(0)
    idx = rng.choice(len(faces), size=max_triangles, replace=False)
    return faces[idx]


def stl_to_mesh3d_trace(
    path: str | Path,
    *,
    name: str | None = None,
    color: str | None = None,
    opacity: float = 0.85,
    max_triangles: int = 12_000,
) -> Any:
    """
    Build one Plotly ``Mesh3d`` trace from a binary STL.

    Large meshes are randomly downsampled to ``max_triangles`` for responsiveness.
    """
    go = _require_plotly()
    path = Path(path)
    mesh = _load_trimesh(path)
    faces = _subsample_faces(np.asarray(mesh.faces), max_triangles)
    verts = np.asarray(mesh.vertices)
    label = name or path.stem
    return go.Mesh3d(
        x=verts[:, 0],
        y=verts[:, 1],
        z=verts[:, 2],
        i=faces[:, 0],
        j=faces[:, 1],
        k=faces[:, 2],
        name=label,
        color=color or "#64748b",
        opacity=opacity,
        flatshading=True,
        lighting=dict(ambient=0.55, diffuse=0.85, roughness=0.9),
    )


def plot_stl_files(
    stl_files: dict[str, str | Path],
    *,
    max_triangles: int = 12_000,
    title: str = "CFD geometry preview",
    show: bool = True,
    width: int = 900,
    height: int = 650,
) -> Any:
    """
    Interactive 3D view of one or more STL layers.

    Parameters
    ----------
    stl_files
        Map of layer name → path (e.g. ``{"buildings": "data/output/buildings.stl"}``).
    max_triangles
        Per-layer triangle cap for notebook performance.
    show
        If True, embed Plotly HTML in the notebook (no ``nbformat`` required).
    """
    go = _require_plotly()
    traces = []
    for layer, path in stl_files.items():
        p = Path(path)
        if not p.is_file():
            continue
        color = _DEFAULT_COLORS.get(layer, "#64748b")
        try:
            traces.append(
                stl_to_mesh3d_trace(
                    p,
                    name=layer,
                    color=color,
                    max_triangles=max_triangles,
                )
            )
        except ValueError as exc:
            print(f"Skip {layer}: {exc}")

    if not traces:
        raise FileNotFoundError("No STL files found to plot")

    fig = go.Figure(data=traces)
    fig.update_layout(
        title=title,
        width=width,
        height=height,
        scene=dict(
            xaxis_title="x (m)",
            yaxis_title="y (m)",
            zaxis_title="z (m)",
            aspectmode="data",
        ),
        margin=dict(l=0, r=0, t=40, b=0),
    )
    if show:
        _show_figure(fig)
    return fig


def _show_figure(fig: Any) -> None:
    """Embed Plotly in the notebook via HTML (avoids nbformat / fig.show() mime path)."""
    out = Path("data/output/stl_preview.html")
    out.parent.mkdir(parents=True, exist_ok=True)

    try:
        from IPython.display import HTML, display

        for inline_js in (True, "cdn"):
            try:
                display(HTML(fig.to_html(include_plotlyjs=inline_js)))
                return
            except Exception:
                continue
    except ImportError:
        pass

    fig.write_html(str(out), include_plotlyjs="cdn")
    try:
        from IPython.display import HTML, display

        display(HTML(out.read_text(encoding="utf-8")))
        return
    except ImportError:
        pass

    raise RuntimeError(
        f"Plotly preview written to {out.resolve()} — open in a browser. "
        "For inline display: pip install -e '.[notebook]' and restart the kernel."
    )


def plot_domain_stls(
    result: Any,
    *,
    layers: tuple[str, ...] | None = None,
    max_triangles: int = 12_000,
    show: bool = True,
) -> Any:
    """Plot STLs from a :class:`~cfd_geometry.domain.DomainResult`."""
    available = {k: v for k, v in result.stl_files.items() if Path(v).is_file()}
    if layers is not None:
        available = {k: v for k, v in available.items() if k in layers}
    return plot_stl_files(
        available,
        max_triangles=max_triangles,
        title="Domain STLs",
        show=show,
    )
