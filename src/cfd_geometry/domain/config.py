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
    download_dsm: bool = False
    download_dtm: bool = False
    opentopography_dsm_product: str = "COP30"
    opentopography_dtm_product: str = "SRTMGL1"
    opentopography_demtype: str = "SRTMGL1"
    use_usgs10m: bool = False
    auto_usgs10m: bool = False
    use_dsm_heights: bool = False
    dsm_file: str | None = None
    dtm_file: str | None = None
    dem_file: str | None = None
    build_buildings_lidar: bool = False
    stepped_facades: bool = False
    place_buffer_m: float = DEFAULT_PLACE_BUFFER_M
    study_buffer_m: float | None = None
    network_timeout: int = 180

    build_buildings: bool = True
    build_trees: bool = True
    build_highways: bool = False
    build_terrain: bool = False

    height_source: str = "osm"
    default_height: float = 9.0
    resolve_overlaps: str | bool = False
    overlap_ratio_threshold: float = 0.5
    complement_raster: str | None = None
    simplify_tolerance: float | None = None
    tree_model: str = "canopy"
    canopy_raster: str | None = None
    ground_buffer: float | None = 500.0
    auto_utm: bool = True
    target_crs: str | None = None
    tree_default_height: float = 10.0
    dem_max_resolution: int = DEFAULT_DEM_MAX_RESOLUTION
    terrain_z_reference: str = "center"
    dem_buffer_m: float = DEFAULT_DEM_BUFFER_M
    dem_bbox: Bbox | None = None
    clip_rasters_to_dem: bool = True
    workers: int = 1
    export_openfoam: bool = False
    refinement_buffer_m: float = 10.0
    openfoam_cell_size: float = 5.0

    input_subdir: str = "input"
    output_subdir: str = "output"

    def __post_init__(self) -> None:
        self.output_dir = Path(self.output_dir)
        if not self.place and not self.bbox:
            raise ValueError("Provide either place= or bbox=")
        if self.place and self.bbox:
            raise ValueError("Provide only one of place= or bbox=")
        if self.study_buffer_m is not None:
            self.place_buffer_m = self.study_buffer_m
            self.dem_buffer_m = self.study_buffer_m
        if self.use_dsm_heights or self.download_dsm:
            self.use_dsm_heights = True
        if self.download_dsm and not self.download_dem:
            self.download_dem = True
        if self.download_dsm and not self.download_dtm:
            self.download_dtm = True
        if self.use_usgs10m:
            from cfd_geometry.download.dsm import USGS10M_PRODUCT

            self.opentopography_dsm_product = USGS10M_PRODUCT
            self.opentopography_dtm_product = USGS10M_PRODUCT
            self.opentopography_demtype = USGS10M_PRODUCT

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
    dsm_filename: str = "dsm.tif"
    dtm_filename: str = "dtm.tif"

    @property
    def dem_tif(self) -> Path:
        return self.input_dir / self.dem_filename

    @property
    def dsm_tif(self) -> Path:
        return self.input_dir / self.dsm_filename

    @property
    def dtm_tif(self) -> Path:
        return self.input_dir / self.dtm_filename


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
