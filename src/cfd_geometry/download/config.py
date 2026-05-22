"""Configuration for auto-downloading study-area inputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from cfd_geometry.constants import DEFAULT_PLACE_BUFFER_M
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
    dem_filename: str = "dem.tif"
    buildings_filename: str = "buildings.shp"
    trees_filename: str = "trees.shp"
    highways_filename: str = "highways.shp"
    opentopography_demtype: str = "SRTMGL1"
    network_timeout: int = 180
    place_buffer_m: float = DEFAULT_PLACE_BUFFER_M

    def __post_init__(self) -> None:
        self.output_dir = Path(self.output_dir)
        if not self.place and not self.bbox:
            raise ValueError("Provide either place= or bbox=")
        if self.place and self.bbox:
            raise ValueError("Provide only one of place= or bbox=")
        unknown = set(self.layers) - {"buildings", "trees", "highways", "dem"}
        if unknown:
            raise ValueError(f"Unknown layers: {unknown}")


@dataclass
class DownloadResult:
    """Paths and counts from a download run."""

    output_dir: Path
    bbox: Bbox
    files: dict[str, Path] = field(default_factory=dict)
    feature_counts: dict[str, int] = field(default_factory=dict)
