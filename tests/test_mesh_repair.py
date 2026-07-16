from mesh_repair import close_subpath, repair_geometry, try_uncross_polygon
from mesh_validator import is_closed, polygon_self_intersects

_BOWTIE = [[0, 0], [10, 10], [10, 0], [0, 10]]
# An asymmetric self-intersecting quadrilateral: unlike _BOWTIE, its shoelace area is nonzero
# (the two triangular lobes formed by the crossing aren't equal-area), so it isn't also flagged
# "degenerate" -- needed to test the self-intersection repair path in isolation from the
# degenerate-drop path, since repair_geometry checks "degenerate" first.
_ASYM_BOWTIE = [[0, 0], [10, 7], [10, 0], [0, 10]]

# ------------------------------------------------------------------- close_subpath


def test_close_subpath_appends_first_point():
    verts = [[0, 0], [10, 0], [10, 10], [0, 10]]
    result = close_subpath(verts)
    assert is_closed(result) is True
    assert result == verts + [verts[0]]


def test_close_subpath_already_closed_returns_equivalent_copy():
    verts = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
    result = close_subpath(verts)
    assert result == verts


# -------------------------------------------------------------- try_uncross_polygon


def test_try_uncross_polygon_simple_bowtie_fixes_with_one_reversal():
    result, fixed = try_uncross_polygon(_BOWTIE)
    assert fixed is True
    assert polygon_self_intersects(result) is False
    assert sorted(map(tuple, result)) == sorted(map(tuple, _BOWTIE))


def test_try_uncross_polygon_preserves_closed_ring():
    closed_bowtie = _BOWTIE + [_BOWTIE[0]]
    result, fixed = try_uncross_polygon(closed_bowtie)
    assert fixed is True
    assert is_closed(result) is True
    assert polygon_self_intersects(result) is False


def test_try_uncross_polygon_valid_nonconvex_L_shape_is_unchanged():
    l_shape = [[0, 0], [20, 0], [20, 10], [10, 10], [10, 20], [0, 20]]
    result, fixed = try_uncross_polygon(l_shape)
    assert fixed is True
    assert result == l_shape


def test_try_uncross_polygon_gives_up_after_iteration_cap():
    # max_iterations=0 deterministically forces the "gave up" path -- a stand-in for a
    # genuinely unfixable self-intersection, since the 2-opt reversal provably converges
    # for real crossings (each reversal strictly decreases ring perimeter), making a small
    # hand-built polygon that reliably resists convergence impractical to construct.
    result, fixed = try_uncross_polygon(_BOWTIE, max_iterations=0)
    assert fixed is False
    assert result == _BOWTIE


def test_try_uncross_polygon_respects_max_vertices_cap():
    result, fixed = try_uncross_polygon(_BOWTIE, max_vertices=2)
    assert fixed is False
    assert result == _BOWTIE


# ----------------------------------------------------------------- repair_geometry


def test_repair_geometry_closes_unclosed_subpath():
    verts = [[0, 0], [10, 0], [10, 10], [0, 10]]
    bbox = [0, 10, 0, 10]
    paths_dict = {"node_a": [[verts, bbox]]}
    results = repair_geometry(paths_dict)
    assert len(results) == 1
    assert results[0].node == "node_a"
    assert results[0].kind == "unclosed"
    assert results[0].fixed is True
    assert is_closed(paths_dict["node_a"][0][0]) is True
    assert paths_dict["node_a"][0][1] == bbox


def test_repair_geometry_drops_degenerate_subpath():
    valid_square = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
    degenerate = [[0, 0], [5, 0], [10, 0]]
    paths_dict = {
        "node_a": [
            [valid_square, [0, 10, 0, 10]],
            [degenerate, [0, 10, 0, 0]],
        ],
    }
    results = repair_geometry(paths_dict)
    assert len(results) == 1
    assert results[0].kind == "degenerate"
    assert results[0].fixed is True
    assert len(paths_dict["node_a"]) == 1
    assert paths_dict["node_a"][0][0] == valid_square


def test_repair_geometry_dropping_all_subpaths_leaves_empty_list():
    degenerate = [[0, 0], [5, 0], [10, 0]]
    paths_dict = {"node_a": [[degenerate, [0, 10, 0, 0]]]}
    repair_geometry(paths_dict)
    assert paths_dict["node_a"] == []


def test_repair_geometry_untangles_self_intersecting_subpath():
    closed_bowtie = _ASYM_BOWTIE + [_ASYM_BOWTIE[0]]
    paths_dict = {"node_a": [[closed_bowtie, [0, 10, 0, 10]]]}
    results = repair_geometry(paths_dict)
    assert len(results) == 1
    assert results[0].kind == "self_intersecting"
    assert results[0].fixed is True
    assert polygon_self_intersects(paths_dict["node_a"][0][0]) is False


def test_repair_geometry_combined_unclosed_and_self_intersecting():
    # Open (unclosed) AND self-intersecting: the bowtie's would-be closing point is omitted.
    paths_dict = {"node_a": [[list(_ASYM_BOWTIE), [0, 10, 0, 10]]]}
    results = repair_geometry(paths_dict)
    kinds = [r.kind for r in results]
    assert kinds == ["self_intersecting", "unclosed"]
    assert all(r.fixed for r in results)
    fixed_verts = paths_dict["node_a"][0][0]
    assert is_closed(fixed_verts) is True
    assert polygon_self_intersects(fixed_verts) is False


def test_repair_geometry_leaves_overlap_untouched():
    square_a = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
    square_b = [[5, 5], [15, 5], [15, 15], [5, 15], [5, 5]]
    paths_dict = {
        "node_a": [[square_a, [0, 10, 0, 10]]],
        "node_b": [[square_b, [5, 15, 5, 15]]],
    }
    results = repair_geometry(paths_dict)
    assert all(r.kind != "overlap" for r in results)
    assert paths_dict["node_a"][0][0] == square_a
    assert paths_dict["node_b"][0][0] == square_b


def test_repair_geometry_no_issues_is_a_noop():
    verts = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
    bbox = [0, 10, 0, 10]
    paths_dict = {"node_a": [[verts, bbox]]}
    results = repair_geometry(paths_dict)
    assert results == []
    assert paths_dict["node_a"][0][0] == verts
    assert paths_dict["node_a"][0][1] == bbox
