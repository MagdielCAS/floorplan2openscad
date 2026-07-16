from mesh_validator import (
    check_subpath,
    find_cross_object_overlaps,
    is_closed,
    is_degenerate,
    polygon_area,
    polygon_self_intersects,
    segments_intersect,
    validate_geometry,
)

# ---------------------------------------------------------------- segments_intersect

_SQUARE = [(0, 0), (10, 0), (10, 10), (0, 10)]


def test_segments_intersect_crossing():
    assert segments_intersect((0, 0), (10, 10), (0, 10), (10, 0)) is True


def test_segments_intersect_parallel_no_cross():
    assert segments_intersect((0, 0), (10, 0), (0, 5), (10, 5)) is False


def test_segments_intersect_shared_endpoint_not_flagged_as_self_intersection():
    # Adjacent edges of a normal convex polygon share a vertex but the polygon
    # itself should not be reported as self-intersecting (see polygon_self_intersects tests).
    assert segments_intersect(_SQUARE[0], _SQUARE[1], _SQUARE[1], _SQUARE[2]) is True


def test_segments_intersect_collinear_overlapping():
    assert segments_intersect((0, 0), (10, 0), (5, 0), (15, 0)) is True


def test_segments_intersect_collinear_disjoint():
    assert segments_intersect((0, 0), (10, 0), (20, 0), (30, 0)) is False


# ------------------------------------------------------------------- polygon_area


def test_polygon_area_square():
    assert abs(polygon_area([[0, 0], [10, 0], [10, 10], [0, 10]])) == 100.0


def test_polygon_area_triangle():
    assert abs(polygon_area([[0, 0], [10, 0], [0, 10]])) == 50.0


# --------------------------------------------------------------------- is_closed


def test_is_closed_true():
    assert is_closed([[0, 0], [10, 0], [10, 10], [0, 0]]) is True


def test_is_closed_false():
    assert is_closed([[0, 0], [10, 0], [10, 10]]) is False


def test_is_closed_epsilon_tolerance():
    assert is_closed([[0, 0], [10, 0], [10, 10], [1e-9, -1e-9]]) is True


# ----------------------------------------------------------------- is_degenerate


def test_is_degenerate_collinear_points():
    assert is_degenerate([[0, 0], [5, 0], [10, 0]], bbox=[0, 10, 0, 0]) is True


def test_is_degenerate_diagonal_collinear_points():
    # Collinear along a diagonal: nonzero bbox area, but zero polygon area.
    verts = [[0, 0], [5, 5], [10, 10]]
    bbox = [0, 10, 0, 10]
    assert is_degenerate(verts, bbox) is True


def test_is_degenerate_valid_square():
    verts = [[0, 0], [10, 0], [10, 10], [0, 10]]
    bbox = [0, 10, 0, 10]
    assert is_degenerate(verts, bbox) is False


# ------------------------------------------------------------ polygon_self_intersects


def test_polygon_self_intersects_bowtie():
    bowtie = [[0, 0], [10, 10], [10, 0], [0, 10]]
    assert polygon_self_intersects(bowtie) is True


def test_polygon_self_intersects_valid_square():
    assert polygon_self_intersects([[0, 0], [10, 0], [10, 10], [0, 10]]) is False


def test_polygon_self_intersects_valid_triangle():
    assert polygon_self_intersects([[0, 0], [10, 0], [5, 10]]) is False


# ---------------------------------------------------------------- check_subpath


def test_check_subpath_valid_closed_square():
    verts = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
    assert check_subpath(verts, bbox=[0, 10, 0, 10]) == []


def test_check_subpath_unclosed():
    verts = [[0, 0], [10, 0], [5, 10]]
    assert "unclosed" in check_subpath(verts, bbox=[0, 10, 0, 10])


def test_check_subpath_self_intersecting():
    bowtie = [[0, 0], [10, 10], [10, 0], [0, 10], [0, 0]]
    assert "self_intersecting" in check_subpath(bowtie, bbox=[0, 10, 0, 10])


def test_check_subpath_degenerate_collinear():
    verts = [[0, 0], [5, 0], [10, 0]]
    assert "degenerate" in check_subpath(verts, bbox=[0, 10, 0, 0])


def test_check_subpath_skips_short_subpaths():
    assert check_subpath([[0, 0], [10, 0]], bbox=[0, 10, 0, 0]) == []


# --------------------------------------------------------------- validate_geometry


def test_validate_geometry_reports_per_node():
    paths_dict = {
        "node_a": [[[[0, 0], [10, 0], [5, 10]], [0, 10, 0, 10]]],  # unclosed
    }
    warnings = validate_geometry(paths_dict)
    assert len(warnings) == 1
    assert warnings[0].node == "node_a"
    assert warnings[0].kind == "unclosed"
    assert warnings[0].other_node is None


def test_validate_geometry_no_issues():
    paths_dict = {
        "node_a": [[[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]], [0, 10, 0, 10]]],
    }
    assert validate_geometry(paths_dict) == []


# ---------------------------------------------------------- find_cross_object_overlaps


def test_find_cross_object_overlaps_two_overlapping_squares():
    square_a = [[0, 0], [10, 0], [10, 10], [0, 10]]
    square_b = [[5, 5], [15, 5], [15, 15], [5, 15]]
    paths_dict = {
        "node_a": [[square_a, [0, 10, 0, 10]]],
        "node_b": [[square_b, [5, 15, 5, 15]]],
    }
    warnings = find_cross_object_overlaps(paths_dict)
    assert len(warnings) == 1
    assert warnings[0].kind == "overlap"
    assert {warnings[0].node, warnings[0].other_node} == {"node_a", "node_b"}


def test_find_cross_object_overlaps_hole_in_outer_same_node():
    outer = [[0, 0], [20, 0], [20, 20], [0, 20]]
    inner = [[5, 5], [15, 5], [15, 15], [5, 15]]
    paths_dict = {
        "node_a": [
            [outer, [0, 20, 0, 20]],
            [inner, [5, 15, 5, 15]],
        ],
    }
    assert find_cross_object_overlaps(paths_dict) == []


def test_find_cross_object_overlaps_full_containment_different_nodes():
    outer = [[0, 0], [20, 0], [20, 20], [0, 20]]
    inner = [[5, 5], [15, 5], [15, 15], [5, 15]]
    paths_dict = {
        "node_a": [[outer, [0, 20, 0, 20]]],
        "node_b": [[inner, [5, 15, 5, 15]]],
    }
    assert find_cross_object_overlaps(paths_dict) == []


def test_find_cross_object_overlaps_disjoint():
    square_a = [[0, 0], [10, 0], [10, 10], [0, 10]]
    square_b = [[100, 100], [110, 100], [110, 110], [100, 110]]
    paths_dict = {
        "node_a": [[square_a, [0, 10, 0, 10]]],
        "node_b": [[square_b, [100, 110, 100, 110]]],
    }
    assert find_cross_object_overlaps(paths_dict) == []
