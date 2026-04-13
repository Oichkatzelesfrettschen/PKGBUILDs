PKGNAME := spline-cp437-limine-font
REPORT_DIR := reports
BUILD_DIR := build
SCRIPT_DIR := scripts
SPLINE_FONT ?= /usr/share/fonts/TTF/SplineSansMono-Regular.ttf
DONOR_PSF ?= /usr/share/kbd/consolefonts/ter-116n.psf.gz

.PHONY: all test report build smoke clean

all: report build

report:
	@mkdir -p "$(REPORT_DIR)"
	@python "$(SCRIPT_DIR)/generate_cp437_report.py" \
		--spline-font "$(SPLINE_FONT)" \
		--donor-psf "$(DONOR_PSF)" \
		--json-out "$(REPORT_DIR)/cp437-source-report.json" \
		--markdown-out "$(REPORT_DIR)/cp437-source-report.md"

build:
	@mkdir -p "$(BUILD_DIR)"
	@python "$(SCRIPT_DIR)/build_limine_font.py" \
		--spline-font "$(SPLINE_FONT)" \
		--donor-psf "$(DONOR_PSF)" \
		--out-font "$(BUILD_DIR)/spline-cp437-8x16.bin" \
		--out-bdf "$(BUILD_DIR)/spline-cp437-8x16.bdf" \
		--out-preview "$(BUILD_DIR)/spline-cp437-sample.png" \
		--out-manifest "$(BUILD_DIR)/spline-cp437-build.json"
	@if command -v fonttosfnt >/dev/null 2>&1; then \
		fonttosfnt -r -o "$(BUILD_DIR)/spline-cp437-8x16.otb" "$(BUILD_DIR)/spline-cp437-8x16.bdf"; \
	fi

test: report build
	@python -c 'import json; from pathlib import Path; \
font_path = Path("build/spline-cp437-8x16.bin"); \
manifest_path = Path("build/spline-cp437-build.json"); \
report_path = Path("reports/cp437-source-report.json"); \
assert font_path.exists(), f"missing {font_path}"; \
assert manifest_path.exists(), f"missing {manifest_path}"; \
assert report_path.exists(), f"missing {report_path}"; \
assert font_path.stat().st_size == 4096, font_path.stat().st_size; \
manifest = json.loads(manifest_path.read_text()); \
assert manifest["font"]["glyph_count"] == 256; \
assert manifest["font"]["glyph_height"] == 16; \
assert manifest["font"]["glyph_width"] == 8; \
assert manifest["policy"]["spline_byte_ranges"] == ["0x20-0x7E"]; \
assert manifest["totals"]["from_spline"] == 95; \
assert manifest["totals"]["from_terminus"] == 161; \
report = json.loads(report_path.read_text()); \
assert report["summary"]["policy_totals"]["from_spline"] == 95; \
assert report["summary"]["policy_totals"]["from_terminus"] == 161; \
print("Font blob, manifest, and report verified.")'

smoke:
	@bash ./tests/smoke-package-artifacts.sh

clean:
	rm -rf "$(REPORT_DIR)" "$(BUILD_DIR)"
