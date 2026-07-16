.DEFAULT_GOAL := help

UV := uv

# Directory containing Inkscape's bundled `inkex` package. Only needed by
# `convert` and `smoke`, since svg_parser.py imports inkex at runtime.
# Override on the command line, e.g. `make convert INKEX_PATH=/usr/share/inkscape/extensions`.
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
INKEX_PATH ?= /Applications/Inkscape.app/Contents/Resources/share/inkscape/extensions
else
INKEX_PATH ?= /usr/share/inkscape/extensions
endif

SVG ?= examples/simple_room.svg
OUT ?= /tmp/floorplan2openscad-out.scad
SCALE ?= 3cm

.PHONY: help
help:
	@echo "Available targets:"
	@echo "  install   - install dev dependencies with uv"
	@echo "  test      - run the pytest suite"
	@echo "  coverage  - run tests with a coverage report (term + html)"
	@echo "  lint      - run ruff check"
	@echo "  format    - run ruff format"
	@echo "  convert   - convert an SVG floor plan to OpenSCAD (SVG=, OUT=, SCALE=)"
	@echo "  validate-inx - check the .inx descriptors and starter template are well-formed XML"
	@echo "  clean     - remove caches and build artifacts"

.PHONY: install
install:
	$(UV) sync --group dev

.PHONY: test
test:
	$(UV) run pytest

.PHONY: coverage
coverage:
	$(UV) run pytest --cov --cov-report=term-missing --cov-report=html

.PHONY: lint
lint:
	$(UV) run ruff check .

.PHONY: format
format:
	$(UV) run ruff format .

# Runs the extension exactly as Inkscape would invoke it: SVG on stdin,
# output path and options as CLI flags. Needs Inkscape installed for the
# bundled `inkex` source (see INKEX_PATH above) plus its pure-pip runtime
# deps, pulled in via the inkex-runtime group.
.PHONY: convert
convert:
	$(UV) sync --group inkex-runtime
	PYTHONPATH="$(INKEX_PATH)" $(UV) run --group inkex-runtime python floorplan2openscad.py \
		--fname="$(OUT)" --base_scale=$(SCALE) < $(SVG)
	@echo "Wrote $(OUT)"

.PHONY: validate-inx
validate-inx:
	xmllint --noout floorplan2openscad.inx floorplan_add_layer.inx templates/floorplan-starter.svg

.PHONY: clean
clean:
	rm -rf .pytest_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -not -path './.venv/*' -exec rm -rf {} +
