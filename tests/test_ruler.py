import pytest

from ruler import CORNERS, RULER_LENGTH_ATTR, RULER_LENGTHS, RULER_MARKER_ATTR, mm_to_doc_units, ruler_geometry

# ------------------------------------------------------------------- mm_to_doc_units


def test_mm_to_doc_units_1m_default_scale():
    assert mm_to_doc_units(1000.0) == pytest.approx(3779.5275590551)


def test_mm_to_doc_units_scales_inversely_with_doc_scale():
    assert mm_to_doc_units(1000.0, doc_scale=2.0) == pytest.approx(1889.7637795276)


def test_mm_to_doc_units_matches_svg_parser_m_conversion():
    # SVGParser.length_to_px uses dpi * 1000 / 25.4 for "m" -> px at 96dpi.
    assert mm_to_doc_units(1000.0) == pytest.approx(96.0 * 1000.0 / 25.4)


# ------------------------------------------------------------------- ruler_geometry


def test_bar_length_matches_requested_real_world_length():
    geometry = ruler_geometry("1m", "bottom-left", doc_width=5000.0, doc_height=5000.0)
    x1, _, x2, _ = geometry["bar"]
    assert abs(x2 - x1) == pytest.approx(geometry["length_units"])
    assert geometry["length_units"] == pytest.approx(mm_to_doc_units(1000.0))


@pytest.mark.parametrize("length_key", list(RULER_LENGTHS.keys()))
def test_bar_length_scales_with_requested_length(length_key):
    geometry = ruler_geometry(length_key, "bottom-left", doc_width=50000.0, doc_height=50000.0)
    expected_mm, _ = RULER_LENGTHS[length_key]
    assert geometry["length_units"] == pytest.approx(mm_to_doc_units(expected_mm))


def test_unknown_length_key_falls_back_to_default():
    default_geometry = ruler_geometry("1m", "bottom-left", doc_width=5000.0, doc_height=5000.0)
    fallback_geometry = ruler_geometry("bogus", "bottom-left", doc_width=5000.0, doc_height=5000.0)
    assert fallback_geometry["length_units"] == pytest.approx(default_geometry["length_units"])


def test_unknown_corner_falls_back_to_default():
    default_geometry = ruler_geometry("1m", "bottom-left", doc_width=5000.0, doc_height=5000.0)
    fallback_geometry = ruler_geometry("1m", "bogus", doc_width=5000.0, doc_height=5000.0)
    assert fallback_geometry["bar"] == default_geometry["bar"]


@pytest.mark.parametrize("corner", CORNERS)
def test_bar_stays_within_document_bounds(corner):
    doc_width, doc_height = 5000.0, 5000.0
    geometry = ruler_geometry("1m", corner, doc_width=doc_width, doc_height=doc_height)
    x1, y1, x2, y2 = geometry["bar"]
    assert 0.0 <= min(x1, x2) and max(x1, x2) <= doc_width
    assert 0.0 <= min(y1, y2) and max(y1, y2) <= doc_height


def test_left_corners_anchor_bar_near_left_edge():
    geometry = ruler_geometry("1m", "bottom-left", doc_width=5000.0, doc_height=5000.0)
    x1, _, x2, _ = geometry["bar"]
    assert min(x1, x2) < 200.0


def test_right_corners_anchor_bar_near_right_edge():
    doc_width = 5000.0
    geometry = ruler_geometry("1m", "bottom-right", doc_width=doc_width, doc_height=5000.0)
    x1, _, x2, _ = geometry["bar"]
    assert max(x1, x2) > doc_width - 200.0


def test_top_corners_place_label_below_bar():
    geometry = ruler_geometry("1m", "top-left", doc_width=5000.0, doc_height=5000.0)
    _, bar_y, _, _ = geometry["bar"]
    assert geometry["label"]["y"] > bar_y


def test_bottom_corners_place_label_above_bar():
    geometry = ruler_geometry("1m", "bottom-left", doc_width=5000.0, doc_height=5000.0)
    _, bar_y, _, _ = geometry["bar"]
    assert geometry["label"]["y"] < bar_y


def test_label_centered_on_bar():
    geometry = ruler_geometry("1m", "bottom-left", doc_width=5000.0, doc_height=5000.0)
    x1, _, x2, _ = geometry["bar"]
    assert geometry["label"]["x"] == pytest.approx((x1 + x2) / 2.0)


def test_label_text_matches_length_key():
    geometry = ruler_geometry("50cm", "bottom-left", doc_width=5000.0, doc_height=5000.0)
    assert geometry["label"]["text"] == "50 cm"


def test_length_mm_matches_length_key():
    geometry = ruler_geometry("50cm", "bottom-left", doc_width=5000.0, doc_height=5000.0)
    assert geometry["length_mm"] == pytest.approx(500.0)


def test_length_mm_matches_length_units_via_mm_to_doc_units():
    geometry = ruler_geometry("2m", "bottom-left", doc_width=50000.0, doc_height=50000.0, doc_scale=1.5)
    assert geometry["length_units"] == pytest.approx(mm_to_doc_units(geometry["length_mm"], doc_scale=1.5))


def test_marker_and_length_attrs_are_distinct_and_stable():
    # Names are part of the on-disk SVG contract read back by
    # svg_parser.find_ruler_calibration and SVGParser._traverse; changing
    # them breaks calibration/exclusion for any SVG saved with the old names.
    assert RULER_MARKER_ATTR == "data-floorplan-ruler"
    assert RULER_LENGTH_ATTR == "data-ruler-mm"
    assert RULER_MARKER_ATTR != RULER_LENGTH_ATTR


def test_doc_origin_offset_is_respected():
    plain = ruler_geometry("1m", "bottom-left", doc_width=5000.0, doc_height=5000.0)
    offset = ruler_geometry("1m", "bottom-left", doc_width=5000.0, doc_height=5000.0, doc_x=100.0, doc_y=50.0)
    x1, y1, x2, y2 = plain["bar"]
    ox1, oy1, ox2, oy2 = offset["bar"]
    assert ox1 == pytest.approx(x1 + 100.0)
    assert ox2 == pytest.approx(x2 + 100.0)
    assert oy1 == pytest.approx(y1 + 50.0)
    assert oy2 == pytest.approx(y2 + 50.0)
