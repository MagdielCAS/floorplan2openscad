#!/usr/bin/env python3
#
# floorplan_add_ruler.py
#
# Inkscape extension entry point. Drops a scale-ruler guide (a bar with end
# ticks and a "1 m"-style label) into the document, sized against the
# document's real width/height/viewBox. The bar is left visible and
# selectable on purpose: the user can drag/scale it to match a known
# real-world distance in their drawing, and floorplan2openscad.py reads the
# bar's resulting length back to calibrate the whole floor plan's scale
# (see find_ruler_calibration in svg_parser.py). The ruler is always
# excluded from the .scad output regardless of its visibility, so it never
# gets rendered as a wall.
#

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import inkex

from layer_naming import unique_layer_name
from ruler import RULER_LENGTH_ATTR, RULER_MARKER_ATTR, ruler_geometry
from svg_parser import SVGParser

_RULER_COLOR = "#e6007e"


def _document_extent(svg):
    """Return (width, height, x, y, scale) describing the page in viewBox coordinates.

    scale is the ratio of the document's physical pixel size to its viewBox
    size along the x axis (1.0 when there's no viewBox, i.e. user units are
    already physical px). Mirrors FloorplanToOpenSCAD._handle_view_box.
    """
    parser = SVGParser()
    width_px = parser.length_to_px(svg.get("width", "100")) or 100.0
    height_px = parser.length_to_px(svg.get("height", "100")) or 100.0

    viewbox = svg.get("viewBox")
    if viewbox:
        vinfo = viewbox.strip().replace(",", " ").split()
        if len(vinfo) >= 4 and float(vinfo[2]) != 0 and float(vinfo[3]) != 0:
            vx, vy, vw, vh = (float(v) for v in vinfo)
            return vw, vh, vx, vy, width_px / vw

    return width_px, height_px, 0.0, 0.0, 1.0


class AddScaleRuler(inkex.EffectExtension):
    def add_arguments(self, pars):
        pars.add_argument("--length", dest="length", type=str, default="1m", help="Real-world length the ruler bar represents.")
        pars.add_argument(
            "--corner",
            dest="corner",
            type=str,
            default="bottom-left",
            help="Which page corner to anchor the ruler to.",
        )

    def effect(self):
        doc_width, doc_height, doc_x, doc_y, doc_scale = _document_extent(self.svg)

        geometry = ruler_geometry(
            self.options.length,
            self.options.corner,
            doc_width,
            doc_height,
            doc_scale=doc_scale,
            doc_x=doc_x,
            doc_y=doc_y,
        )

        layer_id = unique_layer_name("ruler_guide", self.svg.get_ids())
        layer = inkex.Layer.new(layer_id, id=layer_id)
        layer.set(RULER_MARKER_ATTR, "1")

        stroke_width = max(1.0, geometry["length_units"] * 0.004)
        font_size = max(10.0, geometry["length_units"] * 0.045)

        bar = geometry["bar"]
        bar_path = inkex.PathElement()
        bar_path.set("id", f"{layer_id}_bar")
        bar_path.set("d", f"M {bar[0]},{bar[1]} L {bar[2]},{bar[3]}")
        bar_path.set(RULER_LENGTH_ATTR, str(geometry["length_mm"]))
        bar_path.set("style", f"fill:none;stroke:{_RULER_COLOR};stroke-width:{stroke_width:.3f};stroke-linecap:square")
        layer.add(bar_path)

        tick_a, tick_b = geometry["ticks"]
        ticks_path = inkex.PathElement()
        ticks_path.set("id", f"{layer_id}_ticks")
        ticks_path.set(
            "d",
            f"M {tick_a[0]},{tick_a[1]} L {tick_a[2]},{tick_a[3]} M {tick_b[0]},{tick_b[1]} L {tick_b[2]},{tick_b[3]}",
        )
        ticks_path.set("style", f"fill:none;stroke:{_RULER_COLOR};stroke-width:{stroke_width:.3f};stroke-linecap:square")
        layer.add(ticks_path)

        label = geometry["label"]
        text = inkex.TextElement()
        text.set("id", f"{layer_id}_label")
        text.set("x", str(label["x"]))
        text.set("y", str(label["y"]))
        text.set("style", f"font-size:{font_size:.2f}px;font-family:sans-serif;text-anchor:middle;fill:{_RULER_COLOR}")
        text.text = label["text"]
        layer.add(text)

        self.svg.add(layer)


if __name__ == "__main__":
    AddScaleRuler().run()
