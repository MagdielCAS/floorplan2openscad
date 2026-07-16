import xml.etree.ElementTree as ET
from pathlib import Path

from categories import CATEGORIES

_INX_PATH = Path(__file__).parent.parent / "floorplan_add_layer.inx"
_NS = {"inx": "http://www.inkscape.org/namespace/inkscape/extension"}


def _category_option_values():
    root = ET.parse(_INX_PATH).getroot()
    param = root.find(".//inx:param[@name='category']", _NS)
    return {opt.get("value") for opt in param.findall("inx:option", _NS)}


def test_category_options_match_categories_keys():
    assert _category_option_values() == set(CATEGORIES.keys())
