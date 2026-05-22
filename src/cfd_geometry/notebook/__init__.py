"""Jupyter helpers for CFD geometry workflows."""

from cfd_geometry.notebook.colab import setup_colab_widgets
from cfd_geometry.notebook.extent import ExtentSelector, bbox_from_draw_geojson, select_extent
from cfd_geometry.notebook.install import in_colab, install_for_notebook
from cfd_geometry.notebook.visualize import (
    plot_domain_stls,
    plot_stl_files,
    stl_to_mesh3d_trace,
)

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
