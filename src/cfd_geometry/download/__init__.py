"""Download GIS inputs (OSM, optional DEM) for CFD geometry workflows."""

from cfd_geometry.download.config import DownloadConfig, DownloadResult

__all__ = ["DownloadConfig", "DownloadResult", "download_domain"]


def __getattr__(name: str):
    if name == "download_domain":
        from cfd_geometry.download.run import download_domain

        return download_domain
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
