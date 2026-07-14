"""SVG document traversal and vertex extraction. Requires inkex."""

import inkex
from inkex.bezier import beziersplitatt, maxdist

from geometry import parse_length_with_units


def _subdivide_cubic_path(sp, flat, i=1):
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
        sp[i:1] = [[one[2], one[3], two[1]]]


class SVGParser:
    """Walks an SVG tree and extracts flattened vertex lists per node."""

    def __init__(self, smoothness=0.2):
        self.smoothness = smoothness
        self.dpi = 96.0
        self._paths = {}
        self._xmin = self._ymin = 1e70
        self._xmax = self._ymax = -1e70

    # ------------------------------------------------------------------ public

    def parse(self, svg, doc_transform):
        """Walk the SVG tree starting at svg with doc_transform applied.

        Returns (paths_dict, cx, cy) where paths_dict maps each inkex node to
        its subpath list: [([vertex, ...], (xmin, xmax, ymin, ymax)), ...].
        cx and cy are the document centroid used for coordinate centering.
        """
        self._paths = {}
        self._xmin = self._ymin = 1e70
        self._xmax = self._ymax = -1e70
        self._traverse(svg, doc_transform)
        cx = self._xmin + (self._xmax - self._xmin) / 2.0
        cy = self._ymin + (self._ymax - self._ymin) / 2.0
        return dict(self._paths), cx, cy

    def length_to_px(self, str_val, default_unit='px'):
        v, u = parse_length_with_units(str_val, default_unit)
        if v is None:
            return None
        conversions = {
            'mm': self.dpi / 25.4,
            'cm': self.dpi * 10.0 / 25.4,
            'm':  self.dpi * 1000.0 / 25.4,
            'in': self.dpi,
            'ft': 12.0 * self.dpi,
            'pt': self.dpi / 72.0,
            'pc': self.dpi / 6.0,
            'px': 1.0,
        }
        return float(v) * conversions.get(u, 1.0)

    # ----------------------------------------------------------------- private

    def _traverse(self, node_list, mat_current=None, parent_visibility='visible'):
        if mat_current is None:
            mat_current = inkex.Transform()

        for node in node_list:
            v = node.get('visibility', parent_visibility)
            if v == 'inherit':
                v = parent_visibility
            if v in ('hidden', 'collapse'):
                continue
            if node.get('style', '') == 'display:none':
                continue

            mat_new = mat_current @ inkex.Transform(node.get('transform'))
            tag = node.tag

            if tag in (inkex.addNS('g', 'svg'), 'g'):
                self._traverse(node, mat_new, v)
            elif tag in (inkex.addNS('use', 'svg'), 'use'):
                self._handle_use(node, mat_new, v)
            elif tag == inkex.addNS('path', 'svg'):
                d = node.get('d')
                if d:
                    self._extract_vertices(d, node, mat_new)
            elif tag in (inkex.addNS('rect', 'svg'), 'rect'):
                self._extract_vertices(self._rect_to_path(node), node, mat_new)
            elif tag in (inkex.addNS('line', 'svg'), 'line'):
                self._extract_vertices(self._line_to_path(node), node, mat_new)
            elif tag in (inkex.addNS('polyline', 'svg'), 'polyline'):
                self._extract_vertices(self._polyline_to_path(node), node, mat_new)
            elif tag in (inkex.addNS('polygon', 'svg'), 'polygon'):
                self._extract_vertices(self._polygon_to_path(node), node, mat_new)
            elif tag in (inkex.addNS('ellipse', 'svg'), 'ellipse',
                         inkex.addNS('circle', 'svg'), 'circle'):
                self._extract_vertices(self._ellipse_to_path(node), node, mat_new)

    def _handle_use(self, node, mat_new, v):
        refid = node.get(inkex.addNS('href', 'xlink'))
        if not refid:
            return
        refnode = node.xpath('//*[@id="%s"]' % refid[1:])
        if not refnode:
            return
        x, y = float(node.get('x', '0')), float(node.get('y', '0'))
        mat = mat_new @ inkex.Transform(f'translate({x},{y})') if (x or y) else mat_new
        self._traverse(refnode, mat, node.get('visibility', v))

    def _extract_vertices(self, path_str, node, transform):
        if not path_str:
            return
        try:
            p = inkex.paths.Path(path_str).to_superpath()
        except Exception:
            return
        if not p:
            return
        if transform:
            p = p.transform(transform)

        subpath_list = []
        subpath_vertices = []
        sp_xmin = sp_xmax = sp_ymin = sp_ymax = 0.0

        for sp in p:
            if subpath_vertices:
                subpath_list.append([subpath_vertices, [sp_xmin, sp_xmax, sp_ymin, sp_ymax]])

            subpath_vertices = []
            _subdivide_cubic_path(sp, float(self.smoothness))

            first = sp[0][1]
            subpath_vertices.append(first)
            sp_xmin = sp_xmax = first[0]
            sp_ymin = sp_ymax = first[1]

            for csp in sp[1:]:
                pt = csp[1]
                subpath_vertices.append(pt)
                sp_xmin = min(sp_xmin, pt[0])
                sp_xmax = max(sp_xmax, pt[0])
                sp_ymin = min(sp_ymin, pt[1])
                sp_ymax = max(sp_ymax, pt[1])

            self._xmin = min(self._xmin, sp_xmin)
            self._xmax = max(self._xmax, sp_xmax)
            self._ymin = min(self._ymin, sp_ymin)
            self._ymax = max(self._ymax, sp_ymax)

        if subpath_vertices:
            subpath_list.append([subpath_vertices, [sp_xmin, sp_xmax, sp_ymin, sp_ymax]])

        if subpath_list:
            self._paths[node] = subpath_list

    @staticmethod
    def _rect_to_path(node):
        x = float(node.get('x', '0'))
        y = float(node.get('y', '0'))
        w = float(node.get('width', '0'))
        h = float(node.get('height', '0'))
        return str(inkex.paths.Path([
            ['M', [x, y]], ['l', [w, 0]], ['l', [0, h]], ['l', [-w, 0]], ['Z', []]
        ]))

    @staticmethod
    def _line_to_path(node):
        return str(inkex.paths.Path([
            ['M', [float(node.get('x1', '0')), float(node.get('y1', '0'))]],
            ['L', [float(node.get('x2', '0')), float(node.get('y2', '0'))]]
        ]))

    @staticmethod
    def _polyline_to_path(node):
        pa = node.get('points', '').strip().split()
        if not pa:
            return None
        return ''.join(('M ' if i == 0 else ' L ') + pa[i] for i in range(len(pa)))

    @staticmethod
    def _polygon_to_path(node):
        pa = node.get('points', '').strip().split()
        if not pa:
            return None
        return ''.join(('M ' if i == 0 else ' L ') + pa[i] for i in range(len(pa))) + ' Z'

    @staticmethod
    def _ellipse_to_path(node):
        if node.tag in (inkex.addNS('circle', 'svg'), 'circle'):
            rx = ry = float(node.get('r', '0'))
        else:
            rx = float(node.get('rx', '0'))
            ry = float(node.get('ry', '0'))
        if not rx or not ry:
            return None
        cx = float(node.get('cx', '0'))
        cy = float(node.get('cy', '0'))
        x1, x2 = cx - rx, cx + rx
        return f'M {x1},{cy} A {rx},{ry} 0 1 0 {x2},{cy} A {rx},{ry} 0 1 0 {x1},{cy}'
