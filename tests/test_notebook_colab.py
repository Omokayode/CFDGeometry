from cfd_geometry.notebook.colab import setup_colab_widgets


def test_setup_colab_widgets_outside_colab():
    assert setup_colab_widgets() is False
