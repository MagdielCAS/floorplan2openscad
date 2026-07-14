import pytest
from geometry import (
    bbox_in_bbox,
    format_paths,
    format_points,
    parse_length_with_units,
    point_in_bbox,
    point_in_poly,
    poly_in_poly,
)

# ------------------------------------------------------------------ bbox helpers


def test_point_in_bbox_inside():
    assert point_in_bbox((5, 5), (0, 10, 0, 10)) is True


def test_point_in_bbox_outside():
    assert point_in_bbox((15, 5), (0, 10, 0, 10)) is False


def test_point_in_bbox_on_edge():
    assert point_in_bbox((0, 5), (0, 10, 0, 10)) is True


def test_bbox_in_bbox_contained():
    assert bbox_in_bbox((2, 8, 2, 8), (0, 10, 0, 10)) is True


def test_bbox_in_bbox_overflow():
    assert bbox_in_bbox((2, 12, 2, 8), (0, 10, 0, 10)) is False


def test_bbox_in_bbox_identical():
    assert bbox_in_bbox((0, 10, 0, 10), (0, 10, 0, 10)) is True


# ----------------------------------------------------------- point_in_poly


_SQUARE = [(0, 0), (10, 0), (10, 10), (0, 10)]


def test_point_in_poly_center():
    assert point_in_poly((5, 5), _SQUARE) is True


def test_point_in_poly_outside():
    assert point_in_poly((15, 5), _SQUARE) is False


def test_point_in_poly_on_vertex():
    assert point_in_poly((0, 0), _SQUARE) is True


def test_point_in_poly_none_inputs():
    assert point_in_poly(None, _SQUARE) is False
    assert point_in_poly((5, 5), None) is False


def test_point_in_poly_with_bbox_outside_bbox():
    # Should short-circuit before ray-casting when point is outside bbox
    assert point_in_poly((20, 20), _SQUARE, bbox=(0, 10, 0, 10)) is False


# ---------------------------------------------------------------- poly_in_poly


_OUTER = [(0, 0), (20, 0), (20, 20), (0, 20)]
_INNER = [(5, 5), (15, 5), (15, 15), (5, 15)]
_OUTER_BBOX = (0, 20, 0, 20)
_INNER_BBOX = (5, 15, 5, 15)


def test_poly_in_poly_contained():
    assert poly_in_poly(_INNER, _INNER_BBOX, _OUTER, _OUTER_BBOX) is True


def test_poly_in_poly_not_contained():
    outside = [(25, 5), (35, 5), (35, 15), (25, 15)]
    outside_bbox = (25, 35, 5, 15)
    assert poly_in_poly(outside, outside_bbox, _OUTER, _OUTER_BBOX) is False


def test_poly_in_poly_bbox_shortcircuit():
    far_away = [(100, 100), (110, 100), (110, 110), (100, 110)]
    far_bbox = (100, 110, 100, 110)
    assert poly_in_poly(far_away, far_bbox, _OUTER, _OUTER_BBOX) is False


# --------------------------------------------------------------- formatters


def test_format_points_basic():
    result = format_points([[1.0, 2.0], [3.5, 4.5]])
    assert result == "[[1.0000,2.0000],[3.5000,4.5000]]"


def test_format_points_precision():
    result = format_points([[1.23456789, 0.0]])
    assert result == "[[1.2346,0.0000]]"


def test_format_paths_basic():
    result = format_paths([[0, 1, 2], [3, 4]])
    assert result == "[[0,1,2],[3,4]]"


# ------------------------------------------------------- parse_length_with_units


@pytest.mark.parametrize("val,expected_v,expected_u", [
    ("100px", 100.0, "px"),
    ("25.4mm", 25.4, "mm"),
    ("2.54cm", 2.54, "cm"),
    ("1in", 1.0, "in"),
    ("1m",  1.0, "m"),
    ("50%", 50.0, "%"),
    ("72pt", 72.0, "pt"),
])
def test_parse_length_with_units(val, expected_v, expected_u):
    v, u = parse_length_with_units(val)
    assert v == pytest.approx(expected_v)
    assert u == expected_u


def test_parse_length_with_units_invalid():
    v, u = parse_length_with_units("not_a_number")
    assert v is None
    assert u is None


def test_parse_length_with_units_default_unit():
    v, u = parse_length_with_units("42")
    assert v == pytest.approx(42.0)
    assert u == "px"
