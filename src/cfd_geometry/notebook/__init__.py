"""Jupyter helpers for CFD geometry workflows."""

from cfd_geometry.notebook.colab import setup_colab_widgets
from cfd_geometry.notebook.extent import ExtentSelector, bbox_from_draw_geojson, select_extent

__all__ = [
    "ExtentSelector",
    "bbox_from_draw_geojson",
    "select_extent",
    "setup_colab_widgets",
]
