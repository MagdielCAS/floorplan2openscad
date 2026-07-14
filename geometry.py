"""Pure-Python 2D geometry utilities. No inkex dependency."""


def parse_length_with_units(str_val, default_unit='px'):
    u = default_unit
    s = str_val.strip()
    if s[-2:] in ('px', 'pt', 'pc', 'mm', 'cm', 'in', 'ft'):
        u, s = s[-2:], s[:-2]
    elif s[-1:] in ('m', '%'):
        u, s = s[-1:], s[:-1]
    try:
        return float(s), u
    except (ValueError, TypeError):
        return None, None


def point_in_bbox(pt, bbox):
    """bbox = (xmin, xmax, ymin, ymax)"""
    return not (pt[0] < bbox[0] or pt[0] > bbox[1] or pt[1] < bbox[2] or pt[1] > bbox[3])


def bbox_in_bbox(inner, outer):
    return not (inner[0] < outer[0] or inner[1] > outer[1] or inner[2] < outer[2] or inner[3] > outer[3])


def point_in_poly(p, poly, bbox=None):
    if p is None or poly is None:
        return False
    if bbox is not None and not point_in_bbox(p, bbox):
        return False
    if p in poly:
        return True

    x, y = p[0], p[1]
    n = len(poly)

    p1 = poly[0]
    p2 = poly[1] if n > 1 else poly[0]
    for i in range(n):
        if i != 0:
            p1, p2 = poly[i - 1], poly[i]
        if y == p1[1] and p1[1] == p2[1] and min(p1[0], p2[0]) < x < max(p1[0], p2[0]):
            return True

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


def poly_in_poly(poly1, bbox1, poly2, bbox2):
    if bbox1 is not None and bbox2 is not None and not bbox_in_bbox(bbox1, bbox2):
        return False
    return all(point_in_poly(p, poly2, bbox2) for p in poly1)


def format_points(points):
    return "[" + ",".join(f"[{pt[0]:.4f},{pt[1]:.4f}]" for pt in points) + "]"


def format_paths(paths):
    return "[" + ",".join("[" + ",".join(str(idx) for idx in path) + "]" for path in paths) + "]"
