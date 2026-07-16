import pytest

from categories import (
    CATEGORIES,
    SCALE_PRESETS,
    find_layer_label,
    get_scale_config,
    match_category,
    node_label,
    resolve_category,
)

# ----------------------------------------------------------------- CATEGORIES


def test_categories_has_expected_prefixes():
    expected = {
        "floor_",
        "wall_outer_",
        "wall_inner_",
        "wall_balcony_",
        "door_wood_",
        "door_glass_",
        "sliding_door_",
        "window_standard_",
        "wardrobe_",
    }
    assert set(CATEGORIES.keys()) == expected


def test_categories_maps_to_module_names():
    assert CATEGORIES["wall_outer_"] == "wall_outer"
    assert CATEGORIES["floor_"] == "floor_slab"
    assert CATEGORIES["sliding_door_"] == "sliding_glass_door"


# ---------------------------------------------------------------- SCALE_PRESETS


_REQUIRED_KEYS = {
    "desc",
    "wall_height",
    "door_height",
    "window_header",
    "window_sill",
    "floor_thickness",
    "balcony_height",
    "frame_width",
    "scale_factor",
}


@pytest.mark.parametrize("scale", ["3cm", "1cm", "1mm", "1m"])
def test_scale_presets_have_required_keys(scale):
    assert _REQUIRED_KEYS <= set(SCALE_PRESETS[scale].keys())


def test_scale_preset_3cm_ceiling():
    cfg = SCALE_PRESETS["3cm"]
    assert cfg["wall_height"] == pytest.approx(80.0)


def test_scale_preset_1m_ceiling():
    cfg = SCALE_PRESETS["1m"]
    assert cfg["wall_height"] == pytest.approx(2.4)


# ---------------------------------------------------------------- get_scale_config


def test_get_scale_config_valid():
    cfg = get_scale_config("1cm")
    assert cfg["wall_height"] == pytest.approx(240.0)


def test_get_scale_config_unknown_falls_back_to_3cm():
    cfg = get_scale_config("unknown_unit")
    assert cfg == SCALE_PRESETS["3cm"]


# ---------------------------------------------------------------- match_category


@pytest.mark.parametrize(
    "label,expected_module",
    [
        ("wall_outer_north", "wall_outer"),
        ("wall_inner_corridor", "wall_inner"),
        ("wall_balcony_west", "wall_balcony"),
        ("floor_ground", "floor_slab"),
        ("door_wood_entrance", "door_wood"),
        ("door_glass_terrace", "door_glass"),
        ("sliding_door_living", "sliding_glass_door"),
        ("window_standard_s", "window_standard"),
        ("wardrobe_bedroom", "wardrobe"),
    ],
)
def test_match_category_known_prefixes(label, expected_module):
    _, module_name = match_category(label)
    assert module_name == expected_module


def test_match_category_case_insensitive():
    _, module_name = match_category("WALL_OUTER_PERIMETER")
    assert module_name == "wall_outer"


def test_match_category_unknown_returns_none():
    prefix, module_name = match_category("furniture_table")
    assert prefix is None
    assert module_name is None


def test_match_category_empty_string():
    prefix, module_name = match_category("")
    assert prefix is None
    assert module_name is None


def test_match_category_none():
    prefix, module_name = match_category(None)
    assert prefix is None
    assert module_name is None


# ---------------------------------------------------------------- resolve_category


class _MockNode:
    """Minimal duck-type of an inkex element for testing resolve_category."""

    def __init__(self, attrs, parent=None):
        self._attrs = attrs
        self._parent = parent

    def get(self, attr, default=None):
        return self._attrs.get(attr, default)

    def getparent(self):
        return self._parent


_INKSCAPE_LABEL = "{http://www.inkscape.org/namespaces/inkscape}label"
_INKSCAPE_GROUPMODE = "{http://www.inkscape.org/namespaces/inkscape}groupmode"


def test_resolve_category_by_id():
    node = _MockNode({"id": "wall_inner_hall"})
    _, module_name = resolve_category(node)
    assert module_name == "wall_inner"


def test_resolve_category_by_inkscape_label():
    node = _MockNode({_INKSCAPE_LABEL: "floor_slab_level1"})
    _, module_name = resolve_category(node)
    assert module_name == "floor_slab"


def test_resolve_category_falls_back_to_parent():
    parent = _MockNode({_INKSCAPE_LABEL: "window_standard_south"})
    child = _MockNode({"id": "rect42"}, parent=parent)
    _, module_name = resolve_category(child)
    assert module_name == "window_standard"


def test_resolve_category_no_match_returns_none():
    node = _MockNode({"id": "furniture_chair"})
    prefix, module_name = resolve_category(node)
    assert prefix is None
    assert module_name is None


# -------------------------------------------------------------------- node_label


def test_node_label_prefers_inkscape_label():
    node = _MockNode({"id": "rect42", _INKSCAPE_LABEL: "wall_outer_north"})
    assert node_label(node) == "wall_outer_north"


def test_node_label_falls_back_to_id():
    node = _MockNode({"id": "rect42"})
    assert node_label(node) == "rect42"


def test_node_label_falls_back_to_unnamed():
    node = _MockNode({})
    assert node_label(node) == "unnamed"


# --------------------------------------------------------------- find_layer_label


def test_find_layer_label_direct_parent():
    layer = _MockNode({_INKSCAPE_GROUPMODE: "layer", _INKSCAPE_LABEL: "wall_outer_perimeter"})
    node = _MockNode({"id": "outer_wall_ring"}, parent=layer)
    assert find_layer_label(node) == "wall_outer_perimeter"


def test_find_layer_label_skips_non_layer_groups():
    layer = _MockNode({_INKSCAPE_GROUPMODE: "layer", _INKSCAPE_LABEL: "wall_outer_perimeter"})
    group = _MockNode({"id": "decorative_group"}, parent=layer)
    node = _MockNode({"id": "outer_wall_ring"}, parent=group)
    assert find_layer_label(node) == "wall_outer_perimeter"


def test_find_layer_label_no_layer_ancestor():
    node = _MockNode({"id": "outer_wall_ring"})
    assert find_layer_label(node) is None
