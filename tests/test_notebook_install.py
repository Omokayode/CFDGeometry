from cfd_geometry.notebook.install import in_colab


def test_not_in_colab_by_default():
    assert in_colab() is False
