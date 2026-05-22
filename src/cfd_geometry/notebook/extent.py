"""Interactive WGS84 extent selection for Jupyter notebooks."""

from __future__ import annotations

from typing import Any

from cfd_geometry.download.bbox import Bbox
from cfd_geometry.notebook._geo import resolve_map_center


def _require_notebook_deps() -> tuple[Any, Any]:
    try:
        import ipyleaflet
        import ipywidgets as widgets
    except ImportError as exc:
        raise ImportError(
            "Notebook extent picker requires optional dependencies:\n"
            "  pip install -e '.[notebook]'"
        ) from exc
    return ipyleaflet, widgets


def bbox_from_draw_geojson(geo_json: dict) -> Bbox:
    """Build a ``Bbox`` from an ipyleaflet DrawControl GeoJSON feature."""
    geom = geo_json.get("geometry") or {}
    gtype = geom.get("type")
    coords = geom.get("coordinates")
    if not coords:
        raise ValueError("Drawn feature has no coordinates")

    if gtype == "Polygon":
        ring = coords[0]
    elif gtype == "Rectangle":
        # Some draw backends emit a polygon ring; treat like polygon.
        ring = coords[0] if isinstance(coords[0][0], (list, tuple)) else coords
    else:
        raise ValueError(f"Expected a rectangle/polygon, got geometry type {gtype!r}")

    lons = [float(c[0]) for c in ring]
    lats = [float(c[1]) for c in ring]
    box = Bbox(
        west=min(lons),
        south=min(lats),
        east=max(lons),
        north=max(lats),
    )
    box.validate()
    return box


class ExtentSelector:
    """
    Map widget: draw a rectangle, then click **Use this extent**.

    Read ``.bbox`` after confirming, or pass the result to ``DownloadConfig`` /
    ``DomainConfig`` as ``bbox=selector.bbox``.
    """

    def __init__(
        self,
        *,
        center: tuple[float, float] | None = None,
        place: str | None = None,
        zoom: int = 14,
        map_height: str = "480px",
    ) -> None:
        ipyleaflet, widgets = _require_notebook_deps()

        lat, lon = resolve_map_center(center=center, place=place)
        self._draft: Bbox | None = None
        self._bbox: Bbox | None = None
        self._drawn_layer: Any | None = None

        self._status = widgets.HTML(
            value=(
                "<b>Study extent</b><br>"
                "Use the rectangle tool on the map, adjust it, then click "
                "<b>Use this extent</b>."
            )
        )
        self._confirm = widgets.Button(
            description="Use this extent",
            button_style="success",
            disabled=True,
        )
        self._clear = widgets.Button(description="Clear", disabled=True)

        # Only enable rectangle; empty dicts disable other draw tools (ipyleaflet API).
        draw = ipyleaflet.DrawControl(
            rectangle={
                "shapeOptions": {
                    "color": "#2563eb",
                    "weight": 2,
                    "fillOpacity": 0.15,
                }
            },
            polygon={},
            polyline={},
            circle={},
            marker={},
            circlemarker={},
            edit=True,
            remove=True,
        )

        self._map = ipyleaflet.Map(
            center=(lat, lon),
            zoom=zoom,
            scroll_wheel_zoom=True,
            layout=widgets.Layout(width="100%", height=map_height),
        )
        self._map.add_control(draw)

        def _on_draw(_target: Any, action: str, geo_json: dict) -> None:
            if action == "deleted":
                self._set_bbox(None)
                return
            if action not in ("created", "edited"):
                return
            try:
                box = bbox_from_draw_geojson(geo_json)
            except ValueError as exc:
                self._status.value = f"<span style='color:#b91c1c'>{exc}</span>"
                self._confirm.disabled = True
                return
            self._set_bbox(box, highlight=geo_json)

        draw.on_draw(_on_draw)

        def _confirm_click(_btn: Any) -> None:
            if self._draft is None:
                return
            self._bbox = self._draft
            b = self._bbox
            self._status.value = (
                f"<b>Confirmed extent (WGS84)</b><br>"
                f"west={b.west:.6f}, south={b.south:.6f}, "
                f"east={b.east:.6f}, north={b.north:.6f}<br>"
                f"<code>--bbox {b.west:.6f} {b.south:.6f} {b.east:.6f} {b.north:.6f}</code>"
            )

        def _clear_click(_btn: Any) -> None:
            self._set_bbox(None)
            if self._drawn_layer is not None:
                try:
                    self._map.remove_layer(self._drawn_layer)
                except Exception:
                    pass
                self._drawn_layer = None

        self._confirm.on_click(_confirm_click)
        self._clear.on_click(_clear_click)

        toolbar = widgets.HBox([self._confirm, self._clear])
        self.widget = widgets.VBox(
            [
                widgets.HTML(
                    value=(
                        "<p>Draw a <b>rectangle</b> on the map for your OSM / DEM study area "
                        "(WGS84). Pan and zoom as needed.</p>"
                    )
                ),
                self._map,
                toolbar,
                self._status,
            ]
        )

    def _set_bbox(self, box: Bbox | None, *, highlight: dict | None = None) -> None:
        self._draft = box
        if box is None:
            self._bbox = None
        has = box is not None
        self._confirm.disabled = not has
        self._clear.disabled = not (has or self._bbox is not None)
        if box is None:
            self._status.value = (
                "<b>Study extent</b><br>Draw a rectangle on the map, then confirm."
            )
            return
        self._status.value = (
            f"<b>Selected — click “Use this extent”</b><br>"
            f"west={box.west:.6f}, south={box.south:.6f}, "
            f"east={box.east:.6f}, north={box.north:.6f}"
        )
        if highlight is not None:
            ipyleaflet, _ = _require_notebook_deps()
            if self._drawn_layer is not None:
                try:
                    self._map.remove_layer(self._drawn_layer)
                except Exception:
                    pass
            self._drawn_layer = ipyleaflet.GeoJSON(data=highlight)
            self._map.add_layer(self._drawn_layer)

    @property
    def bbox(self) -> Bbox | None:
        """Last confirmed WGS84 extent, or ``None`` until the user confirms."""
        return self._bbox

    def _ipython_display_(self) -> None:
        from IPython.display import display

        display(self.widget)

    def display(self) -> None:
        """Show the selector in the active notebook output."""
        self._ipython_display_()


def select_extent(
    *,
    center: tuple[float, float] | None = None,
    place: str | None = None,
    zoom: int = 14,
) -> ExtentSelector:
    """
    Open an interactive map to pick ``west south east north`` (degrees).

    Example::

        sel = select_extent(place="Milwaukee, Wisconsin, USA")
        sel  # draw rectangle → "Use this extent"
        from cfd_geometry.download import DownloadConfig, download_domain
        download_domain(DownloadConfig(output_dir="data/input", bbox=sel.bbox))
    """
    return ExtentSelector(center=center, place=place, zoom=zoom)
