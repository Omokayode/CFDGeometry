"""Download GIS inputs (OSM, optional DEM) for CFD geometry workflows."""

from cfd_geometry.download.config import DownloadConfig, DownloadResult
from cfd_geometry.download.run import download_domain

__all__ = ["DownloadConfig", "DownloadResult", "download_domain"]
