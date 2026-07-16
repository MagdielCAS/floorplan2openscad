import xml.etree.ElementTree as ET
from pathlib import Path

from categories import CATEGORIES, match_category

_TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "floorplan-starter.svg"
_INKSCAPE_GROUPMODE = "{http://www.inkscape.org/namespaces/inkscape}groupmode"
_SVG_G = "{http://www.w3.org/2000/svg}g"


def _layer_ids():
    root = ET.parse(_TEMPLATE_PATH).getroot()
    return [g.get("id") for g in root.iter(_SVG_G) if g.get(_INKSCAPE_GROUPMODE) == "layer"]


def test_every_layer_resolves_to_a_known_category():
    for layer_id in _layer_ids():
        _, module_name = match_category(layer_id)
        assert module_name is not None, f"layer {layer_id!r} did not match any category prefix"


def test_all_categories_represented_exactly_once():
    resolved = [match_category(layer_id)[0] for layer_id in _layer_ids()]
    assert sorted(resolved) == sorted(CATEGORIES.keys())
