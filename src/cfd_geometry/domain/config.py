"""Configuration for full-domain CFD geometry builds."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from cfd_geometry.constants import (
    DEFAULT_DEM_BUFFER_M,
    DEFAULT_DEM_MAX_RESOLUTION,
    DEFAULT_PLACE_BUFFER_M,
)
from cfd_geometry.download.bbox import Bbox


@dataclass
class DomainConfig:
    """
    One study area: download OSM inputs (optional) and extrude aligned STLs.

    Layout under ``output_dir``:

    - ``input/`` — shapefiles, dem.tif
    - ``output/`` — buildings.stl, trees.stl, etc.
    """

    output_dir: Path
    place: str | None = None
    bbox: Bbox | None = None

    run_download: bool = True
    download_layers: tuple[str, ...] = ("buildings", "trees", "highways")
    download_dem: bool = False
    place_buffer_m: float = DEFAULT_PLACE_BUFFER_M
    network_timeout: int = 180

    build_buildings: bool = True
    build_trees: bool = True
    build_highways: bool = False
    build_terrain: bool = False

    height_source: str = "osm"
    default_height: float = 9.0
    ground_buffer: float | None = 500.0
    auto_utm: bool = True
    target_crs: str | None = None
    tree_default_height: float = 10.0
    dem_max_resolution: int = DEFAULT_DEM_MAX_RESOLUTION
    terrain_z_reference: str = "center"
    dem_buffer_m: float = DEFAULT_DEM_BUFFER_M
    dem_bbox: Bbox | None = None

    input_subdir: str = "input"
    output_subdir: str = "output"

    def __post_init__(self) -> None:
        self.output_dir = Path(self.output_dir)
        if not self.place and not self.bbox:
            raise ValueError("Provide either place= or bbox=")
        if self.place and self.bbox:
            raise ValueError("Provide only one of place= or bbox=")

    @property
    def input_dir(self) -> Path:
        return self.output_dir / self.input_subdir

    @property
    def stl_dir(self) -> Path:
        return self.output_dir / self.output_subdir

    @property
    def buildings_shp(self) -> Path:
        return self.input_dir / "buildings.shp"

    @property
    def trees_shp(self) -> Path:
        return self.input_dir / "trees.shp"

    @property
    def highways_shp(self) -> Path:
        return self.input_dir / "highways.shp"

    dem_filename: str = "dem.tif"

    @property
    def dem_tif(self) -> Path:
        return self.input_dir / self.dem_filename


@dataclass
class DomainResult:
    """Summary from :func:`build_domain`."""

    config: DomainConfig
    bbox: Bbox | None = None
    target_crs: str | None = None
    offset: tuple[float, float] = (0.0, 0.0)
    input_files: dict[str, Path] = field(default_factory=dict)
    stl_files: dict[str, Path] = field(default_factory=dict)
    extrude_stats: dict[str, dict] = field(default_factory=dict)
