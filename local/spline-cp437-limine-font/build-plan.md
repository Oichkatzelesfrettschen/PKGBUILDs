# Build Plan Notes

This package intentionally uses a conservative source policy for v1:

- Spline Sans Mono is rasterized only for printable ASCII `0x20..0x7E`
- Terminus remains the donor for the rest of CP437

## Why this policy exists

Spline Sans Mono does not contain the classic IBM PC terminal glyph set. The
missing portion includes:

- box-drawing glyphs
- block-shading glyphs
- CP437-specific symbols used in text-mode UIs

Using Terminus for non-ASCII bytes keeps Limine visually correct while still
allowing Spline to shape the Latin text.

## Current rasterization strategy

- Pillow rasterizes the Spline TTF to a strict `8x16` cell
- the largest font size that fits all printable ASCII into an `8x16` box is
  selected automatically
- each ASCII glyph is centered into the cell
- donor bytes are copied directly from the Terminus PSF glyph rows

## Future refinement options

- add a FontForge-based strike builder for alternate hinting experiments
- tune per-glyph x/y offsets for letters that still feel too narrow
- evaluate a second Spline-inspired bold variant
- expand non-ASCII Spline substitution only after side-by-side bitmap QA
