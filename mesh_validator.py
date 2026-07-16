"""Geometry-quality validation for SVG floor plan input. No inkex dependency."""

from collections import namedtuple

from geometry import bboxes_intersect, poly_in_poly

_EPS = 1e-6
_AREA_RATIO_EPS = 1e-6
MAX_SELF_INTERSECT_VERTICES = 500

GeometryWarning = namedtuple("GeometryWarning", ["node", "kind", "other_node"])
# kind in {"self_intersecting", "unclosed", "degenerate", "overlap"}; other_node is None except for "overlap"


# ------------------------------------------------------------------ primitives


def _points_close(a, b, epsilon=_EPS):
    return abs(a[0] - b[0]) <= epsilon and abs(a[1] - b[1]) <= epsilon


def _orientation(a, b, c, epsilon=_EPS):
    val = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    if abs(val) <= epsilon:
        return 0
    return 1 if val > 0 else -1


def _on_segment(a, b, c):
    """Assumes a, b, c are collinear. True if c lies within the bbox of segment a-b."""
    return min(a[0], b[0]) - _EPS <= c[0] <= max(a[0], b[0]) + _EPS and min(a[1], b[1]) - _EPS <= c[1] <= max(a[1], b[1]) + _EPS


def segments_intersect(p1, p2, p3, p4):
    """Classic orientation-based segment intersection test, incl. collinear cases."""
    o1 = _orientation(p1, p2, p3)
    o2 = _orientation(p1, p2, p4)
    o3 = _orientation(p3, p4, p1)
    o4 = _orientation(p3, p4, p2)

    if o1 != o2 and o3 != o4:
        return True

    if o1 == 0 and _on_segment(p1, p2, p3):
        return True
    if o2 == 0 and _on_segment(p1, p2, p4):
        return True
    if o3 == 0 and _on_segment(p3, p4, p1):
        return True
    if o4 == 0 and _on_segment(p3, p4, p2):
        return True

    return False


def segments_cross(p1, p2, p3, p4):
    """True only for a proper transversal crossing (not shared/touching endpoints or
    collinear-overlapping segments). Used for overlap detection between separate objects,
    where edges merely touching along a shared boundary (e.g. a window flush against a
    wall) is normal floor-plan authoring, not a defect."""
    o1 = _orientation(p1, p2, p3)
    o2 = _orientation(p1, p2, p4)
    o3 = _orientation(p3, p4, p1)
    o4 = _orientation(p3, p4, p2)
    return o1 != o2 and o3 != o4 and 0 not in (o1, o2, o3, o4)


# --------------------------------------------------------------- per-subpath


def is_closed(vertices, epsilon=_EPS):
    return _points_close(vertices[0], vertices[-1], epsilon)


def polygon_area(vertices):
    """Shoelace formula. Handles a duplicate closing vertex without special-casing."""
    n = len(vertices)
    area = 0.0
    for i in range(n):
        x1, y1 = vertices[i]
        x2, y2 = vertices[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return area / 2.0


def is_degenerate(vertices, bbox=None, area_ratio_epsilon=_AREA_RATIO_EPS):
    if bbox is not None:
        bbox_area = (bbox[1] - bbox[0]) * (bbox[3] - bbox[2])
        if bbox_area <= 0:
            return True
        return abs(polygon_area(vertices)) <= area_ratio_epsilon * bbox_area
    return abs(polygon_area(vertices)) <= area_ratio_epsilon


def find_self_intersecting_edge_pair(ring):
    """Return (i, j), i < j, indices of the first non-adjacent crossing edge pair in `ring`
    (a flat, already-de-duplicated vertex list -- NOT closed with a repeated first/last point),
    or None if none cross. Shared by polygon_self_intersects's boolean check and
    mesh_repair.try_uncross_polygon's 2-opt uncrossing, which needs the actual offending pair
    rather than a yes/no answer."""
    m = len(ring)
    if m < 4:
        return None
    for i in range(m):
        a1, a2 = ring[i], ring[(i + 1) % m]
        for j in range(i + 1, m):
            if j == i or j == (i + 1) % m or (j + 1) % m == i:
                continue
            b1, b2 = ring[j], ring[(j + 1) % m]
            if segments_intersect(a1, a2, b1, b2):
                return (i, j)
    return None


def polygon_self_intersects(vertices, max_vertices=MAX_SELF_INTERSECT_VERTICES):
    ring = vertices[:-1] if is_closed(vertices) else vertices
    if len(ring) > max_vertices:
        return False
    return find_self_intersecting_edge_pair(ring) is not None


def check_subpath(vertices, bbox=None, epsilon=_EPS):
    if len(vertices) < 3:
        return []
    issues = []
    if polygon_self_intersects(vertices):
        issues.append("self_intersecting")
    if not is_closed(vertices, epsilon):
        issues.append("unclosed")
    if is_degenerate(vertices, bbox):
        issues.append("degenerate")
    return issues


def validate_geometry(paths_dict, epsilon=_EPS):
    warnings = []
    for node, subpath_list in paths_dict.items():
        for vertices, bbox in subpath_list:
            for kind in check_subpath(vertices, bbox, epsilon):
                warnings.append(GeometryWarning(node=node, kind=kind, other_node=None))
    return warnings


# ------------------------------------------------------------- cross-object


def _outer_contours(subpath_list):
    """Subpaths not contained by a sibling subpath in the same node, skipping <3-vertex subpaths."""
    n = len(subpath_list)
    contained = [False] * n
    for i in range(n):
        vi, bi = subpath_list[i]
        for j in range(n):
            if i != j and poly_in_poly(vi, bi, subpath_list[j][0], subpath_list[j][1]):
                contained[i] = True
                break
    return [subpath_list[i] for i in range(n) if not contained[i] and len(subpath_list[i][0]) >= 3]


def polygons_partially_overlap(poly_a, bbox_a, poly_b, bbox_b):
    """True if the two polygons' areas intersect but neither fully contains the other."""
    if not bboxes_intersect(bbox_a, bbox_b):
        return False
    if poly_in_poly(poly_a, bbox_a, poly_b, bbox_b) or poly_in_poly(poly_b, bbox_b, poly_a, bbox_a):
        return False
    na, nb = len(poly_a), len(poly_b)
    for i in range(na):
        a1, a2 = poly_a[i], poly_a[(i + 1) % na]
        for j in range(nb):
            b1, b2 = poly_b[j], poly_b[(j + 1) % nb]
            if segments_cross(a1, a2, b1, b2):
                return True
    return False


def find_cross_object_overlaps(paths_dict):
    nodes = list(paths_dict.keys())
    outer_by_node = {n: _outer_contours(paths_dict[n]) for n in nodes}
    warnings = []
    for a in range(len(nodes)):
        for b in range(a + 1, len(nodes)):
            node_a, node_b = nodes[a], nodes[b]
            found = False
            for verts_a, bbox_a in outer_by_node[node_a]:
                if found:
                    break
                for verts_b, bbox_b in outer_by_node[node_b]:
                    if polygons_partially_overlap(verts_a, bbox_a, verts_b, bbox_b):
                        warnings.append(GeometryWarning(node=node_a, kind="overlap", other_node=node_b))
                        found = True
                        break
    return warnings
