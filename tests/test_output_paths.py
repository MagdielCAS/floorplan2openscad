import os

from output_paths import category_output_path, resolve_output_path

# ------------------------------------------------------------------- resolve_output_path


def test_resolve_output_path_substitutes_name():
    assert resolve_output_path("{NAME}.scad", "myfloor", {}) == "myfloor.scad"


def test_resolve_output_path_expands_user():
    result = resolve_output_path("~/Downloads/{NAME}.scad", "myfloor", {})
    assert result == os.path.expanduser("~/Downloads/myfloor.scad")


def test_resolve_output_path_joins_pwd_for_relative_paths():
    result = resolve_output_path("{NAME}.scad", "myfloor", {"PWD": "/home/user/project"})
    assert result == "/home/user/project/myfloor.scad"


def test_resolve_output_path_absolute_path_ignores_pwd():
    result = resolve_output_path("/tmp/{NAME}.scad", "myfloor", {"PWD": "/home/user/project"})
    assert result == "/tmp/myfloor.scad"


def test_resolve_output_path_no_pwd_leaves_relative_path_untouched():
    assert resolve_output_path("{NAME}.scad", "myfloor", {}) == "myfloor.scad"


# ------------------------------------------------------------------- category_output_path


def test_category_output_path_inserts_before_extension():
    assert category_output_path("/tmp/myfloor.scad", "wall_outer") == "/tmp/myfloor_wall_outer.scad"


def test_category_output_path_no_extension():
    assert category_output_path("/tmp/myfloor", "door_wood") == "/tmp/myfloor_door_wood"


def test_category_output_path_preserves_directory():
    assert category_output_path("~/Downloads/plan.scad", "floor_slab") == "~/Downloads/plan_floor_slab.scad"
