"""Configuration for auto-downloading study-area inputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from cfd_geometry.constants import DEFAULT_DEM_BUFFER_M, DEFAULT_PLACE_BUFFER_M
from cfd_geometry.download.bbox import Bbox

DEFAULT_LAYERS = ("buildings", "trees", "highways")


@dataclass
class DownloadConfig:
    """
    Where to fetch data and what to write to disk.

    Provide either ``place`` (geocoded name) or ``bbox`` (WGS84 degrees).
    """

    output_dir: Path
    place: str | None = None
    bbox: Bbox | None = None
    layers: tuple[str, ...] = DEFAULT_LAYERS
    download_dem: bool = False
    download_dsm: bool = False
    download_dtm: bool = False
    dem_filename: str = "dem.tif"
    dsm_filename: str = "dsm.tif"
    dtm_filename: str = "dtm.tif"
    opentopography_dsm_product: str = "COP30"
    opentopography_dtm_product: str = "SRTMGL1"
    clip_rasters_to_dem: bool = True
    use_usgs10m: bool = False
    auto_usgs10m: bool = False
    buildings_filename: str = "buildings.shp"
    trees_filename: str = "trees.shp"
    highways_filename: str = "highways.shp"
    opentopography_demtype: str = "SRTMGL1"
    network_timeout: int = 180
    place_buffer_m: float = DEFAULT_PLACE_BUFFER_M
    study_buffer_m: float | None = None
    dem_buffer_m: float = DEFAULT_DEM_BUFFER_M
    dem_bbox: Bbox | None = None

    def __post_init__(self) -> None:
        self.output_dir = Path(self.output_dir)
        if not self.place and not self.bbox:
            raise ValueError("Provide either place= or bbox=")
        if self.place and self.bbox:
            raise ValueError("Provide only one of place= or bbox=")
        if self.study_buffer_m is not None:
            self.place_buffer_m = self.study_buffer_m
            self.dem_buffer_m = self.study_buffer_m
        unknown = set(self.layers) - {"buildings", "trees", "highways", "dem", "dsm", "dtm"}
        if unknown:
            raise ValueError(f"Unknown layers: {unknown}")


@dataclass
class DownloadResult:
    """Paths and counts from a download run."""

    output_dir: Path
    bbox: Bbox
    files: dict[str, Path] = field(default_factory=dict)
    feature_counts: dict[str, int] = field(default_factory=dict)
