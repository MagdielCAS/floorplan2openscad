"""Best-effort automatic repair for geometry issues detected by mesh_validator. No inkex
dependency. Never touches "overlap" issues -- see mesh_validator.py and HANDOFF.md for why
cross-object overlap is not auto-fixable (no clipping library, and many overlaps are
intentional, e.g. mitered wall corners)."""

from collections import namedtuple

from mesh_validator import (
    MAX_SELF_INTERSECT_VERTICES,
    find_self_intersecting_edge_pair,
    is_closed,
    is_degenerate,
    polygon_self_intersects,
)

RepairResult = namedtuple("RepairResult", ["node", "kind", "fixed"])
# kind in {"self_intersecting", "unclosed", "degenerate"}; "overlap" never appears here.


def close_subpath(vertices):
    """Return a new vertex list with vertices[0] appended if not already closed (a copy;
    original untouched). The appended point already exists in the point set, so any bbox
    computed for `vertices` remains valid for the result -- no bbox recompute needed."""
    if is_closed(vertices):
        return list(vertices)
    return list(vertices) + [vertices[0]]


def try_uncross_polygon(vertices, max_vertices=MAX_SELF_INTERSECT_VERTICES, max_iterations=None):
    """Attempt to remove self-intersections via iterative 2-opt edge-uncrossing: repeatedly
    find one pair of non-adjacent crossing edges (via find_self_intersecting_edge_pair) and
    reverse the vertex run strictly between them. This is a minimal local edit -- it reorders
    the existing point set rather than reshaping the polygon (e.g. via an angular sort), so it
    will not corrupt a legitimately non-convex ring that merely has an unrelated crossing.
    Terminates because each reversal of a genuine crossing strictly decreases total ring
    perimeter (triangle inequality -- the standard 2-opt property); `max_iterations` is a
    defensive cap for degenerate inputs (duplicate/collinear points) where that guarantee
    doesn't cleanly apply, and is exposed mainly so callers/tests can force the "gave up" path
    deterministically.

    Returns (new_vertices, fixed: bool). new_vertices preserves the original point set and
    open/closed state; on failure, returns the ORIGINAL `vertices` unchanged and fixed=False.
    """
    closed = is_closed(vertices)
    ring = list(vertices[:-1]) if closed else list(vertices)
    m = len(ring)
    if m > max_vertices:
        return vertices, False
    if max_iterations is None:
        max_iterations = max(16, 4 * m)

    for _ in range(max_iterations):
        pair = find_self_intersecting_edge_pair(ring)
        if pair is None:
            return (ring + [ring[0]] if closed else ring), True
        i, j = pair
        ring[i + 1 : j + 1] = list(reversed(ring[i + 1 : j + 1]))

    return vertices, False


def repair_geometry(paths_dict):
    """Best-effort in-place repair of paths_dict, using the same per-subpath checks as
    mesh_validator.validate_geometry. Mutates each node's subpath_list in paths_dict (replacing
    vertex lists, or dropping degenerate subpaths outright) and returns one RepairResult per
    (node, subpath) issue found describing what was attempted and whether it fully succeeded.
    Never emits or acts on "overlap" -- callers should still separately run
    find_cross_object_overlaps if check_overlap is enabled; auto-fix has no effect on it.
    """
    results = []
    for node, subpath_list in list(paths_dict.items()):
        new_subpath_list = []
        for vertices, bbox in subpath_list:
            if len(vertices) < 3:
                new_subpath_list.append([vertices, bbox])
                continue

            if is_degenerate(vertices, bbox):
                results.append(RepairResult(node=node, kind="degenerate", fixed=True))
                continue  # drop: contributes ~zero area, consistent with build_items()
                # already silently skipping subpaths it can't render

            fixed_vertices = vertices
            if polygon_self_intersects(fixed_vertices):
                fixed_vertices, ok = try_uncross_polygon(fixed_vertices)
                results.append(RepairResult(node=node, kind="self_intersecting", fixed=ok))

            if not is_closed(fixed_vertices):
                fixed_vertices = close_subpath(fixed_vertices)
                results.append(RepairResult(node=node, kind="unclosed", fixed=True))

            new_subpath_list.append([fixed_vertices, bbox])
        paths_dict[node] = new_subpath_list
    return results
