"""Download GIS inputs (OSM, optional DEM/DSM) for CFD geometry workflows."""

from cfd_geometry.download.config import DownloadConfig, DownloadResult

__all__ = [
    "DownloadConfig",
    "DownloadResult",
    "download_domain",
    "download_dsm_opentopography",
    "download_dtm_opentopography",
    "download_lidar_rasters_opentopography",
]


def __getattr__(name: str):
    if name == "download_domain":
        from cfd_geometry.download.run import download_domain

        return download_domain
    if name == "download_dsm_opentopography":
        from cfd_geometry.download.dsm import download_dsm_opentopography

        return download_dsm_opentopography
    if name == "download_dtm_opentopography":
        from cfd_geometry.download.dsm import download_dtm_opentopography

        return download_dtm_opentopography
    if name == "download_lidar_rasters_opentopography":
        from cfd_geometry.download.dsm import download_lidar_rasters_opentopography

        return download_lidar_rasters_opentopography
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
