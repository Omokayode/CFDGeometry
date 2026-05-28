"""Guard against resolve_bbox scoping bugs in build_domain."""

import inspect


def test_build_domain_has_no_inner_resolve_bbox_import():
    from cfd_geometry.domain import pipeline

    source = inspect.getsource(pipeline.build_domain)
    assert "from cfd_geometry.download.osm import resolve_bbox" not in source
