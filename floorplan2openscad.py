#!/usr/bin/env python3
#
# floorplan2openscad.py
#
# Inkscape extension to convert SVG architectural plans into parametric 3D OpenSCAD models.
# Based on inkscape-paths2openscad with rewritten semantic architecture and modules.
#

import os
import sys
import re
import time
import string
import inkex
from inkex.bezier import beziersplitatt, maxdist

# Definitions of categories and their respective OpenSCAD modules
CATEGORIES = {
    'floor_': 'floor_slab',
    'wall_outer_': 'wall_outer',
    'wall_inner_': 'wall_inner',
    'wall_balcony_': 'wall_balcony',
    'door_wood_': 'door_wood',
    'door_glass_': 'door_glass',
    'sliding_door_': 'sliding_glass_door',
    'window_standard_': 'window_standard',
    'wardrobe_': 'wardrobe',
}

def parseLengthWithUnits(str_val, default_unit='px'):
    u = default_unit
    s = str_val.strip()
    if s[-2:] in ('px', 'pt', 'pc', 'mm', 'cm', 'in', 'ft'):
        u = s[-2:]
        s = s[:-2]
    elif s[-1:] in ('m', '%'):
        u = s[-1:]
        s = s[:-1]

    try:
        v = float(s)
    except:
        return None, None

    return v, u

def pointInBBox(pt, bbox):
    if (pt[0] < bbox[0]) or (pt[0] > bbox[1]) or (pt[1] < bbox[2]) or (pt[1] > bbox[3]):
        return False
    return True

def bboxInBBox(bbox1, bbox2):
    if (bbox1[0] < bbox2[0]) or (bbox1[1] > bbox2[1]) or (bbox1[2] < bbox2[2]) or (bbox1[3] > bbox2[3]):
        return False
    return True

def pointInPoly(p, poly, bbox=None):
    if (p is None) or (poly is None):
        return False

    if bbox is not None:
        if not pointInBBox(p, bbox):
            return False

    if p in poly:
        return True

    x = p[0]
    y = p[1]
    p1 = poly[0]
    p2 = poly[1]
    for i in range(len(poly)):
        if i != 0:
            p1 = poly[i - 1]
            p2 = poly[i]
        if (y == p1[1]) and (p1[1] == p2[1]) and (x > min(p1[0], p2[0])) and (x < max(p1[0], p2[0])):
            return True

    n = len(poly)
    inside = False

    p1_x, p1_y = poly[0]
    for i in range(n + 1):
        p2_x, p2_y = poly[i % n]
        if y > min(p1_y, p2_y):
            if y <= max(p1_y, p2_y):
                if x <= max(p1_x, p2_x):
                    if p1_y != p2_y:
                        intersect = p1_x + (y - p1_y) * (p2_x - p1_x) / (p2_y - p1_y)
                        if x <= intersect:
                            inside = not inside
                    else:
                        inside = not inside
        p1_x, p1_y = p2_x, p2_y

    return inside

def polyInPoly(poly1, bbox1, poly2, bbox2):
    if (bbox1 is not None) and (bbox2 is not None):
        if not bboxInBBox(bbox1, bbox2):
            return False

    for p in poly1:
        if not pointInPoly(p, poly2, bbox2):
            return False

    return True

def subdivideCubicPath(sp, flat, i=1):
    while True:
        while True:
            if i >= len(sp):
                return

            p0 = sp[i - 1][1]
            p1 = sp[i - 1][2]
            p2 = sp[i][0]
            p3 = sp[i][1]

            b = (p0, p1, p2, p3)

            if maxdist(b) > flat:
                break

            i += 1

        one, two = beziersplitatt(b, 0.5)
        sp[i - 1][2] = one[1]
        sp[i][0] = two[2]
        p = [one[2], one[3], two[1]]
        sp[i:1] = [p]

def format_points(points):
    return "[" + ",".join([f"[{pt[0]:.4f},{pt[1]:.4f}]" for pt in points]) + "]"

def format_paths(paths):
    return "[" + ",".join(["[" + ",".join([str(idx) for idx in path]) + "]" for path in paths]) + "]"


