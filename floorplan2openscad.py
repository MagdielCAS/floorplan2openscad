#!/usr/bin/env python3
#
# floorplan2openscad.py
#
# Inkscape extension entry point. Thin shell that wires SVGParser, category
# resolution, and OpenSCAD writing into the inkex.EffectExtension lifecycle.
#

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import inkex

from categories import get_scale_config, resolve_category
from openscad_writer import build_items, write_scad
from svg_parser import SVGParser


class FloorplanToOpenSCAD(inkex.EffectExtension):
    def __init__(self):
        super().__init__()
        self.dpi = 96.0
        self.basename = "floorplan"
        self.docTransform = inkex.Transform()
        self.docHeight = 0.0
        self.docWidth = 0.0
        self._warnings_printed = set()

    def add_arguments(self, pars):
        pars.add_argument(
            "--fname",
            dest="fname",
            type=str,
            default="{NAME}.scad",
            help="OpenSCAD output file (use {NAME} to mirror the SVG filename).",
        )
        pars.add_argument("--base_scale", dest="base_scale", type=str, default="3cm", help="Scale factor: 3cm, 1cm, 1mm, or 1m.")
        pars.add_argument(
            "--smoothness",
            dest="smoothness",
            type=float,
            default=0.2,
            help="Bezier curve smoothing tolerance (smaller = smoother).",
        )

    def effect(self):
        self._handle_view_box()

        parser = SVGParser(smoothness=self.options.smoothness)
        parser.dpi = self.dpi

        if self.options.ids:
            selected = [self.svg.selected[id_] for id_ in self.options.ids]
            paths_dict, cx, cy = parser.parse(selected, self.docTransform)
        else:
            paths_dict, cx, cy = parser.parse(self.svg, self.docTransform)

        if not paths_dict:
            inkex.errormsg("Warning: No valid paths or shapes found in document.")
            return

        paths_with_modules = []
        for node, subpath_list in paths_dict.items():
            _, module_name = resolve_category(node)
            if not module_name:
                name = node.get("{http://www.inkscape.org/namespaces/inkscape}label") or node.get("id", "unnamed")
                if name not in self._warnings_printed:
                    inkex.errormsg(f"Warning: Object '{name}' did not match any category prefix. Falling back to 'wall'.")
                    self._warnings_printed.add(name)
                module_name = "wall"
            paths_with_modules.append((module_name, subpath_list))

        scale_config = get_scale_config(self.options.base_scale)
        items = build_items(paths_with_modules, cx, cy)

        out_fname = self.options.fname.format(**{"NAME": self.basename})
        if not os.path.isabs(out_fname) and "PWD" in os.environ:
            out_fname = os.path.join(os.environ["PWD"], out_fname)
        scad_fname = os.path.expanduser(out_fname)

        try:
            with open(scad_fname, "w") as f:
                write_scad(f, self.basename, items, scale_config)
        except IOError as e:
            inkex.errormsg(f"Unable to write file {self.options.fname}: {e}")

    # ----------------------------------------------------------------- helpers

    def _handle_view_box(self):
        inkscape_version = self.svg.get("{http://www.inkscape.org/namespaces/inkscape}version")
        sodipodi_docname = self.svg.get("{http://sodipodi.sourceforge.net/DTD/sodipodi-0.0.dtd}docname")
        if sodipodi_docname is None:
            sodipodi_docname = "floorplan"
        self.basename = os.path.splitext(os.path.basename(re.sub(r"\.SVG", "", sodipodi_docname, flags=re.I)))[0]

        if inkscape_version:
            m = re.match(r"(\d+)\.(\d+)", inkscape_version)
            if m and (int(m.group(1)) > 0 or int(m.group(2)) > 91):
                self.dpi = 96.0

        parser = SVGParser()
        parser.dpi = self.dpi
        self.docHeight = parser.length_to_px(self.svg.get("height", "100"))
        self.docWidth = parser.length_to_px(self.svg.get("width", "100"))

        if self.docHeight is None:
            self.docHeight = 100.0
        if self.docWidth is None:
            self.docWidth = 100.0

        viewbox = self.svg.get("viewBox")
        if viewbox:
            vinfo = viewbox.strip().replace(",", " ").split()
            if len(vinfo) >= 4 and float(vinfo[2]) != 0 and float(vinfo[3]) != 0:
                sx = self.docWidth / float(vinfo[2])
                sy = self.docHeight / float(vinfo[3])
                self.docTransform = inkex.Transform(f"scale({sx},{sy})")
                return
        self.docTransform = inkex.Transform()


if __name__ == "__main__":
    FloorplanToOpenSCAD().run()
