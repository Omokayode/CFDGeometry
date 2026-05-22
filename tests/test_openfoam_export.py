"""Tests for OpenFOAM case snippet export."""

from cfd_geometry.openfoam.blockmesh import write_blockmesh_dict
from cfd_geometry.openfoam.export import export_openfoam_case


def test_blockmesh_dict_does_not_write_vertices_sidecar(tmp_path):
    out = tmp_path / "blockMeshDict"
    (tmp_path / "blockMeshDict_vertices.txt").write_text("old", encoding="utf-8")
    (tmp_path / "blockMeshDict.vertices.txt").write_text("old", encoding="utf-8")
    write_blockmesh_dict(
        out,
        x_min=0.0,
        x_max=100.0,
        y_min=0.0,
        y_max=50.0,
        z_max=60.0,
        cell_size=10.0,
    )
    assert out.is_file()
    assert not (tmp_path / "blockMeshDict.vertices.txt").exists()
    assert not (tmp_path / "blockMeshDict_vertices.txt").exists()


def test_export_openfoam_writes_snappy_and_blockmesh(tmp_path):
    bounds = {
        "x_min": 100.0,
        "x_max": 200.0,
        "y_min": 50.0,
        "y_max": 150.0,
        "z_min": 0.0,
        "z_max": 25.0,
    }
    stl = tmp_path / "buildings_on_dem.stl"
    stl.write_bytes(b"x" * 100)
    info = export_openfoam_case(
        tmp_path / "output",
        building_bounds=bounds,
        max_building_height=25.0,
        ground_buffer_m=500.0,
        stl_files={"buildings_on_dem": stl, "terrain": tmp_path / "terrain.stl"},
        refinement_buffer_m=10.0,
    )
    out = tmp_path / "output"
    assert (out / "blockMeshDict").is_file()
    snappy = (out / "snappyHexMeshDict").read_text()
    assert "refinementBox" in snappy
    assert "buildings_on_dem" in snappy
    assert "searchableBox" in snappy
    assert "locationInMesh" in snappy
    assert info["nx"] > 0
    cmd = (out / "snappyHexMeshConfig.command").read_text()
    assert "snappyHexMeshConfig" in cmd
