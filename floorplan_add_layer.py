#!/usr/bin/env python3
#
# floorplan_add_layer.py
#
# Inkscape extension entry point. Creates a new layer pre-named with one of
# the known semantic category prefixes, so users don't have to look up and
# type the prefix by hand.
#

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import inkex

from layer_naming import build_layer_name, unique_layer_name


class AddSemanticLayer(inkex.EffectExtension):
    def add_arguments(self, pars):
        pars.add_argument(
            "--category", dest="category", type=str, default="wall_outer_", help="Category prefix for the new layer."
        )
        pars.add_argument(
            "--suffix", dest="suffix", type=str, default="1", help="Name suffix appended after the category prefix."
        )
        pars.add_argument(
            "--placement",
            dest="placement",
            type=str,
            default="top",
            help="Where to insert the new layer: 'top' for a top-level layer, 'sub' for a sublayer of the active layer.",
        )

    def effect(self):
        name = build_layer_name(self.options.category, self.options.suffix)
        new_id = unique_layer_name(name, self.svg.get_ids())

        layer = inkex.Layer.new(new_id, id=new_id)

        parent = self.svg.get_current_layer() if self.options.placement == "sub" else self.svg
        parent.add(layer)


if __name__ == "__main__":
    AddSemanticLayer().run()