class FloorplanToOpenSCAD(inkex.EffectExtension):
    def __init__(self):
        super().__init__()
        self.dpi = 96.0
        self.cx = 0.0
        self.cy = 0.0
        self.xmin, self.xmax = (1.0E70, -1.0E70)
        self.ymin, self.ymax = (1.0E70, -1.0E70)
        self.paths = {}
        self.basename = "floorplan"
        self.warnings_printed = set()

    def add_arguments(self, pars):
        pars.add_argument(
            '--fname', dest='fname', type=str, default='{NAME}.scad',
            help='OpenSCAD output file derived from the svg file name.')
        pars.add_argument(
            '--base_scale', dest='base_scale', type=str, default='3cm',
            help='Scale factor (3cm, 1cm, 1mm, 1m).')
        pars.add_argument(
            '--smoothness', dest='smoothness', type=type(0.2), default=0.2,
            help='Curve smoothing (less for more)')

    def getLength(self, name, default):
        str_val = self.svg.get(name)
        if str_val:
            return self.LengthWithUnit(str_val)
        return float(default)

    def LengthWithUnit(self, strn, default_unit='px'):
        v, u = parseLengthWithUnits(strn, default_unit)
        if v is None:
            return None
        elif u == 'mm':
            return float(v) * (self.dpi / 25.4)
        elif u == 'cm':
            return float(v) * (self.dpi * 10.0 / 25.4)
        elif u == 'm':
            return float(v) * (self.dpi * 1000.0 / 25.4)
        elif u == 'in':
            return float(v) * self.dpi
        elif u == 'ft':
            return float(v) * 12.0 * self.dpi
        elif u == 'pt':
            return float(v) * (self.dpi / 72.0)
        elif u == 'pc':
            return float(v) * (self.dpi / 6.0)
        elif u == 'px':
            return float(v)
        return None

    def getDocProps(self):
        inkscape_version = self.svg.get("{http://www.inkscape.org/namespaces/inkscape}version")
        sodipodi_docname = self.svg.get("{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}docname")
        if sodipodi_docname is None:
            sodipodi_docname = "floorplan"
        self.basename = re.sub(r"\.SVG", "", sodipodi_docname, flags=re.I)
        self.basename = os.path.splitext(os.path.basename(self.basename))[0]

        if inkscape_version:
            m = re.match(r"(\d+)\.(\d+)", inkscape_version)
            if m:
                if int(m.group(1)) > 0 or int(m.group(2)) > 91:
                    self.dpi = 96.0

        self.docHeight = self.getLength('height', 100)
        self.docWidth = self.getLength('width', 100)
        return (self.docHeight is not None) and (self.docWidth is not None)

    def handleViewBox(self):
        if self.getDocProps():
            viewbox = self.svg.get('viewBox')
            if viewbox:
                vinfo = viewbox.strip().replace(',', ' ').split()
                if len(vinfo) >= 4 and float(vinfo[2]) != 0 and float(vinfo[3]) != 0:
                    sx = self.docWidth  / float(vinfo[2])
                    sy = self.docHeight / float(vinfo[3])
                    self.docTransform = inkex.Transform('scale(%f,%f)' % (sx, sy))
                else:
                    self.docTransform = inkex.Transform()
            else:
                self.docTransform = inkex.Transform()

    def getPathVertices(self, path, node=None, transform=None):
        if (not path) or (len(path) == 0):
            return None

        try:
            p = inkex.paths.Path(path).to_superpath()
        except:
            return None
        if (not p) or (len(p) == 0):
            return None

        if transform:
            p = p.transform(transform)

        subpath_list = []
        subpath_vertices = []

        for sp in p:
            if len(subpath_vertices):
                subpath_list.append([subpath_vertices, [sp_xmin, sp_xmax, sp_ymin, sp_ymax]])

            subpath_vertices = []
            subdivideCubicPath(sp, float(self.options.smoothness))

            first_point = sp[0][1]
            subpath_vertices.append(first_point)
            sp_xmin = first_point[0]
            sp_xmax = first_point[0]
            sp_ymin = first_point[1]
            sp_ymax = first_point[1]

            n = len(sp)
            for csp in sp[1:n]:
                pt = csp[1]
                subpath_vertices.append(pt)

                if pt[0] < sp_xmin:
                    sp_xmin = pt[0]
                elif pt[0] > sp_xmax:
                    sp_xmax = pt[0]
                if pt[1] < sp_ymin:
                    sp_ymin = pt[1]
                elif pt[1] > sp_ymax:
                    sp_ymax = pt[1]

            if sp_xmin < self.xmin:
                self.xmin = sp_xmin
            if sp_xmax > self.xmax:
                self.xmax = sp_xmax
            if sp_ymin < self.ymin:
                self.ymin = sp_ymin
            if sp_ymax > self.ymax:
                self.ymax = sp_ymax

        if len(subpath_vertices):
            subpath_list.append([subpath_vertices, [sp_xmin, sp_xmax, sp_ymin, sp_ymax]])

        if len(subpath_list) > 0:
            self.paths[node] = subpath_list

    def recursivelyTraverseSvg(self, aNodeList, matCurrent=None, parent_visibility='visible'):
        if matCurrent is None:
            matCurrent = inkex.Transform()

        for node in aNodeList:
            v = node.get('visibility', parent_visibility)
            if v == 'inherit':
                v = parent_visibility
            if v == 'hidden' or v == 'collapse':
                continue

            s = node.get('style', '')
            if s == 'display:none':
                continue

            matNew = matCurrent @ inkex.Transform(node.get("transform"))

            if node.tag in (inkex.addNS('g', 'svg'), 'g'):
                self.recursivelyTraverseSvg(node, matNew, v)

            elif node.tag in (inkex.addNS('use', 'svg'), 'use'):
                refid = node.get(inkex.addNS('href', 'xlink'))
                if not refid:
                    continue
                path = '//*[@id="%s"]' % refid[1:]
                refnode = node.xpath(path)
                if refnode:
                    x = float(node.get('x', '0'))
                    y = float(node.get('y', '0'))
                    if (x != 0) or (y != 0):
                        matNew2 = matNew @ inkex.Transform('translate(%f,%f)' % (x, y))
                    else:
                        matNew2 = matNew
                    v = node.get('visibility', v)
                    self.recursivelyTraverseSvg(refnode, matNew2, v)

            elif node.tag == inkex.addNS('path', 'svg'):
                path_data = node.get('d')
                if path_data:
                    self.getPathVertices(path_data, node, matNew)

            elif node.tag in (inkex.addNS('rect', 'svg'), 'rect'):
                x = float(node.get('x', '0'))
                y = float(node.get('y', '0'))
                w = float(node.get('width', '0'))
                h = float(node.get('height', '0'))
                a = [
                    ['M', [x, y]],
                    ['l', [w, 0]],
                    ['l', [0, h]],
                    ['l', [-w, 0]],
                    ['Z', []]
                ]
                self.getPathVertices(str(inkex.paths.Path(a)), node, matNew)

            elif node.tag in (inkex.addNS('line', 'svg'), 'line'):
                x1 = float(node.get('x1', '0'))
                y1 = float(node.get('y1', '0'))
                x2 = float(node.get('x2', '0'))
                y2 = float(node.get('y2', '0'))
                a = [
                    ['M', [x1, y1]],
                    ['L', [x2, y2]]
                ]
                self.getPathVertices(str(inkex.paths.Path(a)), node, matNew)

            elif node.tag in (inkex.addNS('polyline', 'svg'), 'polyline'):
                pl = node.get('points', '').strip()
                if pl == '':
                    continue
                pa = pl.split()
                d = "".join(["M " + pa[i] if i == 0 else " L " + pa[i] for i in range(0, len(pa))])
                self.getPathVertices(d, node, matNew)

            elif node.tag in (inkex.addNS('polygon', 'svg'), 'polygon'):
                pl = node.get('points', '').strip()
                if pl == '':
                    continue
                pa = pl.split()
                d = "".join(["M " + pa[i] if i == 0 else " L " + pa[i] for i in range(0, len(pa))])
                d += " Z"
                self.getPathVertices(d, node, matNew)

            elif node.tag in (inkex.addNS('ellipse', 'svg'), 'ellipse', inkex.addNS('circle', 'svg'), 'circle'):
                if node.tag in (inkex.addNS('ellipse', 'svg'), 'ellipse'):
                    rx = float(node.get('rx', '0'))
                    ry = float(node.get('ry', '0'))
                else:
                    rx = float(node.get('r', '0'))
                    ry = rx
                if rx == 0 or ry == 0:
                    continue
                cx = float(node.get('cx', '0'))
                cy = float(node.get('cy', '0'))
                x1 = cx - rx
                x2 = cx + rx
                d = 'M %f,%f '     % (x1, cy) + \
                    'A %f,%f '     % (rx, ry) + \
                    '0 1 0 %f,%f ' % (x2, cy) + \
                    'A %f,%f '     % (rx, ry) + \
                    '0 1 0 %f,%f'  % (x1, cy)
                self.getPathVertices(d, node, matNew)

    def recursivelyGetEnclosingTransform(self, node):
        node = node.getparent()
        if node is not None:
            parent_transform = self.recursivelyGetEnclosingTransform(node)
            node_transform = node.get('transform', None)
            if node_transform is None:
                return parent_transform
            else:
                tr = inkex.Transform(node_transform)
                if parent_transform is None:
                    return tr
                else:
                    return parent_transform @ tr
        else:
            return self.docTransform

    def get_category_for_node(self, node):
        for attr in ('id', '{http://www.inkscape.org/namespaces/inkscape}label'):
            val = node.get(attr)
            if val:
                for prefix, module_name in CATEGORIES.items():
                    if val.lower().startswith(prefix.lower()):
                        return prefix, module_name

        parent = node.getparent()
        while parent is not None:
            for attr in ('id', '{http://www.inkscape.org/namespaces/inkscape}label'):
                val = parent.get(attr)
                if val:
                    for prefix, module_name in CATEGORIES.items():
                        if val.lower().startswith(prefix.lower()):
                            return prefix, module_name
            parent = parent.getparent()

        return None, None

    def effect(self):
        self.handleViewBox()

        if self.options.ids:
            for id in self.options.ids:
                transform = self.recursivelyGetEnclosingTransform(self.svg.selected[id])
                self.recursivelyTraverseSvg([self.svg.selected[id]], transform)
        else:
            self.recursivelyTraverseSvg(self.svg, self.docTransform)

        if not self.paths:
            inkex.errormsg("Warning: No valid paths or shapes found in document.")
            return

        self.cx = self.xmin + (self.xmax - self.xmin) / 2.0
        self.cy = self.ymin + (self.ymax - self.ymin) / 2.0

        scale_opt = self.options.base_scale
        if scale_opt == '3cm':
            scale_desc = "80 units = 2.40m (1 unit = 3cm)"
            wall_height = 80.0
            door_height = 66.6
            window_header = 70.0
            window_sill = 30.0
            floor_thickness = 5.0
            balcony_height = 36.6
            frame_width = 2.0
            scale_factor = (25.4 / 96.0) / 30.0
        elif scale_opt == '1cm':
            scale_desc = "240 units = 2.40m (1 unit = 1cm)"
            wall_height = 240.0
            door_height = 200.0
            window_header = 210.0
            window_sill = 90.0
            floor_thickness = 15.0
            balcony_height = 110.0
            frame_width = 6.0
            scale_factor = (25.4 / 96.0) / 10.0
        elif scale_opt == '1mm':
            scale_desc = "2400 units = 2.40m (1 unit = 1mm)"
            wall_height = 2400.0
            door_height = 2000.0
            window_header = 2100.0
            window_sill = 900.0
            floor_thickness = 150.0
            balcony_height = 1100.0
            frame_width = 60.0
            scale_factor = (25.4 / 96.0) / 1.0
        elif scale_opt == '1m':
            scale_desc = "2.4 units = 2.40m (1 unit = 1m)"
            wall_height = 2.4
            door_height = 2.0
            window_header = 2.1
            window_sill = 0.9
            floor_thickness = 0.15
            balcony_height = 1.10
            frame_width = 0.06
            scale_factor = (25.4 / 96.0) / 1000.0
        else:
            scale_desc = "80 units = 2.40m (1 unit = 3cm)"
            wall_height = 80.0
            door_height = 66.6
            window_header = 70.0
            window_sill = 30.0
            floor_thickness = 5.0
            balcony_height = 36.6
            frame_width = 2.0
            scale_factor = (25.4 / 96.0) / 30.0

        try:
            out_fname = self.options.fname.format(**{'NAME': self.basename})
            if not os.path.isabs(out_fname) and 'PWD' in os.environ:
                out_fname = os.path.join(os.environ['PWD'], out_fname)
            scad_fname = os.path.expanduser(out_fname)

            with open(scad_fname, 'w') as f:
                # Section A: Parameters (Global Variables)
                f.write(f"// Generated from SVG floor plan \"{self.basename}.svg\" at {time.ctime()}\n")
                f.write(f"// Base Z-Scale: {scale_desc}\n\n")
                f.write(f"BASE_Z_SCALE = 80;\n")
                f.write(f"WALL_HEIGHT      = {wall_height:.2f}/80 * BASE_Z_SCALE;  // Standard ceiling height (2.40m)\n")
                f.write(f"DOOR_HEIGHT      = {door_height:.2f}/80 * BASE_Z_SCALE;  // Standard door clearance (2.00m)\n")
                f.write(f"WINDOW_HEADER    = {window_header:.2f}/80 * BASE_Z_SCALE;  // Top of the window frame (2.10m)\n")
                f.write(f"WINDOW_SILL      = {window_sill:.2f}/80 * BASE_Z_SCALE;  // Standard window sill height (0.90m)\n")
                f.write(f"FLOOR_THICKNESS  = {floor_thickness:.2f}/80 * BASE_Z_SCALE;  // Slab thickness below Z=0 (0.15m)\n")
                f.write(f"BALCONY_HEIGHT   = {balcony_height:.2f}/80 * BASE_Z_SCALE;  // Height for balcony/varanda walls (1.10m)\n")
                f.write(f"FRAME_WIDTH      = {frame_width:.2f}/80 * BASE_Z_SCALE;  // Width of door and window frames\n\n")
                f.write("RENDER_DOORS     = true;\n")
                f.write("RENDER_WINDOWS   = true;\n")
                f.write("RENDER_FLOORS    = true;\n")
                f.write("RENDER_FURNITURE = true;\n\n")
                f.write(f"SCALE_FACTOR     = {scale_factor:.8f};\n")
                f.write("module apply_svg_scale() {\n")
                f.write("    scale([SCALE_FACTOR, -SCALE_FACTOR, 1]) children(); // 96 DPI and unit adjustment\n")
                f.write("}\n\n")

                # Section B: Semantic Modules
                f.write("/* --- Semantic Modules --- */\n\n")
                f.write("""module wall(points, paths=[], h=WALL_HEIGHT) {
    color([0.9, 0.9, 0.92])
    linear_extrude(height=h, convexity=10) {
        if (len(paths) > 0) {
            polygon(points, paths);
        } else {
            polygon(points);
        }
    }
}

module wall_outer(points, paths=[], h=WALL_HEIGHT) {
    color([0.9, 0.9, 0.92])
    linear_extrude(height=h, convexity=10) {
        if (len(paths) > 0) {
            polygon(points, paths);
        } else {
            polygon(points);
        }
    }
}

module wall_inner(points, paths=[], h=WALL_HEIGHT) {
    color([0.9, 0.9, 0.92])
    linear_extrude(height=h, convexity=10) {
        if (len(paths) > 0) {
            polygon(points, paths);
        } else {
            polygon(points);
        }
    }
}

module wall_balcony(points, paths=[], h=BALCONY_HEIGHT) {
    color([0.9, 0.9, 0.92])
    linear_extrude(height=h, convexity=10) {
        if (len(paths) > 0) {
            polygon(points, paths);
        } else {
            polygon(points);
        }
    }
}

module floor_slab(points, paths=[], h=FLOOR_THICKNESS) {
    if (RENDER_FLOORS) {
        color([0.85, 0.8, 0.75]) // Light wood/tile base
        translate([0, 0, -h])
        linear_extrude(height=h, convexity=10) {
            if (len(paths) > 0) {
                polygon(points, paths);
            } else {
                polygon(points);
            }
        }
    }
}

module door_wood(points, paths=[]) {
    // Lintel wall above door
    color([0.9, 0.9, 0.92])
    translate([0, 0, DOOR_HEIGHT])
    linear_extrude(height=WALL_HEIGHT - DOOR_HEIGHT, convexity=10) {
        if (len(paths) > 0) {
            polygon(points, paths);
        } else {
            polygon(points);
        }
    }
    if (RENDER_DOORS) {
        color([0.4, 0.25, 0.1]) // Wood tone
        linear_extrude(height=DOOR_HEIGHT, convexity=10) {
            if (len(paths) > 0) {
                polygon(points, paths);
            } else {
                polygon(points);
            }
        }
    }
}

module door_glass(points, paths=[]) {
    // Lintel wall above door
    color([0.9, 0.9, 0.92])
    translate([0, 0, DOOR_HEIGHT])
    linear_extrude(height=WALL_HEIGHT - DOOR_HEIGHT, convexity=10) {
        if (len(paths) > 0) {
            polygon(points, paths);
        } else {
            polygon(points);
        }
    }
    if (RENDER_DOORS) {
        // Wood frame
        color([0.4, 0.25, 0.1]) // Wood tone
        linear_extrude(height=DOOR_HEIGHT, convexity=10) {
            difference() {
                if (len(paths) > 0) {
                    polygon(points, paths);
                } else {
                    polygon(points);
                }
                offset(delta = -FRAME_WIDTH) {
                    if (len(paths) > 0) {
                        polygon(points, paths);
                    } else {
                        polygon(points);
                    }
                }
            }
        }
        // Glass panel
        color([0.5, 0.8, 1.0, 0.3]) // Translucent glass
        linear_extrude(height=DOOR_HEIGHT, convexity=10) {
            offset(delta = -FRAME_WIDTH) {
                if (len(paths) > 0) {
                    polygon(points, paths);
                } else {
                    polygon(points);
                }
            }
        }
    }
}

module sliding_glass_door(points, paths=[]) {
    // Lintel wall above door
    color([0.9, 0.9, 0.92])
    translate([0, 0, DOOR_HEIGHT])
    linear_extrude(height=WALL_HEIGHT - DOOR_HEIGHT, convexity=10) {
        if (len(paths) > 0) {
            polygon(points, paths);
        } else {
            polygon(points);
        }
    }
    if (RENDER_DOORS) {
        // Dark minimal frame
        color("darkslategrey")
        linear_extrude(height=DOOR_HEIGHT, convexity=10) {
            difference() {
                if (len(paths) > 0) {
                    polygon(points, paths);
                } else {
                    polygon(points);
                }
                offset(delta = -FRAME_WIDTH / 2.0) {
                    if (len(paths) > 0) {
                        polygon(points, paths);
                    } else {
                        polygon(points);
                    }
                }
            }
        }
        // Glass panel
        color([0.5, 0.8, 1.0, 0.3]) // Translucent glass
        linear_extrude(height=DOOR_HEIGHT, convexity=10) {
            offset(delta = -FRAME_WIDTH / 2.0) {
                if (len(paths) > 0) {
                    polygon(points, paths);
                } else {
                    polygon(points);
                }
            }
        }
    }
}

module window_standard(points, paths=[]) {
    // Sill wall below window
    color([0.9, 0.9, 0.92])
    linear_extrude(height=WINDOW_SILL, convexity=10) {
        if (len(paths) > 0) {
            polygon(points, paths);
        } else {
            polygon(points);
        }
    }
    // Lintel wall above window
    color([0.9, 0.9, 0.92])
    translate([0, 0, WINDOW_HEADER])
    linear_extrude(height=WALL_HEIGHT - WINDOW_HEADER, convexity=10) {
        if (len(paths) > 0) {
            polygon(points, paths);
        } else {
            polygon(points);
        }
    }
    if (RENDER_WINDOWS) {
        // Window frame
        color([0.75, 0.78, 0.80]) // Light aluminium frame
        translate([0, 0, WINDOW_SILL])
        linear_extrude(height=WINDOW_HEADER - WINDOW_SILL, convexity=10) {
            difference() {
                if (len(paths) > 0) {
                    polygon(points, paths);
                } else {
                    polygon(points);
                }
                offset(delta = -FRAME_WIDTH) {
                    if (len(paths) > 0) {
                        polygon(points, paths);
                    } else {
                        polygon(points);
                    }
                }
            }
        }
        // Glass pane
        color([0.5, 0.8, 1.0, 0.3]) // Translucent glass
        translate([0, 0, WINDOW_SILL])
        linear_extrude(height=WINDOW_HEADER - WINDOW_SILL, convexity=10) {
            if (len(paths) > 0) {
                polygon(points, paths);
            } else {
                polygon(points);
            }
        }
    }
}

module wardrobe(points, paths=[]) {
    if (RENDER_FURNITURE) {
        color("wheat")
        linear_extrude(height=WALL_HEIGHT, convexity=10) {
            if (len(paths) > 0) {
                polygon(points, paths);
            } else {
                polygon(points);
            }
        }
    }
}
""")
                f.write("\n/* --- Data Extraction & Coordinates --- */\n\n")

                counts = {cat: 0 for cat in CATEGORIES.values()}
                counts['wall'] = 0

                data_lines = []
                exec_lines = []

                for node, path in self.paths.items():
                    if not path or len(path) == 0:
                        continue

                    prefix, module_name = self.get_category_for_node(node)
                    if not module_name:
                        label = node.get('{http://www.inkscape.org/namespaces/inkscape}label')
                        node_id = node.get('id', 'unnamed')
                        name_to_warn = label if label else node_id

                        if name_to_warn not in self.warnings_printed:
                            inkex.errormsg(f"Warning: Object '{name_to_warn}' did not match any category prefix. Falling back to standard 'wall'.")
                            self.warnings_printed.add(name_to_warn)

                        module_name = 'wall'

                    counts[module_name] += 1
                    idx = counts[module_name]
                    var_base = f"path_{module_name}_{idx}"

                    contains = [[] for _ in range(len(path))]
                    contained_by = [[] for _ in range(len(path))]

                    for i in range(len(path)):
                        for j in range(i + 1, len(path)):
                            if polyInPoly(path[j][0], path[j][1], path[i][0], path[i][1]):
                                contains[i].append(j)
                                contained_by[j].append(i)
                            elif polyInPoly(path[i][0], path[i][1], path[j][0], path[j][1]):
                                contains[j].append(i)
                                contained_by[i].append(j)

                    for i in range(len(path)):
                        if len(contained_by[i]) > 0:
                            continue

                        subpath = path[i][0]
                        if len(subpath) < 3:
                            continue

                        polypoints = []
                        polypaths = []

                        for pt in subpath:
                            polypoints.append([pt[0] - self.cx, pt[1] - self.cy])

                        has_holes = len(contains[i]) > 0
                        if has_holes:
                            polypaths.append(list(range(len(subpath))))
                            curr_idx = len(subpath)

                            for j in contains[i]:
                                inner_subpath = path[j][0]
                                inner_indices = []
                                for pt in inner_subpath:
                                    polypoints.append([pt[0] - self.cx, pt[1] - self.cy])
                                    inner_indices.append(curr_idx)
                                    curr_idx += 1
                                polypaths.append(inner_indices)

                        suffix = f"_{i}" if len(path) > 1 else ""
                        var_name = f"{var_base}{suffix}"

                        data_lines.append(f"{var_name}_points = {format_points(polypoints)};\n")
                        if has_holes:
                            data_lines.append(f"{var_name}_paths = {format_paths(polypaths)};\n")
                            exec_lines.append(f"        {module_name}({var_name}_points, {var_name}_paths);\n")
                        else:
                            exec_lines.append(f"        {module_name}({var_name}_points);\n")

                for line in data_lines:
                    f.write(line)

                f.write("\n/* --- Execution Set --- */\n\n")
                f.write("union() {\n")
                f.write("    apply_svg_scale() {\n")
                for line in exec_lines:
                    f.write(line)
                f.write("    }\n")
                f.write("}\n")

        except IOError as e:
            inkex.errormsg('Unable to write file ' + self.options.fname)
            inkex.errormsg("ERROR: " + str(e))


if __name__ == '__main__':
    FloorplanToOpenSCAD().run()
