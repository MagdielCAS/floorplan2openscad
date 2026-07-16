"""Semantic category definitions, scale presets, and category resolution. No inkex dependency."""

CATEGORIES = {
    "floor_": "floor_slab",
    "wall_outer_": "wall_outer",
    "wall_inner_": "wall_inner",
    "wall_balcony_": "wall_balcony",
    "door_wood_": "door_wood",
    "door_glass_": "door_glass",
    "sliding_door_": "sliding_glass_door",
    "window_standard_": "window_standard",
    "wardrobe_": "wardrobe",
}

SCALE_PRESETS = {
    "3cm": {
        "desc": "80 units = 2.40m (1 unit = 3cm)",
        "wall_height": 80.0,
        "door_height": 66.6,
        "window_header": 70.0,
        "window_sill": 30.0,
        "floor_thickness": 5.0,
        "balcony_height": 36.6,
        "frame_width": 2.0,
        "scale_factor": (25.4 / 96.0) / 30.0,
    },
    "1cm": {
        "desc": "240 units = 2.40m (1 unit = 1cm)",
        "wall_height": 240.0,
        "door_height": 200.0,
        "window_header": 210.0,
        "window_sill": 90.0,
        "floor_thickness": 15.0,
        "balcony_height": 110.0,
        "frame_width": 6.0,
        "scale_factor": (25.4 / 96.0) / 10.0,
    },
    "1mm": {
        "desc": "2400 units = 2.40m (1 unit = 1mm)",
        "wall_height": 2400.0,
        "door_height": 2000.0,
        "window_header": 2100.0,
        "window_sill": 900.0,
        "floor_thickness": 150.0,
        "balcony_height": 1100.0,
        "frame_width": 60.0,
        "scale_factor": (25.4 / 96.0) / 1.0,
    },
    "1m": {
        "desc": "2.4 units = 2.40m (1 unit = 1m)",
        "wall_height": 2.4,
        "door_height": 2.0,
        "window_header": 2.1,
        "window_sill": 0.9,
        "floor_thickness": 0.15,
        "balcony_height": 1.10,
        "frame_width": 0.06,
        "scale_factor": (25.4 / 96.0) / 1000.0,
    },
}

_DEFAULT_SCALE = "3cm"

_INKSCAPE_LABEL = "{http://www.inkscape.org/namespaces/inkscape}label"


def get_scale_config(scale_opt):
    """Return the scale preset dict for scale_opt, defaulting to 3cm."""
    return SCALE_PRESETS.get(scale_opt, SCALE_PRESETS[_DEFAULT_SCALE])


def match_category(label_or_id):
    """Return (prefix, module_name) for the first matching CATEGORIES prefix, or (None, None)."""
    if not label_or_id:
        return None, None
    val = label_or_id.lower()
    for prefix, module_name in CATEGORIES.items():
        if val.startswith(prefix.lower()):
            return prefix, module_name
    return None, None


def resolve_category(node):
    """Walk node and its ancestors to find a matching category prefix.

    Works with any object whose .get(attr) returns a string and .getparent()
    returns the parent node (duck-typed; compatible with inkex elements).
    Returns (prefix, module_name) or (None, None).
    """
    for attr in ("id", _INKSCAPE_LABEL):
        prefix, module_name = match_category(node.get(attr))
        if module_name:
            return prefix, module_name

    parent = node.getparent()
    while parent is not None:
        for attr in ("id", _INKSCAPE_LABEL):
            prefix, module_name = match_category(parent.get(attr))
            if module_name:
                return prefix, module_name
        parent = parent.getparent()

    return None, None
