"""Install helpers for notebook / Colab environments."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_GIT_ORIGIN = "git+https://github.com/Omokayode/CFDGeometry.git@main"

# Colab ships ipython==7.34; do not pull ipython>=8 via optional deps.
_COLAB_WIDGET_DEPS = (
    "ipywidgets>=7.6,<9",
    "ipyleaflet>=0.17",
    "jupyterlab_widgets>=1.0.5,<4",
    "plotly>=5.18",
)


def in_colab() -> bool:
    try:
        import google.colab  # noqa: F401

        return True
    except ImportError:
        return False


def _run_pip(*args: str) -> None:
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-q", *args],
    )


def install_for_notebook(*, repo_root: Path | None = None) -> None:
    """
    Install cfd-geometry and map widgets without breaking Colab's ipython pin.

    Local clone: editable install with ``[notebook,download]``.
    Colab: install ``[download]`` from GitHub, then widget deps with only-if-needed.
    """
    root = repo_root or Path.cwd()
    src_pkg = root / "src" / "cfd_geometry"

    if in_colab():
        _run_pip(
            *_COLAB_WIDGET_DEPS,
            "--upgrade-strategy",
            "only-if-needed",
        )
        _run_pip(f"{_GIT_ORIGIN}#egg=cfd-geometry[download]")
        return

    if src_pkg.exists():
        _run_pip("-e", f"{root}[notebook,download]")
        return

    _run_pip(f"{_GIT_ORIGIN}#egg=cfd-geometry[notebook,download]")
