# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An Inkscape extension (Python 3.12) that converts 2D SVG floor plans into parametric 3D OpenSCAD models. It is **semantic**: it reads Inkscape layer/object ID prefixes and maps them to specialized OpenSCAD modules (walls, doors, windows, slabs, etc.) rather than doing a generic path conversion.

## Running and testing

Dependencies and dev tooling are managed with `uv`. Common tasks are wrapped in the `Makefile`:

```bash
make install     # uv sync --group dev
make test        # pytest
make coverage    # pytest with term + html coverage report
make lint        # ruff check
make format      # ruff format
make convert     # run the extension against an SVG (SVG=, OUT=, SCALE=)
make validate-inx  # xmllint --noout on the .inx descriptor
```

`categories.py`, `geometry.py`, and `openscad_writer.py` are pure Python and covered by `tests/`. `svg_parser.py` and `floorplan2openscad.py` import `inkex`, which is bundled with Inkscape rather than pip-installable, so `make convert` points `PYTHONPATH` at Inkscape's bundled `inkex` source (`INKEX_PATH`, auto-detected per OS, overridable) and installs `inkex`'s pure-pip runtime deps (numpy, lxml, Pillow, tinycss2, pyserial, cssselect — no Cairo needed) via the `inkex-runtime` dependency group. Reload after editing: in Inkscape, go to Extensions → Reload All Extensions (or restart Inkscape).

Python version is pinned to `3.12.0` via `.tool-versions` (asdf).

Pre-commit hooks (`.pre-commit-config.yaml`) run ruff lint/format, INX well-formedness, and the test suite before each commit — install with `uv run pre-commit install`. CI (`.github/workflows/ci.yml`) runs the same checks plus an end-to-end SVG→OpenSCAD smoke test on Ubuntu with Inkscape installed via apt. Tagging a commit `vX.Y.Z` (matching the `version` in `pyproject.toml`) triggers `.github/workflows/release.yml`, which packages the extension into a `floorplan2openscad/` zip and publishes it as a GitHub release.

## Architecture

The extension is two files:

- **`floorplan2openscad.inx`** — Inkscape extension descriptor XML. Declares the UI parameters (`fname`, `base_scale`, `smoothness`) and registers the script under *Extensions → Generate from Path → Semantic Floorplan to OpenSCAD*.
- **`floorplan2openscad.py`** — All logic lives here in `FloorplanToOpenSCAD(inkex.EffectExtension)`.

### Pipeline inside `effect()`

1. **SVG traversal** (`recursivelyTraverseSvg`) — walks the SVG node tree, accumulates cumulative `inkex.Transform` matrices, and converts every shape type (path, rect, line, polyline, polygon, ellipse/circle) to a unified path representation.

2. **Bezier flattening** (`getPathVertices` → `subdivideCubicPath`) — recursively subdivides cubic bezier curves until segment deviation is below the `smoothness` threshold, producing a list of `(x, y)` vertex arrays per subpath. Results are stored in `self.paths[node]`.

3. **Hole detection** (`polyInPoly` / `pointInPoly` / `bboxInBBox`) — for each node with multiple subpaths, determines parent/child containment relationships to build OpenSCAD `polygon(points, paths)` with hole indexes.

4. **Category matching** (`get_category_for_node`) — checks the node's `id` and `inkscape:label` attributes (and then walks up to parent groups/layers) against the `CATEGORIES` dict prefix table. Unmatched objects fall back to the generic `wall` module and emit a warning.

5. **OpenSCAD output** — writes a single `.scad` file in three sections:
   - Global parametric variables (`WALL_HEIGHT`, `DOOR_HEIGHT`, `WINDOW_SILL`, etc.) expressed as ratios of `BASE_Z_SCALE=1` so the user can tweak one number.
   - Inline module definitions for all semantic types (wall, wall_outer, wall_inner, wall_balcony, floor_slab, door_wood, door_glass, sliding_glass_door, window_standard, wardrobe).
   - Coordinate arrays and `union() { apply_svg_scale() { ... } }` call block.

### Semantic categories

