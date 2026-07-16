"""Pure helpers for building a new layer's id/label from a category prefix and
a user-supplied suffix. No inkex dependency."""

import re

_DISALLOWED_CHARS = re.compile(r"[^A-Za-z0-9_-]+")
_REPEAT_SEPARATORS = re.compile(r"[_-]{2,}")


def sanitize_suffix(suffix):
    """Normalize a user-supplied suffix into a safe id/label fragment.

    Replaces disallowed characters with underscores, collapses repeated
    separators, and strips leading/trailing separators. Returns "" if
    nothing usable remains.
    """
    cleaned = _DISALLOWED_CHARS.sub("_", suffix or "")
    cleaned = _REPEAT_SEPARATORS.sub("_", cleaned)
    return cleaned.strip("_-")


def build_layer_name(prefix, suffix):
    """Build a full layer name from a category prefix and a raw suffix.

    Falls back to "1" if the sanitized suffix is empty, so the result never
    ends in a bare prefix with a trailing underscore.
    """
    clean = sanitize_suffix(suffix)
    return prefix + (clean or "1")


def unique_layer_name(candidate, existing_ids):
    """Disambiguate candidate against existing_ids by appending -2, -3, ...

    existing_ids may be any container supporting `in`.
    """
    if candidate not in existing_ids:
        return candidate
    n = 2
    while f"{candidate}-{n}" in existing_ids:
        n += 1
    return f"{candidate}-{n}"
