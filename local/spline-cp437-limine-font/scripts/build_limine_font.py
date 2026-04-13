#!/usr/bin/env python3
import argparse
import gzip
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


CP437_OVERRIDES = {
    0x01: 0x263A,
    0x02: 0x263B,
    0x03: 0x2665,
    0x04: 0x2666,
    0x05: 0x2663,
    0x06: 0x2660,
    0x07: 0x2022,
    0x08: 0x25D8,
    0x09: 0x25CB,
    0x0A: 0x25D9,
    0x0B: 0x2642,
    0x0C: 0x2640,
    0x0D: 0x266A,
    0x0E: 0x266B,
    0x0F: 0x263C,
    0x10: 0x25BA,
    0x11: 0x25C4,
    0x12: 0x2195,
    0x13: 0x203C,
    0x14: 0x00B6,
    0x15: 0x00A7,
    0x16: 0x25AC,
    0x17: 0x21A8,
    0x18: 0x2191,
    0x19: 0x2193,
    0x1A: 0x2192,
    0x1B: 0x2190,
    0x1C: 0x221F,
    0x1D: 0x2194,
    0x1E: 0x25B2,
    0x1F: 0x25BC,
    0x7F: 0x2302,
}

SPLINE_START = 0x20
SPLINE_END = 0x7E


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spline-font", required=True)
    parser.add_argument("--donor-psf", required=True)
    parser.add_argument("--out-font", required=True)
    parser.add_argument("--out-bdf", required=True)
    parser.add_argument("--out-preview", required=True)
    parser.add_argument("--out-manifest", required=True)
    return parser.parse_args()


def cp437_codepoint(byte_value: int) -> int:
    if byte_value in CP437_OVERRIDES:
        return CP437_OVERRIDES[byte_value]
    return ord(bytes([byte_value]).decode("cp437"))


def parse_psf_glyphs(path: Path):
    data = gzip.open(path, "rb").read()
    if data[:2] != b"\x36\x04":
        raise ValueError("Only PSF1 donor fonts are supported in this builder")

    mode = data[2]
    charsize = data[3]
    glyph_count = 512 if (mode & 0x01) else 256
    has_unicode = bool(mode & 0x02)
    glyph_data_start = 4
    glyph_data_end = glyph_data_start + glyph_count * charsize
    glyph_blob = data[glyph_data_start:glyph_data_end]

    glyphs = []
    for i in range(glyph_count):
        start = i * charsize
        glyphs.append(list(glyph_blob[start : start + charsize]))

    return {
        "glyphs": glyphs,
        "glyph_count": glyph_count,
        "charsize": charsize,
        "has_unicode_table": has_unicode,
    }


def choose_font_size(font_path: Path, width: int = 8, height: int = 16) -> int:
    best = None
    for size in range(8, 33):
        font = ImageFont.truetype(str(font_path), size=size)
        max_width = 0
        max_height = 0
        for byte_value in range(SPLINE_START, SPLINE_END + 1):
            ch = chr(cp437_codepoint(byte_value))
            bbox = font.getbbox(ch)
            glyph_width = max(0, bbox[2] - bbox[0])
            glyph_height = max(0, bbox[3] - bbox[1])
            max_width = max(max_width, glyph_width)
            max_height = max(max_height, glyph_height)
        if max_width <= width and max_height <= height:
            best = size
    if best is None:
        raise ValueError("No usable Pillow raster size fits printable ASCII into 8x16")
    return best


def rasterize_spline_glyph(font, ch: str, width: int = 8, height: int = 16):
    bbox = font.getbbox(ch)
    glyph_width = max(0, bbox[2] - bbox[0])
    glyph_height = max(0, bbox[3] - bbox[1])
    x = (width - glyph_width) // 2 - bbox[0]
    y = (height - glyph_height) // 2 - bbox[1]

    image = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(image)
    draw.text((x, y), ch, font=font, fill=255)

    rows = []
    for py in range(height):
        row = 0
        for px in range(width):
            if image.getpixel((px, py)) > 0:
                row |= 1 << (7 - px)
        rows.append(row)
    return rows


def build_bdf(glyph_rows):
    lines = [
        "STARTFONT 2.1",
        "FONT -misc-spline-cp437-medium-r-normal--16-160-75-75-c-80-cp437",
        "SIZE 16 75 75",
        "FONTBOUNDINGBOX 8 16 0 0",
        "STARTPROPERTIES 5",
        "FONT_ASCENT 16",
        "FONT_DESCENT 0",
        'SPACING "C"',
        'CHARSET_REGISTRY "CP437"',
        'CHARSET_ENCODING "0"',
        "ENDPROPERTIES",
        f"CHARS {len(glyph_rows)}",
    ]

    for byte_value, rows in enumerate(glyph_rows):
        lines.extend(
            [
                f"STARTCHAR cp{byte_value:02X}",
                f"ENCODING {byte_value}",
                "SWIDTH 500 0",
                "DWIDTH 8 0",
                "BBX 8 16 0 0",
                "BITMAP",
            ]
        )
        lines.extend(f"{row:02X}" for row in rows)
        lines.append("ENDCHAR")

    lines.append("ENDFONT")
    return "\n".join(lines) + "\n"


