"""Google Colab helpers."""

from __future__ import annotations


def setup_colab_widgets() -> bool:
    """
    Enable ipywidgets in Google Colab (required for the extent map).

    Returns True when running inside Colab and the widget manager was enabled.
    """
    try:
        import google.colab  # noqa: F401
    except ImportError:
        return False

    from google.colab import output

    output.enable_custom_widget_manager()
    return True
