# spline-cp437-limine-font

Package-managed build and artifact bundle for a Limine-compatible CP437 bitmap
font with Spline Sans Mono as the ASCII design source and Terminus as the
donor for the rest of the code page.

## Goal

Produce a hybrid `8x16` CP437 bitmap font suitable for Limine `term_font`,
where:

- Spline Sans Mono supplies printable ASCII bytes `0x20..0x7E`
- Terminus supplies bytes `0x00..0x1F`, `0x7F`, and `0x80..0xFF`

This conservative policy preserves box drawing, block shading, and CP437-
specific terminal art while still giving the menu a Spline-like Latin feel.

## Current package state

This package now provides a complete local build pipeline and installs the
generated font artifacts for package-managed consumers:

- a CP437 source report generator
- a hybrid font builder that emits the final raw Limine bitmap blob
- a BDF export for inspection
- an optional OTB preview target when `fonttosfnt` is present
- a labeled PNG preview sheet and JSON build manifest
- installed font assets under `/usr/share/spline-cp437-limine-font/fonts/`
- installed source reports under `/usr/share/spline-cp437-limine-font/reports/`

You can inspect the installed package directly with pacman:

```bash
pacman -Qi spline-cp437-limine-font
pacman -Ql spline-cp437-limine-font
```

When `cachyos-limine-themes` is already active on the machine, installing or
upgrading this package also restages the live `/boot` font copy and runs a
theme verify pass so Limine does not keep using a stale staged font.

## Current local inputs

- Spline source:
  `/usr/share/fonts/TTF/SplineSansMono-Regular.ttf`
- Donor source:
  `/usr/share/kbd/consolefonts/ter-116n.psf.gz`

## Output artifacts

Running `make build` generates:

- `build/spline-cp437-8x16.bin`
- `build/spline-cp437-8x16.bdf`
- `build/spline-cp437-8x16.otb` when `fonttosfnt` is available
- `build/spline-cp437-sample.png`
- `build/spline-cp437-build.json`

Running `make report` generates:

- `reports/cp437-source-report.json`
- `reports/cp437-source-report.md`

## Quick usage

```bash
cd ~/Github/pkgbuilds/local/spline-cp437-limine-font
make test
```

For a fuller local package regression check:

```bash
cd ~/Github/pkgbuilds/local/spline-cp437-limine-font
make smoke
```

That smoke test verifies:

- raw build artifacts still regenerate
- package metadata still refreshes
- the built package archive still contains the expected scripts, fonts, and reports

The Limine-ready blob is:

- `build/spline-cp437-8x16.bin`

Use it with:

```ini
term_font: boot():/limine/themes/cachyos-official/fonts/spline-cp437-8x16.bin
term_font_size: 8x16
```

Installed package artifacts include:

- `/usr/share/spline-cp437-limine-font/fonts/spline-cp437-8x16.bin`
- `/usr/share/spline-cp437-limine-font/fonts/spline-cp437-8x16.bdf`
- `/usr/share/spline-cp437-limine-font/fonts/spline-cp437-8x16.otb`
- `/usr/share/spline-cp437-limine-font/fonts/spline-cp437-sample.png`
- `/usr/share/spline-cp437-limine-font/fonts/spline-cp437-build.json`
- `/usr/share/spline-cp437-limine-font/reports/cp437-source-report.json`
- `/usr/share/spline-cp437-limine-font/reports/cp437-source-report.md`

The preview sheet groups the most important glyph classes into one artifact:

- ASCII uppercase and lowercase
- digits and punctuation
- box-drawing glyphs
- shading, block, and symbol glyphs
