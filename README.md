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

---

## Base Scale Configuration

The dropdown in the Inkscape extension interface adjusts the unit scale and parameters:

- **3 cm** (Architectural 1:100 draft): 1 unit = 3cm. Ceiling height is `80.0` units.
- **1 cm**: 1 unit = 1cm. Ceiling height is `240.0` units.
- **1 mm**: 1 unit = 1mm. Ceiling height is `2400.0` units.
- **1 m**: 1 unit = 1m. Ceiling height is `2.4` units.

---

## Installation

1. Clone or download this repository.
2. Move the `floorplan2openscad` folder into your Inkscape extensions folder:
   - **Linux**: `~/.config/inkscape/extensions/`
   - **macOS**: `~/Library/Application Support/org.inkscape.Inkscape/config/inkscape/extensions/`
   - **Windows**: `%APPDATA%\inkscape\extensions\`
3. Restart Inkscape. The extension will appear under **Extensions → Generate from Path → Semantic Floorplan to OpenSCAD**.

---

## How to Use

1. Draw your floor plan elements in Inkscape.
2. Group or layer your shapes and label the layers using one of the prefixes above (e.g., a layer named `wall_outer_ground`).
3. Convert all shapes to paths: **Path → Object to Path** (Ctrl+Shift+C).
4. Run the extension: Go to **Extensions → Generate from Path → Semantic Floorplan to OpenSCAD**.
5. Select your output `.scad` filename and base scale, then click **Apply**.
6. Open the generated file in **OpenSCAD** to customize, preview, and export your 3D architectural model.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
