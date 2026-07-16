# floorplan2openscad

An Inkscape extension that converts 2D architectural SVG floor plans into fully parametric 3D OpenSCAD models.

Unlike general path-to-OpenSCAD converters, this extension is **semantic**. It reads your layer names (or individual object IDs/prefixes) in Inkscape, extracts the coordinates, and wraps them in custom procedural OpenSCAD modules representing architectural features.

---

## Features

- **Semantic Prefix Identification**: Automatically matches paths by their layer name or object ID prefix and maps them to specialized OpenSCAD modules.
- **Parametric Controls**: Custom dimensions (wall height, door clearance, window sill/header heights, slab thickness, balcony wall heights, and frame widths) are exposed as global variables at the top of the `.scad` file.
- **Base Scale Conversions**: Tweak the output base scale dropdown in Inkscape to match your drafting units (e.g. 1 unit = 3cm, 1cm, 1mm, or 1m).
- **Hole and Subpath Support**: Correctly renders nested paths (such as walls with inner cutouts or donut slabs) as OpenSCAD polygons with hole indexes.
- **Comprehensive Transform Support**: Parses paths, rectangles, circles, ellipses, lines, polylines, and polygons, automatically applying cumulative group transforms.
- **On-Canvas Scale Calibration**: A helper extension drops a resizable "1 m" reference bar into a corner of the canvas. Drag it to match a known real-world distance in your drawing, and the conversion automatically calibrates the whole floor plan's scale from the bar's resulting length — instead of relying on the fixed 96dpi assumption. The ruler itself is never rendered in the `.scad` output.

---

## Semantic Categories & Prefix Rules

Name your Inkscape layers (or individual object IDs) with one of the following prefixes (case-insensitive):

| Prefix | Element Type | OpenSCAD Module | Description |
|---|---|---|---|
| `floor_` | Floor Slabs | `floor_slab(points)` | Slab extruded downwards below Z=0 |
| `wall_outer_` | Exterior Walls | `wall_outer(points)` | Full-height exterior structural walls |
| `wall_inner_` | Interior Walls | `wall_inner(points)` | Full-height interior walls |
| `wall_balcony_` | Balcony Walls | `wall_balcony(points)` | Half-height masonry walls for balconies |
| `door_wood_` | Wooden Doors | `door_wood(points)` | Standard door (wood leaf + lintel above) |
| `door_glass_` | Glass Doors | `door_glass(points)` | Wood frame + translucent glass panel |
| `sliding_door_` | Sliding Doors | `sliding_glass_door(points)` | Minimal dark frames + large sliding glass panes |
| `window_standard_` | Standard Windows | `window_standard(points)` | Wall sill + frame + glass pane + lintel |
| `wardrobe_` | Built-in Closets | `wardrobe(points)` | Floor-to-ceiling closet block |

> **Warning:** If an object or layer does not match any known prefix, it falls back to a standard `wall` extrusion, and a warning is printed in the Inkscape interface.

This table, the **Add Semantic Layer** extension's dropdown, and the starter template below are all derived from the same `CATEGORIES` mapping in `categories.py`, and the latter two are checked in CI against that mapping — so there's nothing to keep in sync by hand beyond this table itself.

---

## Base Scale Configuration

The dropdown in the Inkscape extension interface adjusts the unit scale and parameters:

- **3 cm** (Architectural 1:100 draft): 1 unit = 3cm. Ceiling height is `80.0` units.
- **1 cm**: 1 unit = 1cm. Ceiling height is `240.0` units.
- **1 mm**: 1 unit = 1mm. Ceiling height is `2400.0` units.
- **1 m**: 1 unit = 1m. Ceiling height is `2.4` units.

> **Note:** This dropdown only relabels the output unit and sets the ceiling/door/window Z-height constants above — it does not rescale your drawing's XY footprint. The real-world plan size comes from your SVG document's actual width/height/viewBox, or from the on-canvas scale ruler if one is present (see below).

---

## Scale Ruler & Calibration

Run **Extensions → Floorplan → Add Scale Ruler** to drop a bar (with end ticks and a "1 m"-style label) into a corner of the canvas, sized against your document's actual width/height/viewBox. Unlike the earlier one-shot guide, this bar is a **live calibration control**:

1. Select the ruler's bar (or drag a box around the whole ruler — bar, ticks, and label together) and resize it with Inkscape's selection tool to match a real-world distance you can see in your drawing (e.g. stretch/shrink it to line up against a wall you know is 4m long).
2. Run **Semantic Floorplan to OpenSCAD** as usual. The conversion looks for the ruler bar anywhere in the document (hidden or visible), measures its current length, and uses that to calibrate `SCALE_FACTOR` for the whole model — overriding the fixed 96dpi assumption the base scale preset would otherwise use.
3. The ruler itself is never written to the `.scad` output, regardless of whether it's visible or hidden.
4. If you don't add a ruler, conversion behaves exactly as before: real-world size comes from the document's width/height/viewBox.

If you resize the *whole* ruler (bar + ticks + label) proportionally, everything stays visually aligned. If you only stretch the bar itself, the ticks/label won't follow — that's fine, since only the bar's endpoints are used for calibration.

---

## Installation

1. Clone or download this repository.
2. Move the `floorplan2openscad` folder into your Inkscape extensions folder:
   - **Linux**: `~/.config/inkscape/extensions/`
   - **macOS**: `~/Library/Application Support/org.inkscape.Inkscape/config/inkscape/extensions/`
   - **Windows**: `%APPDATA%\inkscape\extensions\`
3. Restart Inkscape. The extension will appear under **Extensions → Generate from Path → Semantic Floorplan to OpenSCAD**, with two helper extensions under **Extensions → Floorplan**: **Add Semantic Layer** and **Add Scale Ruler**.

### Installing the starter template (optional)

To start new floor plans with all nine category layers already created, copy `templates/floorplan-starter.svg` into Inkscape's templates directory:

- **Linux**: `~/.config/inkscape/templates/`
- **macOS**: `~/Library/Application Support/org.inkscape.Inkscape/config/inkscape/templates/`
- **Windows**: `%APPDATA%\inkscape\templates\`

Restart Inkscape; the template then appears under **File → New From Template**. Delete any layers you don't need before drawing.

---

## How to Use

1. Draw your floor plan elements in Inkscape.
2. Group or layer your shapes and label the layers using one of the prefixes above (e.g., a layer named `wall_outer_ground`). Instead of typing a prefix by hand, you can run **Extensions → Floorplan → Add Semantic Layer**, pick a category from the dropdown, and give it a name suffix — it creates the correctly-prefixed layer for you (as a top-level layer or a sublayer of the active layer). Starting from the starter template (see above) skips this step entirely for the common categories.
3. Not sure if your drawing is the right real-world size? Run **Extensions → Floorplan → Add Scale Ruler** to drop a resizable "1 m" (or 10cm/50cm/2m/5m) reference bar into a corner of the canvas. Drag it to match a known distance in your drawing — see [Scale Ruler & Calibration](#scale-ruler--calibration) above — and the conversion will use it to calibrate the model's scale. It's excluded from the `.scad` output either way.
4. Convert all shapes to paths: **Path → Object to Path** (Ctrl+Shift+C).
5. Run the extension: Go to **Extensions → Generate from Path → Semantic Floorplan to OpenSCAD**.
6. Select your output `.scad` filename and base scale, then click **Apply**.
7. Open the generated file in **OpenSCAD** to customize, preview, and export your 3D architectural model.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
