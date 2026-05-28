from pathlib import Path

from cfd_geometry.notebook.install import find_repo_root, in_colab, verify_domain_import


def test_not_in_colab_by_default():
    assert in_colab() is False


def test_find_repo_root_from_notebooks_dir():
    repo = Path(__file__).resolve().parents[1]
    nb_dir = repo / "notebooks"
    assert find_repo_root(nb_dir) == repo


def test_verify_domain_import_ok():
    verify_domain_import()
