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

from categories import find_layer_label, get_scale_config, node_label, resolve_category
from mesh_repair import repair_geometry
from mesh_validator import find_cross_object_overlaps, validate_geometry
from openscad_writer import build_items, write_scad
from svg_parser import SVGParser

_GEOMETRY_WARNING_MESSAGES = {
    "self_intersecting": "shape {obj} is self-intersecting (bowtie/figure-8) and will likely produce a degenerate 3D mesh.",
    "unclosed": (
        "shape {obj} has an unclosed subpath; OpenSCAD's polygon() will silently auto-close it "
        "with a straight line, which may not match your intent."
    ),
    "degenerate": "shape {obj} has a near-zero-area subpath (collinear/duplicate points) and may not render.",
}

_GEOMETRY_WARNING_MESSAGES_AFTER_AUTO_FIX = {
    "self_intersecting": (
        "shape {obj} is still self-intersecting after auto-fix; automatic repair could only "
        "remove crossings one at a time and gave up before finding a simple polygon. This needs "
        "manual correction in the SVG."
    ),
}


def _node_descriptor(node):
    """Human-facing "'name' (layer 'layer_name')" description, for locating a node in Inkscape."""
    name = node_label(node)
    layer = find_layer_label(node)
    return f"'{name}' (layer '{layer}')" if layer else f"'{name}'"


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
        pars.add_argument(
            "--check_geometry",
            dest="check_geometry",
            type=inkex.Boolean,
            default=True,
            help="Warn about self-intersecting, unclosed, or degenerate (zero-area) shapes.",
        )
        pars.add_argument(
            "--check_overlap",
            dest="check_overlap",
            type=inkex.Boolean,
            default=False,
            help=(
                "Warn about overlapping objects that aren't fully nested (holes) inside one another. "
                "Off by default: mitered wall corners and floor-under-wall overlap are common and harmless."
            ),
        )
        pars.add_argument(
            "--auto_fix",
            dest="auto_fix",
            type=inkex.Boolean,
            default=False,
            help=(
                "Best-effort automatic repair of issues found by geometry checking: closes unclosed "
                "subpaths, drops zero-area subpaths, and untangles simple self-intersections. Not "
                "every issue can be fixed; anything left broken is still reported. Has no effect on "
                "overlap warnings. Enabling this also runs and reports geometry checking even if "
                "that checkbox is off."
            ),
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

        if self.options.check_geometry or self.options.auto_fix:
            warnings = validate_geometry(paths_dict)
            auto_fix_attempted = False
            if self.options.auto_fix and warnings:
                auto_fix_attempted = True
                repair_results = repair_geometry(paths_dict)
                self._emit_repair_summary(repair_results)
                warnings = validate_geometry(paths_dict)
            self._emit_warnings(warnings, auto_fix_attempted=auto_fix_attempted)

        if self.options.check_overlap:
            self._emit_warnings(find_cross_object_overlaps(paths_dict))

        paths_with_modules = []
        for node, subpath_list in paths_dict.items():
            _, module_name = resolve_category(node)
            if not module_name:
                obj = _node_descriptor(node)
                if obj not in self._warnings_printed:
                    inkex.errormsg(f"Warning: Object {obj} did not match any category prefix. Falling back to 'wall'.")
                    self._warnings_printed.add(obj)
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

    def _emit_warnings(self, warnings, auto_fix_attempted=False):
        for w in warnings:
            obj = _node_descriptor(w.node)
            if w.kind == "overlap":
                other_obj = _node_descriptor(w.other_node)
                a, b = sorted((obj, other_obj))
                key = f"overlap:{a}:{b}"
                msg = (
                    f"Warning: Objects {a} and {b} overlap without one fully containing the other; "
                    "this may produce coincident/overlapping faces in the 3D output."
                )
            else:
                key = f"{w.kind}:{obj}"
                messages = _GEOMETRY_WARNING_MESSAGES
                if auto_fix_attempted and w.kind in _GEOMETRY_WARNING_MESSAGES_AFTER_AUTO_FIX:
                    messages = _GEOMETRY_WARNING_MESSAGES_AFTER_AUTO_FIX
                msg = f"Warning: {messages[w.kind].format(obj=obj)}"
            if key not in self._warnings_printed:
                self._warnings_printed.add(key)
                inkex.errormsg(msg)

    def _emit_repair_summary(self, repair_results):
        counts = {}
        for r in repair_results:
            if r.fixed:
                counts[r.kind] = counts.get(r.kind, 0) + 1
        if not counts:
            return
        parts = []
        if counts.get("unclosed"):
            parts.append(f"closed {counts['unclosed']} unclosed subpath(s)")
        if counts.get("degenerate"):
            parts.append(f"removed {counts['degenerate']} degenerate (near-zero-area) subpath(s)")
        if counts.get("self_intersecting"):
            parts.append(f"untangled {counts['self_intersecting']} self-intersecting subpath(s)")
        inkex.errormsg(f"Auto-fix: {', '.join(parts)}.")

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
