def test_lazy_plot_import():
    pytest = __import__("pytest")
    pytest.importorskip("plotly")
    import cfd_geometry.notebook as nb

    assert callable(nb.plot_domain_stls)
