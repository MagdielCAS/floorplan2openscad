# floorplan2openscad

> Convert SVG floor plans into 3D OpenSCAD models using prefixed layer names to identify architectural elements such as walls, doors, windows, stairs, and more.

---

## Overview

**floorplan2openscad** is a tool that takes an SVG floor plan drawn in [Inkscape](https://inkscape.org/) and converts it into a parametric [OpenSCAD](https://openscad.org/) 3D model.  It is heavily inspired by [inkscape-paths2openscad](https://github.com/fablabnbg/inkscape-paths2openscad) but is purpose-built for architectural floor plans.  Instead of treating every path identically, it reads **prefixed layer names** in your SVG to understand what each shape represents — walls, doors, windows, stairs, columns, and more — and generates a properly structured, ready-to-render `.scad` file.

---

## Features

- **Layer-driven architecture** — name your Inkscape layers with a recognised prefix and the tool will automatically assign the correct 3D behaviour to every path in that layer.
- **Walls** — closed paths are extruded to a configurable wall height.
- **Doors** — arcs and rectangles in a door layer are turned into door-shaped cutouts and optionally a swinging door leaf.
- **Windows** — paths in a window layer produce horizontal slot cutouts at the correct sill and head heights.
- **Stairs** — stepped extrusions follow a stair-tread path.
- **Columns / pillars** — circular or rectangular shapes are extruded as solid columns.
- **Furniture (optional)** — simple footprint shapes can be extruded at a low height for visualisation.
- **Parametric output** — wall height, slab thickness, door height, window sill/head heights and more are exposed as OpenSCAD variables at the top of the output file so you can tweak them without re-running the converter.
- **Clean, readable `.scad`** — each layer group becomes a named OpenSCAD `module`, making it easy to include only the parts you need.

---

## Layer Naming Conventions

Rename your Inkscape layers so that their names start with one of the following prefixes (case-insensitive).  Everything after the prefix is treated as a free-form label.

| Prefix | Element | Default behaviour |
|---|---|---|
| `wall:` | Load-bearing or partition wall | Extruded to `wall_height` |
| `door:` | Door opening + leaf | Cutout in the wall layer + optional swinging leaf |
| `window:` | Window opening | Horizontal slot cut between `window_sill` and `window_head` heights |
| `stair:` | Stair flight | Stepped extrusion following the path direction |
| `column:` | Column / pillar | Solid extrusion to `column_height` |
| `slab:` | Floor or ceiling slab | Extruded to `slab_thickness` (placed at z = 0 or z = `wall_height`) |
| `furniture:` | Furniture footprint | Flat extrusion to `furniture_height` for visualisation |
| `ignore:` | Annotation / dimension | Skipped entirely |

> **Tip:** you can have multiple layers with the same prefix, e.g. `wall: exterior` and `wall: interior`.  All paths in both layers will be treated as walls.

### Example layer setup in Inkscape

```
wall: exterior
wall: interior
door: ground floor
window: ground floor
stair: main staircase
column: structural
slab: ground floor
furniture: kitchen (optional)
ignore: dimensions
```

---

## Requirements

- [Python](https://www.python.org/) 3.9 or newer
- [Inkscape](https://inkscape.org/) (for drawing / exporting the floor plan SVG; not required at conversion time)
- [OpenSCAD](https://openscad.org/) (to render the generated `.scad` file)
- Python dependencies listed in `requirements.txt`

---

## Installation

```bash
git clone https://github.com/MagdielCAS/floorplan2openscad.git
cd floorplan2openscad
pip install -r requirements.txt
```

---

## Quick Start

1. **Draw your floor plan** in Inkscape.
2. **Name your layers** using the prefixes described above (e.g. `wall: exterior`).
3. **Save as Plain SVG** (`File → Save a copy → Plain SVG`).
4. **Run the converter:**

   ```bash
   python floorplan2openscad.py floorplan.svg -o floorplan.scad
   ```

5. **Open the result** in OpenSCAD:

   ```bash
   openscad floorplan.scad
   ```

---

## Command-Line Options

```
usage: floorplan2openscad.py [-h] [-o OUTPUT] [--wall-height WALL_HEIGHT]
                             [--slab-thickness SLAB_THICKNESS]
                             [--door-height DOOR_HEIGHT]
                             [--window-sill WINDOW_SILL]
                             [--window-head WINDOW_HEAD]
                             [--column-height COLUMN_HEIGHT]
                             [--furniture-height FURNITURE_HEIGHT]
                             [--scale SCALE] [--no-furniture]
                             [--list-layers]
                             input

positional arguments:
  input                 Path to the input SVG floor plan

options:
  -h, --help            Show this help message and exit
  -o OUTPUT             Output .scad file (default: <input>.scad)
  --wall-height         Wall height in mm (default: 2700)
  --slab-thickness      Floor/ceiling slab thickness in mm (default: 200)
  --door-height         Door opening height in mm (default: 2100)
  --window-sill         Window sill height in mm (default: 900)
  --window-head         Window head height in mm (default: 2100)
  --column-height       Column height in mm (default: 2700)
  --furniture-height    Furniture extrusion height in mm (default: 50)
  --scale               Scale factor applied to SVG coordinates (default: 1.0)
  --no-furniture        Skip furniture layers
  --list-layers         Print detected layers and their assigned types, then exit
```

---

## Output Structure

The generated `.scad` file is organised as follows:

```openscad
// floorplan2openscad — generated from floorplan.svg
// https://github.com/MagdielCAS/floorplan2openscad

/* --- Parameters --- */
wall_height      = 2700;
slab_thickness   = 200;
door_height      = 2100;
window_sill      =  900;
window_head      = 2100;
column_height    = 2700;
furniture_height =   50;

/* --- Modules --- */
module walls()      { ... }
module doors()      { ... }
module windows()    { ... }
module stairs()     { ... }
module columns()    { ... }
module slabs()      { ... }
module furniture()  { ... }

/* --- Assembly --- */
walls();
difference() {
    walls();
    doors();
    windows();
}
stairs();
columns();
slabs();
furniture();
```

---

## How It Works

1. **Parse SVG** — the tool uses Python's `xml.etree.ElementTree` to walk the SVG document tree, collecting all `<g>` (group/layer) elements and their children.
2. **Identify layers** — each layer's `inkscape:label` attribute is matched against the prefix table.
3. **Extract paths** — SVG `<path>`, `<rect>`, `<circle>`, and `<ellipse>` elements are converted to 2D polygon coordinates using a path-parsing library.
4. **Apply transforms** — any SVG `transform` attributes (translate, rotate, scale, matrix) are applied so coordinates are in a consistent world space.
5. **Generate OpenSCAD** — for each layer type the appropriate OpenSCAD primitive (`linear_extrude`, `difference`, etc.) is written out together with the 2D polygon data.

---

## Contributing

Contributions are welcome!  Please open an issue or pull request on [GitHub](https://github.com/MagdielCAS/floorplan2openscad).

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/my-new-feature`
3. Commit your changes: `git commit -m "Add my new feature"`
4. Push to the branch: `git push origin feature/my-new-feature`
5. Open a pull request.

---

## Acknowledgements

- [inkscape-paths2openscad](https://github.com/fablabnbg/inkscape-paths2openscad) by [FabLab Nürnberg](https://fablab.fau.de/) — the original inspiration for converting SVG paths to OpenSCAD.
- [Inkscape](https://inkscape.org/) — open-source vector graphics editor used for drawing floor plans.
- [OpenSCAD](https://openscad.org/) — the scriptable 3D CAD modeller used as the output target.

---

## License

This project is released under the [MIT License](LICENSE).
