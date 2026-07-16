"""OpenSCAD file generation. No inkex dependency."""

import time

from geometry import format_paths, format_points, poly_in_poly

_PARAMETERS_TEMPLATE = """\
// Generated from SVG floor plan "{basename}.svg" at {timestamp}
// Base Z-Scale: {desc}

BASE_Z_SCALE = 1;
WALL_HEIGHT      = {wall_height:.2f}/80 * BASE_Z_SCALE;  // Standard ceiling height (2.40m)
DOOR_HEIGHT      = {door_height:.2f}/80 * BASE_Z_SCALE;  // Standard door clearance (2.00m)
WINDOW_HEADER    = {window_header:.2f}/80 * BASE_Z_SCALE;  // Top of the window frame (2.10m)
WINDOW_SILL      = {window_sill:.2f}/80 * BASE_Z_SCALE;  // Standard window sill height (0.90m)
FLOOR_THICKNESS  = {floor_thickness:.2f}/80 * BASE_Z_SCALE;  // Slab thickness below Z=0 (0.15m)
BALCONY_HEIGHT   = {balcony_height:.2f}/80 * BASE_Z_SCALE;  // Height for balcony/varanda walls (1.10m)
FRAME_WIDTH      = {frame_width:.2f}/80 * BASE_Z_SCALE;  // Width of door and window frames

RENDER_DOORS     = true;
RENDER_WINDOWS   = true;
RENDER_FLOORS    = true;
RENDER_FURNITURE = true;

SCALE_FACTOR     = {scale_factor:.8f};
module apply_svg_scale() {{
    scale([SCALE_FACTOR, -SCALE_FACTOR, 1]) children(); // 96 DPI and unit adjustment
}}

"""

_MODULES = """\
/* --- Semantic Modules --- */

module wall(points, paths=[], h=WALL_HEIGHT) {
    color([0.9, 0.9, 0.92])
    linear_extrude(height=h, convexity=10) {
        if (len(paths) > 0) { polygon(points, paths); } else { polygon(points); }
    }
}

module wall_outer(points, paths=[], h=WALL_HEIGHT) {
    color([0.9, 0.9, 0.92])
    linear_extrude(height=h, convexity=10) {
        if (len(paths) > 0) { polygon(points, paths); } else { polygon(points); }
    }
}

module wall_inner(points, paths=[], h=WALL_HEIGHT) {
    color([0.9, 0.9, 0.92])
    linear_extrude(height=h, convexity=10) {
        if (len(paths) > 0) { polygon(points, paths); } else { polygon(points); }
    }
}

module wall_balcony(points, paths=[], h=BALCONY_HEIGHT) {
    color([0.9, 0.9, 0.92])
    linear_extrude(height=h, convexity=10) {
        if (len(paths) > 0) { polygon(points, paths); } else { polygon(points); }
    }
}

module floor_slab(points, paths=[], h=FLOOR_THICKNESS) {
    if (RENDER_FLOORS) {
        color([0.85, 0.8, 0.75])
        translate([0, 0, -h])
        linear_extrude(height=h, convexity=10) {
            if (len(paths) > 0) { polygon(points, paths); } else { polygon(points); }
        }
    }
}

module door_wood(points, paths=[]) {
    color([0.9, 0.9, 0.92])
    translate([0, 0, DOOR_HEIGHT])
    linear_extrude(height=WALL_HEIGHT - DOOR_HEIGHT, convexity=10) {
        if (len(paths) > 0) { polygon(points, paths); } else { polygon(points); }
    }
    if (RENDER_DOORS) {
        color([0.4, 0.25, 0.1])
        linear_extrude(height=DOOR_HEIGHT, convexity=10) {
            if (len(paths) > 0) { polygon(points, paths); } else { polygon(points); }
        }
    }
}

module door_glass(points, paths=[]) {
    color([0.9, 0.9, 0.92])
    translate([0, 0, DOOR_HEIGHT])
    linear_extrude(height=WALL_HEIGHT - DOOR_HEIGHT, convexity=10) {
        if (len(paths) > 0) { polygon(points, paths); } else { polygon(points); }
    }
    if (RENDER_DOORS) {
        color([0.4, 0.25, 0.1])
        linear_extrude(height=DOOR_HEIGHT, convexity=10) {
            difference() {
                if (len(paths) > 0) { polygon(points, paths); } else { polygon(points); }
                offset(delta = -FRAME_WIDTH) {
                    if (len(paths) > 0) { polygon(points, paths); } else { polygon(points); }
                }
            }
        }
        color([0.5, 0.8, 1.0, 0.3])
        linear_extrude(height=DOOR_HEIGHT, convexity=10) {
            offset(delta = -FRAME_WIDTH) {
                if (len(paths) > 0) { polygon(points, paths); } else { polygon(points); }
            }
        }
    }
}

module sliding_glass_door(points, paths=[]) {
    color([0.9, 0.9, 0.92])
    translate([0, 0, DOOR_HEIGHT])
    linear_extrude(height=WALL_HEIGHT - DOOR_HEIGHT, convexity=10) {
        if (len(paths) > 0) { polygon(points, paths); } else { polygon(points); }
    }
    if (RENDER_DOORS) {
        color("darkslategrey")
        linear_extrude(height=DOOR_HEIGHT, convexity=10) {
            difference() {
                if (len(paths) > 0) { polygon(points, paths); } else { polygon(points); }
                offset(delta = -FRAME_WIDTH / 2.0) {
                    if (len(paths) > 0) { polygon(points, paths); } else { polygon(points); }
                }
            }
        }
        color([0.5, 0.8, 1.0, 0.3])
        linear_extrude(height=DOOR_HEIGHT, convexity=10) {
            offset(delta = -FRAME_WIDTH / 2.0) {
                if (len(paths) > 0) { polygon(points, paths); } else { polygon(points); }
            }
        }
    }
}

module window_standard(points, paths=[]) {
    color([0.9, 0.9, 0.92])
    linear_extrude(height=WINDOW_SILL, convexity=10) {
        if (len(paths) > 0) { polygon(points, paths); } else { polygon(points); }
    }
    color([0.9, 0.9, 0.92])
    translate([0, 0, WINDOW_HEADER])
    linear_extrude(height=WALL_HEIGHT - WINDOW_HEADER, convexity=10) {
        if (len(paths) > 0) { polygon(points, paths); } else { polygon(points); }
    }
    if (RENDER_WINDOWS) {
        color([0.75, 0.78, 0.80])
        translate([0, 0, WINDOW_SILL])
        linear_extrude(height=WINDOW_HEADER - WINDOW_SILL, convexity=10) {
            difference() {
                if (len(paths) > 0) { polygon(points, paths); } else { polygon(points); }
                offset(delta = -FRAME_WIDTH) {
                    if (len(paths) > 0) { polygon(points, paths); } else { polygon(points); }
                }
            }
        }
        color([0.5, 0.8, 1.0, 0.3])
        translate([0, 0, WINDOW_SILL])
        linear_extrude(height=WINDOW_HEADER - WINDOW_SILL, convexity=10) {
            if (len(paths) > 0) { polygon(points, paths); } else { polygon(points); }
        }
    }
}

module wardrobe(points, paths=[]) {
    if (RENDER_FURNITURE) {
        color("wheat")
        linear_extrude(height=WALL_HEIGHT, convexity=10) {
            if (len(paths) > 0) { polygon(points, paths); } else { polygon(points); }
        }
    }
}

"""


