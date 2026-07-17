"""Output filename resolution for the .scad writer. No inkex dependency."""

import os


def resolve_output_path(fname_template, basename, environ):
    """Expand the '{NAME}' placeholder, resolve against PWD, and expand '~'."""
    out_fname = fname_template.format(**{"NAME": basename})
    if not os.path.isabs(out_fname) and "PWD" in environ:
        out_fname = os.path.join(environ["PWD"], out_fname)
    return os.path.expanduser(out_fname)


def category_output_path(path, category):
    """Insert '_<category>' before the file extension of an already-resolved output path."""
    root, ext = os.path.splitext(path)
    return f"{root}_{category}{ext}"