The `CATEGORIES` dict (top of the file) maps layer/ID prefix strings → OpenSCAD module names. Adding a new architectural type requires: (1) adding an entry to `CATEGORIES`, and (2) writing the corresponding OpenSCAD module in the string written to the output file inside `effect()`.

### Scale system

The `base_scale` option selects a preset that sets all dimensional constants (wall height, door clearance, sill heights, floor thickness, and a `scale_factor` that converts SVG px to real-world units). All values in the output are written as `{raw_value}/{raw_value_at_3cm} * BASE_Z_SCALE` expressions so the user can rescale the model by changing a single OpenSCAD variable.

## OpenSCAD constructs used in generated output

The generated `.scad` files use a small, fixed set of OpenSCAD primitives. Reference: [OpenSCAD User Manual](https://en.wikibooks.org/wiki/OpenSCAD_User_Manual) / [official docs](https://openscad.org/documentation.html).

**`polygon(points, paths, convexity)`** — the core 2D primitive. When `paths` is omitted, all points form one outline. When multiple path index arrays are supplied, the first is the outer contour and the rest are holes (subtracted like `difference()`). `convexity=10` is set on all calls to support correct preview of non-convex shapes.

**`linear_extrude(height, convexity)`** — lifts a 2D polygon into a 3D solid along Z. Every architectural element is an extruded polygon; there is no mesh geometry.

**`offset(delta)`** — shrinks or expands a 2D polygon. Used inside `door_glass`, `door_wood` (sliding), and `window_standard` modules to carve out the interior of a frame: the outer polygon minus an `offset(delta=-FRAME_WIDTH)` inner polygon produces the frame ring via `difference()`.

**`translate([x,y,z])`** — used to stack sub-elements vertically. Window sill walls sit at Z=0, the frame and glass span `[WINDOW_SILL, WINDOW_HEADER]`, and the lintel wall sits above `WINDOW_HEADER`. Door lintels use `translate([0,0,DOOR_HEIGHT])`.

**`scale([sx, -sy, 1])`** — the `apply_svg_scale()` wrapper flips the Y axis (SVG Y grows downward, OpenSCAD Y grows upward) and converts px units to the chosen real-world unit via `SCALE_FACTOR`.

**`color([R, G, B, alpha])`** — purely visual; each module uses a fixed color vector (walls `[0.9,0.9,0.92]`, wood doors `[0.4,0.25,0.1]`, glass `[0.5,0.8,1.0,0.3]`, etc.). Alpha < 1 produces transparency in the OpenSCAD preview.

**`union()`** — the top-level wrapper combines all instantiated elements into a single solid.

## Inkscape extension framework

Reference: [Inkscape Extensions Documentation](https://inkscape.gitlab.io/extensions/documentation/)

The extension is built on `inkex.EffectExtension`. Key framework contracts:

- **`add_arguments(pars)`** — registers CLI flags (via `argparse`) that map 1:1 to the `<param>` elements in the `.inx` file. Values are available at runtime as `self.options.<name>`.
- **`effect()`** — the entry point called by Inkscape after it passes the current SVG document via stdin. `self.svg` is the parsed SVG root; `self.options.ids` is populated when the user runs the extension on a selection.
- **`inkex.Transform`** — an immutable matrix type. Composed with the `@` operator (`parent_transform @ child_transform`). Applied to superpath data via `.transform(matrix)`. The extension chains transforms depth-first through the SVG tree to produce absolute coordinates.
- **`inkex.paths.Path(d).to_superpath()`** — converts an SVG path `d` attribute string into a nested cubic-bezier representation (`[subpath][segment][handle/anchor]`). Used as the starting point for vertex extraction.
- **`inkex.errormsg(str)`** — routes a message to the Inkscape UI error panel. Used here for unmatched category warnings and file I/O errors.
- **INX file** — the `.inx` descriptor must declare every `<param>` that the Python script reads from `self.options`. The `<command reldir="extensions">` path is relative to the Inkscape extensions root directory, which is why the folder itself must be placed there. Validate the INX with `xmllint` and the RELAX NG schema from the Inkscape extensions repository before deployment.
