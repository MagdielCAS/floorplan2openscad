"""Pure geometry for the on-canvas scale-ruler guide. No inkex dependency.

The ruler calibrates against the document's real width/height/viewBox, not
the base_scale preset in categories.py: scale_factor in SCALE_PRESETS is
self-canceling across presets (scale_factor * mm_per_unit is always
25.4/96 regardless of preset), so the base_scale dropdown never changes a
drawing's real-world XY footprint -- only its Z-height constants and output
unit label. The document's width/height/viewBox is what actually determines
how many raw SVG user-space units correspond to a real-world meter.
"""

# Matches the 96dpi assumption used throughout the extension family (see
# SVGParser.length_to_px).
_DPI = 96.0
_MM_PER_INCH = 25.4

# length_key -> (real-world length in mm, display label)
RULER_LENGTHS = {
    "10cm": (100.0, "10 cm"),
    "50cm": (500.0, "50 cm"),
    "1m": (1000.0, "1 m"),
    "2m": (2000.0, "2 m"),
    "5m": (5000.0, "5 m"),
}

CORNERS = ("top-left", "top-right", "bottom-left", "bottom-right")

_DEFAULT_LENGTH = "1m"
_DEFAULT_CORNER = "bottom-left"

_TICK_RATIO = 0.03
_MIN_TICK = 5.0
_MAX_TICK = 40.0

# Marks the ruler's top-level layer, so SVGParser._traverse can skip the
# whole guide (bar, ticks, label) -- it never reaches paths_dict, so it's
# excluded from the .scad output, geometry checks, and the bounding-box
# centroid, regardless of what it's named or whether it's currently visible.
RULER_MARKER_ATTR = "data-floorplan-ruler"

# Holds the real-world length (in mm) the ruler bar currently represents,
# on the bar path itself. This is fixed at insertion time and does not
# change if the user later resizes the bar -- resizing the bar is exactly
# how the user recalibrates the drawing's scale (see find_ruler_calibration
# in svg_parser.py, which locates this bar via direct xpath rather than
# SVGParser traversal, since calibration must work even while the ruler
# layer is hidden).
RULER_LENGTH_ATTR = "data-ruler-mm"


def mm_to_doc_units(length_mm, doc_scale=1.0):
    """Convert a real-world length in mm to raw SVG user-space (viewBox) units.

    doc_scale is the ratio of the document's physical pixel size to its
    viewBox size along one axis (matching the `sx`/`sy` computed in
    FloorplanToOpenSCAD._handle_view_box). Defaults to 1.0 for documents
    where the viewBox matches width/height 1:1 (e.g. plain px documents).
    """
    physical_px = length_mm * _DPI / _MM_PER_INCH
    return physical_px / (doc_scale or 1.0)


def ruler_geometry(length_key, corner, doc_width, doc_height, doc_scale=1.0, doc_x=0.0, doc_y=0.0, margin_ratio=0.03):
    """Compute the scale-ruler's bar/ticks/label geometry in document (viewBox) coordinates.

    doc_width/doc_height describe the visible page area in viewBox
    coordinates; doc_x/doc_y is the page origin (0,0 unless the viewBox
    itself is offset).

    Returns a dict:
        {
            "bar": (x1, y1, x2, y2),
            "ticks": [(x1, y1, x2, y2), (x1, y1, x2, y2)],
            "label": {"x": float, "y": float, "text": str},
            "length_units": float,
            "length_mm": float,
        }
    """
    length_mm, label_text = RULER_LENGTHS.get(length_key, RULER_LENGTHS[_DEFAULT_LENGTH])
    bar_len = mm_to_doc_units(length_mm, doc_scale)

    if corner not in CORNERS:
        corner = _DEFAULT_CORNER

    margin = margin_ratio * min(doc_width, doc_height)
    tick = min(_MAX_TICK, max(_MIN_TICK, bar_len * _TICK_RATIO))
    label_gap = max(tick * 0.8, 8.0)

    if corner.endswith("left"):
        x1 = doc_x + margin
        x2 = x1 + bar_len
    else:
        x2 = doc_x + doc_width - margin
        x1 = x2 - bar_len

    if corner.startswith("top"):
        y = doc_y + margin
        label_y = y + tick + label_gap
    else:
        y = doc_y + doc_height - margin
        label_y = y - tick - label_gap

    ticks = [
        (x1, y - tick, x1, y + tick),
        (x2, y - tick, x2, y + tick),
    ]

    label = {"x": (x1 + x2) / 2.0, "y": label_y, "text": label_text}

    return {
        "bar": (x1, y, x2, y),
        "ticks": ticks,
        "label": label,
        "length_units": bar_len,
        "length_mm": length_mm,
    }
