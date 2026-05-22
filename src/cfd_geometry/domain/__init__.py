"""End-to-end domain build: download inputs and export aligned STLs."""

from cfd_geometry.domain.config import DomainConfig, DomainResult
from cfd_geometry.domain.pipeline import build_domain

__all__ = ["DomainConfig", "DomainResult", "build_domain"]
