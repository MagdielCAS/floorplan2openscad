import pytest

from layer_naming import build_layer_name, sanitize_suffix, unique_layer_name

# ------------------------------------------------------------------- sanitize_suffix


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("kitchen", "kitchen"),
        ("  kitchen  ", "kitchen"),
        ("kitchen north", "kitchen_north"),
        ("kitchen!!north", "kitchen_north"),
        ("__kitchen__", "kitchen"),
        ("a---b", "a_b"),
        ("", ""),
        ("!!!", ""),
        (None, ""),
    ],
)
def test_sanitize_suffix(raw, expected):
    assert sanitize_suffix(raw) == expected


# ------------------------------------------------------------------- build_layer_name


def test_build_layer_name_normal_suffix():
    assert build_layer_name("wall_outer_", "north") == "wall_outer_north"


def test_build_layer_name_empty_suffix_falls_back_to_1():
    assert build_layer_name("wardrobe_", "") == "wardrobe_1"


def test_build_layer_name_punctuation_only_suffix_falls_back_to_1():
    assert build_layer_name("wardrobe_", "!!!") == "wardrobe_1"


def test_build_layer_name_sanitizes_suffix():
    assert build_layer_name("door_wood_", "front door!") == "door_wood_front_door"


# ------------------------------------------------------------------- unique_layer_name


def test_unique_layer_name_no_collision():
    assert unique_layer_name("wall_outer_north", set()) == "wall_outer_north"


def test_unique_layer_name_single_collision():
    existing = {"wall_outer_north"}
    assert unique_layer_name("wall_outer_north", existing) == "wall_outer_north-2"


def test_unique_layer_name_multiple_collisions():
    existing = {"wall_outer_north", "wall_outer_north-2", "wall_outer_north-3"}
    assert unique_layer_name("wall_outer_north", existing) == "wall_outer_north-4"
