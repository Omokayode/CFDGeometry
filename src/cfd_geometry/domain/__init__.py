"""End-to-end domain build: download inputs and export aligned STLs."""

from cfd_geometry.domain.config import DomainConfig, DomainResult

__all__ = ["DomainConfig", "DomainResult", "build_domain"]


def __getattr__(name: str):
    if name == "build_domain":
        from cfd_geometry.domain.pipeline import build_domain

        return build_domain
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
