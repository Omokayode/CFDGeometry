"""Tree mesh model strategies."""

from __future__ import annotations

from dataclasses import dataclass

from shapely.geometry import Point

from cfd_geometry.trees.geometry import create_tree_canopy, default_tree_config


@dataclass
class CanopyTreeModel:
    """Trunk + canopy (cylinder or sphere from cfg)."""

    name: str = "canopy"

    def triangles_at(self, point: Point, *, height: float, cfg: dict) -> list:
        trunk_h = height * cfg["trunk_height_ratio"]
        canopy_h = height - trunk_h
        canopy_r = height * cfg["canopy_radius_ratio"]
        return create_tree_canopy(
            point,
            canopy_r,
            trunk_h,
            canopy_h,
            cfg["trunk_radius"],
            canopy_shape=cfg.get("canopy_shape", "cylinder"),
            sides=cfg.get("detail_level", 12),
        )


@dataclass
class CylinderTreeModel:
    """Force cylindrical canopy."""

    name: str = "cylinder"

    def triangles_at(self, point: Point, *, height: float, cfg: dict) -> list:
        cfg = {**default_tree_config(), **cfg, "canopy_shape": "cylinder"}
        return CanopyTreeModel().triangles_at(point, height=height, cfg=cfg)


@dataclass
class SphereTreeModel:
    """Force spherical canopy."""

    name: str = "sphere"

    def triangles_at(self, point: Point, *, height: float, cfg: dict) -> list:
        cfg = {**default_tree_config(), **cfg, "canopy_shape": "sphere"}
        return CanopyTreeModel().triangles_at(point, height=height, cfg=cfg)


@dataclass
class SkipTreeModel:
    """Do not generate tree geometry."""

    name: str = "skip"

    def triangles_at(self, point: Point, *, height: float, cfg: dict) -> list:
        return []


def tree_model_from_name(name: str) -> CanopyTreeModel | CylinderTreeModel | SphereTreeModel | SkipTreeModel:
    """Names: ``canopy``, ``cylinder``, ``sphere``, ``skip``."""
    key = name.lower().strip()
    if key in ("canopy", "default"):
        return CanopyTreeModel()
    if key == "cylinder":
        return CylinderTreeModel()
    if key == "sphere":
        return SphereTreeModel()
    if key == "skip":
        return SkipTreeModel()
    raise ValueError(f"Unknown tree model: {name!r}")
