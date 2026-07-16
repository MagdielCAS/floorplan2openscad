import xml.etree.ElementTree as ET
from pathlib import Path

from ruler import CORNERS, RULER_LENGTHS

_INX_PATH = Path(__file__).parent.parent / "floorplan_add_ruler.inx"
_NS = {"inx": "http://www.inkscape.org/namespace/inkscape/extension"}


def _option_values(param_name):
    root = ET.parse(_INX_PATH).getroot()
    param = root.find(f".//inx:param[@name='{param_name}']", _NS)
    return {opt.get("value") for opt in param.findall("inx:option", _NS)}


def test_length_options_match_ruler_lengths_keys():
    assert _option_values("length") == set(RULER_LENGTHS.keys())


def test_corner_options_match_ruler_corners():
    assert _option_values("corner") == set(CORNERS)
