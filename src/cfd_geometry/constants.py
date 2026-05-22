"""Shared defaults for coordinate systems and geometry."""

DEFAULT_TARGET_CRS = "EPSG:32616"
DEFAULT_EPSG = 32616

# Street/point geocode buffer: 250 m → ~500 m × 500 m download box
DEFAULT_PLACE_BUFFER_M = 250.0

# Max raster dimension when loading/reprojecting DEMs (avoids TiB allocations)
DEFAULT_DEM_MAX_RESOLUTION = 800
MAX_DEM_PIXELS = 25_000_000
