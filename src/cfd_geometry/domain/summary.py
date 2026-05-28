"""Write domain build summary JSON."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from cfd_geometry.domain.config import DomainResult


def write_domain_summary(result: DomainResult, path: str | Path | None = None) -> Path:
    """Serialize build metadata for OpenFOAM / ParaView setup."""
    config = result.config
    out = Path(path or config.stl_dir / "domain_summary.json")

    bbox = None
    if result.bbox is not None:
        bbox = {
            "west": result.bbox.west,
            "south": result.bbox.south,
            "east": result.bbox.east,
            "north": result.bbox.north,
        }

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "place": config.place,
        "bbox_wgs84": bbox,
        "target_crs": result.target_crs,
        "offset_m": {"x": result.offset[0], "y": result.offset[1]},
        "place_buffer_m": config.place_buffer_m,
        "dem_buffer_m": config.dem_buffer_m,
        "study_buffer_m": config.study_buffer_m,
        "terrain_z_reference": config.terrain_z_reference,
        "input_files": {k: str(v) for k, v in result.input_files.items()},
        "stl_files": {k: str(v) for k, v in result.stl_files.items()},
        "extrude_stats": result.extrude_stats,
        "openfoam": result.extrude_stats.get("openfoam"),
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"  Summary: {out}")
    return out
