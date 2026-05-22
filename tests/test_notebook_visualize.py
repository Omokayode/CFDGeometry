import pytest

from cfd_geometry.mesh.stl_io import write_stl_binary


@pytest.fixture
def tiny_stl(tmp_path):
    tri = [[0.0, 0.0, 0.0], [10.0, 0.0, 0.0], [0.0, 10.0, 0.0]]
    path = tmp_path / "box.stl"
    write_stl_binary(path, [tri, tri])
    return path


def test_plot_stl_files_builds_figure(tiny_stl):
    plotly = pytest.importorskip("plotly")
    from cfd_geometry.notebook.visualize import plot_stl_files

    fig = plot_stl_files({"buildings": tiny_stl}, show=False)
    assert len(fig.data) == 1
    assert fig.data[0].type == "mesh3d"


def test_show_figure_uses_html_display(tiny_stl):
    pytest = __import__("pytest")
    pytest.importorskip("plotly")
    from unittest.mock import MagicMock, patch

    from cfd_geometry.notebook.visualize import _show_figure, plot_stl_files

    fig = plot_stl_files({"buildings": tiny_stl}, show=False)
    mock_display = MagicMock()
    with patch("IPython.display.display", mock_display), patch(
        "IPython.display.HTML", MagicMock()
    ):
        _show_figure(fig)
    assert mock_display.called


def test_plot_stl_files_missing_raises(tmp_path):
    pytest.importorskip("plotly")
    from cfd_geometry.notebook.visualize import plot_stl_files

    with pytest.raises(FileNotFoundError):
        plot_stl_files({"missing": tmp_path / "nope.stl"}, show=False)
