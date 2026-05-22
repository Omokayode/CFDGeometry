"""Jupyter helpers for CFD geometry workflows."""

from cfd_geometry.notebook.colab import setup_colab_widgets
from cfd_geometry.notebook.extent import ExtentSelector, bbox_from_draw_geojson, select_extent
from cfd_geometry.notebook.install import in_colab, install_for_notebook

__all__ = [
    "ExtentSelector",
    "bbox_from_draw_geojson",
    "in_colab",
    "install_for_notebook",
    "plot_domain_stls",
    "plot_stl_files",
    "select_extent",
    "setup_colab_widgets",
    "stl_to_mesh3d_trace",
]

_LAZY = {
    "plot_domain_stls": ("cfd_geometry.notebook.visualize", "plot_domain_stls"),
    "plot_stl_files": ("cfd_geometry.notebook.visualize", "plot_stl_files"),
    "stl_to_mesh3d_trace": ("cfd_geometry.notebook.visualize", "stl_to_mesh3d_trace"),
}


def __getattr__(name: str):
    if name in _LAZY:
        module_path, attr = _LAZY[name]
        import importlib

        return getattr(importlib.import_module(module_path), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
