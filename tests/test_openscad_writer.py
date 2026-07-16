import io

import pytest

from categories import get_scale_config
from openscad_writer import build_items, write_scad

# ---------------------------------------------------------------- build_items


def _make_path(vertices):
    """Wrap a vertex list in the subpath_list format returned by SVGParser."""
    xs = [v[0] for v in vertices]
    ys = [v[1] for v in vertices]
    bbox = [min(xs), max(xs), min(ys), max(ys)]
    return [[vertices, bbox]]


def test_build_items_single_shape():
    verts = [[0, 0], [10, 0], [10, 10], [0, 10]]
    items = build_items([("wall_outer", _make_path(verts))], cx=5.0, cy=5.0)
    assert len(items) == 1
    item = items[0]
    assert item["module_name"] == "wall_outer"
    assert item["var_name"] == "path_wall_outer_1"
    assert item["polypaths"] == []
    # Verify centering: all points should be shifted by (-cx, -cy)
    assert item["points"][0] == pytest.approx([-5.0, -5.0])
    assert item["points"][2] == pytest.approx([5.0, 5.0])


def test_build_items_detects_holes():
    outer = [[0, 0], [20, 0], [20, 20], [0, 20]]
    inner = [[5, 5], [15, 5], [15, 15], [5, 15]]
    # Both subpaths in the same element (the SVGParser puts them in the same list)
    xs_o, ys_o = [v[0] for v in outer], [v[1] for v in outer]
    xs_i, ys_i = [v[0] for v in inner], [v[1] for v in inner]
    path = [
        [outer, [min(xs_o), max(xs_o), min(ys_o), max(ys_o)]],
        [inner, [min(xs_i), max(xs_i), min(ys_i), max(ys_i)]],
    ]
    items = build_items([("floor_slab", path)], cx=10.0, cy=10.0)
    assert len(items) == 1
    item = items[0]
    # Should have polypaths (hole detected)
    assert len(item["polypaths"]) == 2
    # Outer path indices: 0..3 (4 outer vertices), hole indices start at 4
    assert item["polypaths"][0] == [0, 1, 2, 3]
    assert item["polypaths"][1] == [4, 5, 6, 7]
    # Total points: 4 outer + 4 inner = 8
    assert len(item["points"]) == 8


def test_build_items_skips_degenerate_subpaths():
    # Subpath with fewer than 3 vertices should be skipped
    items = build_items([("wall_inner", [[[[0, 0], [10, 0]], [0, 10, 0, 0]]])], cx=0, cy=0)
    assert items == []


def test_build_items_sequential_var_names():
    verts = [[0, 0], [5, 0], [5, 5], [0, 5]]
    pairs = [("door_wood", _make_path(verts)), ("door_wood", _make_path(verts))]
    items = build_items(pairs, cx=2.5, cy=2.5)
    assert items[0]["var_name"] == "path_door_wood_1"
    assert items[1]["var_name"] == "path_door_wood_2"


# ---------------------------------------------------------------- write_scad


def _write_to_string(items, scale_key="3cm", basename="test"):
    buf = io.StringIO()
    write_scad(buf, basename, items, get_scale_config(scale_key))
    return buf.getvalue()


def test_write_scad_contains_basename():
    verts = [[0, 0], [10, 0], [10, 10], [0, 10]]
    items = build_items([("wall_outer", _make_path(verts))], cx=5, cy=5)
    output = _write_to_string(items, basename="my_floor")
    assert '"my_floor.svg"' in output


def test_write_scad_contains_base_z_scale():
    items = build_items([("floor_slab", _make_path([[0, 0], [10, 0], [10, 10], [0, 10]]))], cx=5, cy=5)
    output = _write_to_string(items)
    assert "BASE_Z_SCALE = 80;" in output


def test_write_scad_contains_all_global_vars():
    items = build_items([("wall_outer", _make_path([[0, 0], [5, 0], [5, 5], [0, 5]]))], cx=2.5, cy=2.5)
    output = _write_to_string(items)
    for var in (
        "WALL_HEIGHT",
        "DOOR_HEIGHT",
        "WINDOW_HEADER",
        "WINDOW_SILL",
        "FLOOR_THICKNESS",
        "BALCONY_HEIGHT",
        "FRAME_WIDTH",
        "SCALE_FACTOR",
    ):
        assert var in output, f"Missing global variable: {var}"


def test_write_scad_contains_semantic_modules():
    items = []
    output = _write_to_string(items)
    for mod in (
        "module wall(",
        "module wall_outer(",
        "module floor_slab(",
        "module door_wood(",
        "module window_standard(",
        "module wardrobe(",
    ):
        assert mod in output, f"Missing module definition: {mod}"


def test_write_scad_data_and_execution_sections():
    verts = [[0, 0], [10, 0], [10, 10], [0, 10]]
    items = build_items([("wall_inner", _make_path(verts))], cx=5, cy=5)
    output = _write_to_string(items)
    assert "path_wall_inner_1_points" in output
    assert "wall_inner(path_wall_inner_1_points)" in output


def test_write_scad_with_holes_passes_paths_arg():
    outer = [[0, 0], [20, 0], [20, 20], [0, 20]]
    inner = [[5, 5], [15, 5], [15, 15], [5, 15]]
    xs_o, ys_o = [v[0] for v in outer], [v[1] for v in outer]
    xs_i, ys_i = [v[0] for v in inner], [v[1] for v in inner]
    path = [
        [outer, [min(xs_o), max(xs_o), min(ys_o), max(ys_o)]],
        [inner, [min(xs_i), max(xs_i), min(ys_i), max(ys_i)]],
    ]
    items = build_items([("floor_slab", path)], cx=10, cy=10)
    output = _write_to_string(items)
    # Multi-subpath elements get a positional suffix (_0 for the first outer subpath)
    assert "path_floor_slab_1_0_paths" in output
    assert "floor_slab(path_floor_slab_1_0_points, path_floor_slab_1_0_paths)" in output


def test_write_scad_1cm_scale():
    items = build_items([("wall_outer", _make_path([[0, 0], [5, 0], [5, 5], [0, 5]]))], cx=2.5, cy=2.5)
    output = _write_to_string(items, scale_key="1cm")
    assert "240 units = 2.40m" in output


def test_write_scad_ends_with_closing_brace():
    items = build_items([("wall_outer", _make_path([[0, 0], [5, 0], [5, 5], [0, 5]]))], cx=2.5, cy=2.5)
    output = _write_to_string(items)
    assert output.rstrip().endswith("}")