def render_preview(glyph_rows, out_path: Path):
    reverse_map = {}
    for byte_value in range(256):
        reverse_map[cp437_codepoint(byte_value)] = byte_value

    scale = 4
    cell_w = 8 * scale
    cell_h = 16 * scale
    spacing = scale
    margin = 16
    section_gap = 18
    row_gap = 8

    sections = [
        (
            "ASCII UPPER + LOWER",
            [
                "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                "abcdefghijklmnopqrstuvwxyz",
            ],
            (29, 199, 181),
        ),
        (
            "DIGITS + PUNCTUATION",
            [
                "0123456789",
                "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~",
            ],
            (220, 233, 236),
        ),
        (
            "BOX DRAWING",
            [
                "│─┌┐└┘├┤┬┴┼",
                "║═╔╗╚╝╠╣╦╩╬",
            ],
            (137, 210, 245),
        ),
        (
            "SHADING + BLOCKS",
            [
                "░▒▓█▄▀■",
                "◄►▲▼○●☺☻",
            ],
            (245, 206, 119),
        ),
    ]

    label_font = ImageFont.load_default()
    label_bbox = label_font.getbbox("ASCII UPPER + LOWER")
    label_h = max(0, label_bbox[3] - label_bbox[1])

    max_line_len = max(len(line) for _, lines, _ in sections for line in lines)
    width = margin * 2 + max_line_len * (cell_w + spacing)

    height = margin
    for _, lines, _ in sections:
        height += label_h + row_gap
        height += len(lines) * (cell_h + spacing)
        height += section_gap
    height += margin - section_gap

    image = Image.new("RGB", (width, height), "#081016")
    draw = ImageDraw.Draw(image)
    on_color = (220, 233, 236)
    heading_color = (160, 177, 190)

    y = margin
    for title, lines, glyph_color in sections:
        draw.text((margin, y), title, font=label_font, fill=heading_color)
        y += label_h + row_gap
        for line in lines:
            x0 = margin
            y0 = y
            for col_index, ch in enumerate(line):
                cp = ord(ch)
                byte_value = reverse_map.get(cp)
                if byte_value is None and cp < 256:
                    byte_value = cp
                if byte_value is None:
                    continue
                rows = glyph_rows[byte_value]
                color = glyph_color if ch != " " else on_color
                for py, row in enumerate(rows):
                    for px in range(8):
                        if row & (1 << (7 - px)):
                            for sy in range(scale):
                                for sx in range(scale):
                                    image.putpixel(
                                        (
                                            x0 + col_index * (cell_w + spacing) + px * scale + sx,
                                            y0 + py * scale + sy,
                                        ),
                                        color,
                                    )
            y += cell_h + spacing
        y += section_gap

    image.save(out_path)


def main():
    args = parse_args()

    spline_path = Path(args.spline_font)
    donor_path = Path(args.donor_psf)
    out_font = Path(args.out_font)
    out_bdf = Path(args.out_bdf)
    out_preview = Path(args.out_preview)
    out_manifest = Path(args.out_manifest)

    donor = parse_psf_glyphs(donor_path)
    if donor["glyph_count"] < 256 or donor["charsize"] != 16:
        raise ValueError("Donor font must provide at least 256 glyphs of size 8x16")

    font_size = choose_font_size(spline_path)
    spline_font = ImageFont.truetype(str(spline_path), size=font_size)

    glyph_rows = []
    manifest_rows = []
    spline_count = 0
    donor_count = 0

    for byte_value in range(256):
        if SPLINE_START <= byte_value <= SPLINE_END:
            ch = chr(cp437_codepoint(byte_value))
            rows = rasterize_spline_glyph(spline_font, ch)
            source = "spline"
            spline_count += 1
        else:
            rows = donor["glyphs"][byte_value]
            source = "terminus"
            donor_count += 1

        glyph_rows.append(rows)
        manifest_rows.append(
            {
                "byte": f"0x{byte_value:02X}",
                "unicode_codepoint": f"U+{cp437_codepoint(byte_value):04X}",
                "source": source,
                "rows_hex": [f"{row:02X}" for row in rows],
            }
        )

    out_font.parent.mkdir(parents=True, exist_ok=True)
    out_bdf.parent.mkdir(parents=True, exist_ok=True)
    out_preview.parent.mkdir(parents=True, exist_ok=True)
    out_manifest.parent.mkdir(parents=True, exist_ok=True)

    raw = bytes(row for rows in glyph_rows for row in rows)
    out_font.write_bytes(raw)
    out_bdf.write_text(build_bdf(glyph_rows))
    render_preview(glyph_rows, out_preview)

    manifest = {
        "spline_font": str(spline_path),
        "donor_psf": str(donor_path),
        "policy": {
            "spline_byte_ranges": ["0x20-0x7E"],
            "terminus_byte_ranges": ["0x00-0x1F", "0x7F-0xFF"],
        },
        "font": {
            "glyph_count": 256,
            "glyph_width": 8,
            "glyph_height": 16,
            "blob_size_bytes": len(raw),
            "chosen_spline_point_size": font_size,
        },
        "totals": {
            "from_spline": spline_count,
            "from_terminus": donor_count,
        },
        "rows": manifest_rows,
    }
    out_manifest.write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
