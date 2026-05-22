"""Tests for OpenFOAM blockMesh helper output."""

from cfd_geometry.openfoam.blockmesh import write_blockmesh_dict, write_blockmesh_vertices


def test_write_blockmesh_vertices(tmp_path):
    out = tmp_path / "blockMeshDict_vertices.txt"
    info = write_blockmesh_vertices(
        out,
        x_min=-100.0,
        x_max=100.0,
        y_min=-50.0,
        y_max=50.0,
        z_max=200.0,
        cell_size=10.0,
    )
    text = out.read_text()
    assert "vertices" in text
    assert "blocks" in text
    assert info["nx"] == 20
    assert info["ny"] == 10
    assert info["nz"] == 20


def test_write_blockmesh_dict(tmp_path):
    out = tmp_path / "blockMeshDict"
    info = write_blockmesh_dict(
        out,
        x_min=0.0,
        x_max=50.0,
        y_min=0.0,
        y_max=50.0,
        z_max=100.0,
        cell_size=5.0,
    )
    text = out.read_text()
    assert "FoamFile" in text
    assert "boundary" in text
    assert "inlet" in text
    assert info["total_cells"] > 0
