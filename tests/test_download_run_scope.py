"""Guard against resolve_bbox scoping bugs in download_domain."""

import inspect


def test_download_domain_has_no_inner_resolve_bbox_import():
    from cfd_geometry.download import run

    source = inspect.getsource(run.download_domain)
    first_bbox = source.index("bbox = ")
    after_first_bbox = source[first_bbox:]
    assert "from cfd_geometry.download.osm import resolve_bbox" not in after_first_bbox