def build_items(paths_with_modules, cx, cy):
    """Resolve holes and center coordinates for a list of (module_name, subpath_list) pairs.

    Returns a list of dicts with keys: module_name, var_name, points, polypaths.
    """
    counts = {}
    items = []

    for module_name, path in paths_with_modules:
        if not path:
            continue

        counts[module_name] = counts.get(module_name, 0) + 1
        idx = counts[module_name]
        var_base = f"path_{module_name}_{idx}"

        n = len(path)
        contains = [[] for _ in range(n)]
        contained_by = [[] for _ in range(n)]

        for i in range(n):
            for j in range(i + 1, n):
                if poly_in_poly(path[j][0], path[j][1], path[i][0], path[i][1]):
                    contains[i].append(j)
                    contained_by[j].append(i)
                elif poly_in_poly(path[i][0], path[i][1], path[j][0], path[j][1]):
                    contains[j].append(i)
                    contained_by[i].append(j)

        for i in range(n):
            if contained_by[i]:
                continue
            subpath = path[i][0]
            if len(subpath) < 3:
                continue

            polypoints = [[pt[0] - cx, pt[1] - cy] for pt in subpath]
            polypaths = []

            if contains[i]:
                polypaths.append(list(range(len(subpath))))
                curr_idx = len(subpath)
                for j in contains[i]:
                    inner_subpath = path[j][0]
                    inner_indices = []
                    for pt in inner_subpath:
                        polypoints.append([pt[0] - cx, pt[1] - cy])
                        inner_indices.append(curr_idx)
                        curr_idx += 1
                    polypaths.append(inner_indices)

            suffix = f"_{i}" if n > 1 else ""
            items.append(
                {
                    "module_name": module_name,
                    "var_name": f"{var_base}{suffix}",
                    "points": polypoints,
                    "polypaths": polypaths,
                }
            )

    return items


def write_scad(f, basename, items, scale_config):
    """Write a complete .scad file to the open file object f."""
    f.write(
        _PARAMETERS_TEMPLATE.format(
            basename=basename,
            timestamp=time.ctime(),
            **scale_config,
        )
    )
    f.write(_MODULES)
    f.write("/* --- Data Extraction & Coordinates --- */\n\n")
    for item in items:
        f.write(f"{item['var_name']}_points = {format_points(item['points'])};\n")
        if item["polypaths"]:
            f.write(f"{item['var_name']}_paths = {format_paths(item['polypaths'])};\n")
    f.write("\n/* --- Execution Set --- */\n\n")
    f.write("union() {\n    apply_svg_scale() {\n")
    for item in items:
        if item["polypaths"]:
            f.write(f"        {item['module_name']}({item['var_name']}_points, {item['var_name']}_paths);\n")
        else:
            f.write(f"        {item['module_name']}({item['var_name']}_points);\n")
    f.write("    }\n}\n")
