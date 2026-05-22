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


def find_repo_root(start: Path | None = None) -> Path:
    """
    Locate the CFDGeometry repo root (contains ``src/cfd_geometry/domain``).

    Notebooks often run with cwd ``notebooks/``; walk parents so editable
    install still works in VS Code.
    """
    here = (start or Path.cwd()).resolve()
    for p in (here, *here.parents):
        if (p / "src" / "cfd_geometry" / "domain").is_dir():
            return p
    return here


def verify_domain_import() -> None:
    """Raise with setup hints if the full package (including ``domain``) is missing."""
    try:
        from cfd_geometry.domain import DomainConfig, build_domain  # noqa: F401
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "cfd_geometry is installed without the domain package.\n"
            "VS Code / local fix:\n"
            "  1. File → Open Folder → CFDGeometry repo root (not only notebooks/)\n"
            "  2. Select the .venv kernel (Python: .venv/bin/python)\n"
            "  3. Terminal: python -m pip install -U pip setuptools wheel\n"
            "  4. Terminal: python -m pip install -e \".[notebook,download]\"\n"
            "  5. Re-run the STEP 1 install cell\n"
        ) from exc


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
    root = repo_root or find_repo_root()
    src_pkg = root / "src" / "cfd_geometry"

    if in_colab():
        _run_pip(
            *_COLAB_WIDGET_DEPS,
            "--upgrade-strategy",
            "only-if-needed",
        )
        _run_pip(
            "--upgrade",
            "--force-reinstall",
            "--no-cache-dir",
            f"{_GIT_ORIGIN}#egg=cfd-geometry[download]",
        )
        return

    if src_pkg.exists():
        _run_pip("-e", f"{root}[notebook,download]")
        return

    _run_pip(f"{_GIT_ORIGIN}#egg=cfd-geometry[notebook,download]")
