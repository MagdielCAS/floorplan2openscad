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
make validate-inx  # xmllint --noout on the .inx descriptors and starter template
```

`categories.py`, `geometry.py`, `mesh_validator.py`, `mesh_repair.py`, `openscad_writer.py`, `layer_naming.py`, and `ruler.py` are pure Python and covered by `tests/`. `svg_parser.py`, `floorplan2openscad.py`, `floorplan_add_layer.py`, and `floorplan_add_ruler.py` import `inkex`, which is bundled with Inkscape rather than pip-installable, so `make convert` points `PYTHONPATH` at Inkscape's bundled `inkex` source (`INKEX_PATH`, auto-detected per OS, overridable) and installs `inkex`'s pure-pip runtime deps (numpy, lxml, Pillow, tinycss2, pyserial, cssselect — no Cairo needed) via the `inkex-runtime` dependency group. Reload after editing: in Inkscape, go to Extensions → Reload All Extensions (or restart Inkscape).

Python version is pinned to `3.12.0` via `.tool-versions` (asdf).

Pre-commit hooks (`.pre-commit-config.yaml`) run ruff lint/format, INX well-formedness, and the test suite before each commit — install with `uv run pre-commit install`. CI (`.github/workflows/ci.yml`) runs the same checks plus an end-to-end SVG→OpenSCAD smoke test on Ubuntu with Inkscape installed via apt. Tagging a commit `vX.Y.Z` (matching the `version` in `pyproject.toml`) triggers `.github/workflows/release.yml`, which packages the extension into a `floorplan2openscad/` zip and publishes it as a GitHub release.

## Architecture

The extension is two files:

- **`floorplan2openscad.inx`** — Inkscape extension descriptor XML. Declares the UI parameters (`fname`, `split_by_category`, `base_scale`, `smoothness`) and registers the script under *Extensions → Floorplan → Semantic Floorplan to OpenSCAD*.
- **`floorplan2openscad.py`** — All logic lives here in `FloorplanToOpenSCAD(inkex.EffectExtension)`.

### Pipeline inside `effect()`

1. **SVG traversal** (`recursivelyTraverseSvg`) — walks the SVG node tree, accumulates cumulative `inkex.Transform` matrices, and converts every shape type (path, rect, line, polyline, polygon, ellipse/circle) to a unified path representation.

2. **Bezier flattening** (`getPathVertices` → `subdivideCubicPath`) — recursively subdivides cubic bezier curves until segment deviation is below the `smoothness` threshold, producing a list of `(x, y)` vertex arrays per subpath. Results are stored in `self.paths[node]`.

3. **Hole detection** (`polyInPoly` / `pointInPoly` / `bboxInBBox`) — for each node with multiple subpaths, determines parent/child containment relationships to build OpenSCAD `polygon(points, paths)` with hole indexes.

4. **Category matching** (`get_category_for_node`) — checks the node's `id` and `inkscape:label` attributes (and then walks up to parent groups/layers) against the `CATEGORIES` dict prefix table. Unmatched objects fall back to the generic `wall` module and emit a warning.

5. **OpenSCAD output** (`openscad_writer.write_scad`) — writes a `.scad` file in three sections:
   - Global parametric variables (`WALL_HEIGHT`, `DOOR_HEIGHT`, `WINDOW_SILL`, etc.) expressed as ratios of `BASE_Z_SCALE=1` so the user can tweak one number.
   - Module definitions for all semantic types (wall, wall_outer, wall_inner, wall_balcony, floor_slab, door_wood, door_glass, sliding_glass_door, window_standard, wardrobe), sourced from the `_MODULE_DEFINITIONS` dict.
   - Coordinate arrays and `union() { apply_svg_scale() { ... } }` call block.

   By default this is a single combined file. If the `split_by_category` option is enabled, `effect()` instead groups `items` by `module_name` and calls `write_scad` once per category, passing `module_names={category}` so each file's module-definitions section is trimmed to just that category (via `openscad_writer._modules_text`) — useful for importing categories separately into tools (e.g. FreeCAD) that otherwise treat a `.scad` file's `union()` as one opaque object. Per-category filenames are `{NAME}_{category}.scad`, computed by the pure helpers in `output_paths.py` (`resolve_output_path`, `category_output_path`) — kept inkex-free, like `layer_naming.py` and `ruler.py`, so they're unit-testable without Inkscape installed.

### Semantic categories

The `CATEGORIES` dict (top of the file) maps layer/ID prefix strings → OpenSCAD module names. Adding a new architectural type requires: (1) adding an entry to `CATEGORIES`, and (2) writing the corresponding OpenSCAD module in the string written to the output file inside `effect()`.

### Scale system

The `base_scale` option selects a preset that sets all dimensional constants (wall height, door clearance, sill heights, floor thickness, and a `scale_factor` that converts SVG px to the chosen output unit). All values in the output are written as `{raw_value}/{raw_value_at_3cm} * BASE_Z_SCALE` expressions so the user can rescale the model by changing a single OpenSCAD variable.

Note `scale_factor` is self-canceling across presets: `scale_factor * mm_per_unit` always equals `25.4/96` regardless of which preset is chosen (see `test_scale_factor_is_self_canceling_across_presets` in `tests/test_categories.py`). So `base_scale` never rescales a drawing's real-world XY footprint — it only relabels the output unit and sets the Z-height constants. The real-world plan size is determined by the SVG document's `width`/`height`/`viewBox`, or overridden by the on-canvas scale ruler if one is present (see below) — `FloorplanToOpenSCAD._resolve_scale_config` picks between the two.

### Add Semantic Layer extension

A second, independent extension pair — `floorplan_add_layer.inx` + `floorplan_add_layer.py`, registered under *Extensions → Floorplan → Add Semantic Layer* — creates a new layer pre-named with one of the `CATEGORIES` prefixes, so users pick from a dropdown instead of typing/memorizing a prefix. The category `<option>` values in the `.inx` are hand-authored (INX is static XML) but drift-guarded by `tests/test_floorplan_add_layer_inx.py`, which asserts they exactly match `categories.CATEGORIES` keys. The pure suffix-sanitizing/id-building logic lives in `layer_naming.py` (`sanitize_suffix`, `build_layer_name`, `unique_layer_name`); `floorplan_add_layer.py` is thin `inkex` glue that builds an `inkex.Layer` and inserts it as a top-level layer or as a sublayer of the active layer (`placement` option), relying on `EffectExtension`'s default `run()` to write the mutated document back — unlike `floorplan2openscad.py`, it doesn't write a separate output file.

### Add Scale Ruler extension and ruler-based calibration

A third, independent extension pair — `floorplan_add_ruler.inx` + `floorplan_add_ruler.py`, registered under *Extensions → Floorplan → Add Scale Ruler* — inserts a visual reference bar (a line, end ticks, and a text label like "1 m") sized against the document's actual `width`/`height`/`viewBox`. Unlike a static guide, this bar is a **live calibration control**: the user drags/scales it (or the whole ruler layer) to match a known real-world distance in their drawing, and `floorplan2openscad.py` reads the bar's *current* length back at conversion time to calibrate `SCALE_FACTOR` for the whole model, overriding the fixed-96dpi-derived value the base_scale preset would otherwise produce. Resizing the ruler bar back to its original inserted length reproduces the exact same `SCALE_FACTOR` as if no ruler were present at all — the calibration path is a strict generalization of the default, uncalibrated one.

The pure geometry lives in `ruler.py` (`ruler_geometry`, `mm_to_doc_units`, `RULER_LENGTHS`, `CORNERS`), plus two shared attribute-name constants: `RULER_MARKER_ATTR` (`data-floorplan-ruler`, set on the ruler's `inkex.Layer`) and `RULER_LENGTH_ATTR` (`data-ruler-mm`, set on the bar `PathElement`, holding the real-world mm value fixed at insertion time — this is what stays constant while the bar's on-canvas length changes). `floorplan_add_ruler.py` is thin `inkex` glue: it computes the document's viewBox-to-physical-px ratio (mirroring `FloorplanToOpenSCAD._handle_view_box`), builds separate bar/ticks `PathElement`s and a `TextElement` (label) inside a new `inkex.Layer` tagged with `RULER_MARKER_ATTR`, and inserts it at the document root, visible by default (the whole point is that the user can select and resize it).

Two things make the ruler both editable and safely excluded from conversion regardless of visibility:
- `SVGParser._traverse` (in `svg_parser.py`) skips any node carrying `RULER_MARKER_ATTR` before recursing into it — so the ruler's bar/ticks/label never reach `paths_dict`, never skew the document's bounding-box centroid, never trigger the "falling back to wall" warning, and never appear in geometry/overlap checks. This is a visibility-independent skip, distinct from the pre-existing `display:none`/`visibility:hidden` skip just above it in the same loop.
- `svg_parser.find_ruler_calibration(svg, doc_transform)` finds the bar via a direct `svg.xpath("//*[@data-ruler-mm]")` (bypassing `_traverse` entirely, so it works even while the ruler is hidden), reads its `d` attribute, and measures its length after applying `doc_transform @ node.composed_transform()` — `composed_transform()` is an `inkex.BaseElement` method that composes every ancestor `transform` down to the node, so the measurement is correct whether Inkscape baked the resize into the path's `d` coordinates directly or left it as a `transform` attribute (both are common depending on the "store transformation" preference).

`FloorplanToOpenSCAD._resolve_scale_config` (in `floorplan2openscad.py`) ties it together: `calibrated_scale_factor = real_world_mm / (raw_length * scale_config["mm_per_unit"])`, where `mm_per_unit` is a field on each `SCALE_PRESETS` entry (30/10/1/1000 for 3cm/1cm/1mm/1m) added specifically to make this calibration formula explicit rather than back-deriving it from `wall_height`. If multiple ruler bars exist, the first (in document order) is used and a warning is emitted for the rest.

The `<option>` values in `floorplan_add_ruler.inx` (`length`, `corner`) are drift-guarded by `tests/test_floorplan_add_ruler_inx.py` against `ruler.RULER_LENGTHS` / `ruler.CORNERS`.

### Starter template

`templates/floorplan-starter.svg` ships one empty, correctly-named layer per `CATEGORIES` prefix. Users copy it into Inkscape's templates directory (path documented in README) to make it available under *File → New From Template*. `tests/test_templates.py` parses it and asserts every layer resolves to a known category via `categories.match_category`, with all nine categories represented exactly once.

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
