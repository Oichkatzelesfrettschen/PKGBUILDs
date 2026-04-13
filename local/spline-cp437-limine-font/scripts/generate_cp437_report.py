#!/usr/bin/env python3
import argparse
import gzip
import json
import struct
from pathlib import Path

from fontTools.ttLib import TTFont


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

BOX_BLOCK_BYTES = {
    0xB0, 0xB1, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6, 0xB7, 0xB8, 0xB9, 0xBA,
    0xBB, 0xBC, 0xBD, 0xBE, 0xBF, 0xC0, 0xC1, 0xC2, 0xC3, 0xC4, 0xC5,
    0xC6, 0xC7, 0xC8, 0xC9, 0xCA, 0xCB, 0xCC, 0xCD, 0xCE, 0xCF, 0xD0,
    0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA, 0xDB,
    0xDC, 0xDD, 0xDE, 0xDF,
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spline-font", required=True)
    parser.add_argument("--donor-psf", required=True)
    parser.add_argument("--json-out", required=True)
    parser.add_argument("--markdown-out", required=True)
    return parser.parse_args()


def cp437_codepoint(byte_value: int) -> int:
    if byte_value in CP437_OVERRIDES:
        return CP437_OVERRIDES[byte_value]
    return ord(bytes([byte_value]).decode("cp437"))


def parse_psf_metadata(path: Path):
    with gzip.open(path, "rb") as f:
        magic = f.read(4)
        if len(magic) < 4:
            raise ValueError("PSF file too short")

        if magic[:2] == b"\x36\x04":
            mode = magic[2]
            charsize = magic[3]
            length = 512 if (mode & 0x01) else 256
            has_unicode = bool(mode & 0x02)
            return {
                "format": "PSF1",
                "glyph_count": length,
                "charsize": charsize,
                "width": 8,
                "height": charsize,
                "has_unicode_table": has_unicode,
            }

        if magic == b"\x72\xb5\x4a\x86":
            rest = f.read(28)
            version, headersize, flags, length, charsize, height, width = struct.unpack(
                "<7I", rest
            )
            return {
                "format": "PSF2",
                "version": version,
                "glyph_count": length,
                "charsize": charsize,
                "width": width,
                "height": height,
                "has_unicode_table": bool(flags & 0x01),
                "headersize": headersize,
            }

        raise ValueError("Unsupported PSF format")


def display_char(byte_value: int, codepoint: int) -> str:
    if byte_value == 0x00:
        return "NUL"
    try:
        return chr(codepoint)
    except ValueError:
        return ""


def category_for(byte_value: int) -> str:
    if 0x20 <= byte_value <= 0x7E:
        return "printable_ascii"
    if byte_value in BOX_BLOCK_BYTES:
        return "box_or_block"
    return "cp437_symbol"


def source_for(byte_value: int) -> str:
    if 0x20 <= byte_value <= 0x7E:
        return "spline"
    return "terminus"


def main():
    args = parse_args()

    spline_path = Path(args.spline_font)
    donor_path = Path(args.donor_psf)
    json_out = Path(args.json_out)
    markdown_out = Path(args.markdown_out)

    spline = TTFont(str(spline_path))
    cmap = spline["cmap"].getBestCmap()
    donor_meta = parse_psf_metadata(donor_path)

    rows = []
    policy_spline_count = 0
    policy_donor_count = 0
    coverage_count = 0

    for byte_value in range(256):
        cp = cp437_codepoint(byte_value)
        policy_source = source_for(byte_value)
        has_spline = cp in cmap
        glyph_name = cmap.get(cp)

        if policy_source == "spline":
            policy_spline_count += 1
        else:
            policy_donor_count += 1

        if has_spline:
            coverage_count += 1

        rows.append(
            {
                "byte": byte_value,
                "byte_hex": f"0x{byte_value:02X}",
                "unicode_codepoint": f"U+{cp:04X}",
                "character": display_char(byte_value, cp),
                "category": category_for(byte_value),
                "policy_source": policy_source,
                "spline_has_codepoint": has_spline,
                "spline_glyph_name": glyph_name,
            }
        )

    summary = {
        "spline_font": str(spline_path),
        "donor_psf": str(donor_path),
        "donor_psf_metadata": donor_meta,
        "coverage_totals": {
            "cp437_slots": 256,
            "spline_codepoints_present": coverage_count,
            "spline_codepoints_missing": 256 - coverage_count,
        },
        "policy_totals": {
            "cp437_slots": 256,
            "from_spline": policy_spline_count,
            "from_terminus": policy_donor_count,
        },
    }

    json_out.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2) + "\n")

    md = []
    md.append("# CP437 Source Report")
    md.append("")
    md.append(f"- Spline font: `{spline_path}`")
    md.append(f"- Donor PSF: `{donor_path}`")
    md.append(
        f"- Donor format: `{donor_meta['format']}`, glyphs: `{donor_meta['glyph_count']}`, size: `{donor_meta['width']}x{donor_meta['height']}`"
    )
    md.append(
        f"- Spline Unicode coverage over CP437 visual map: `{coverage_count}` present, `{256 - coverage_count}` missing"
    )
    md.append(f"- Policy source count from Spline: `{policy_spline_count}`")
    md.append(f"- Policy source count from Terminus: `{policy_donor_count}`")
    md.append("")
    md.append("| Byte | Unicode | Char | Category | Policy Source | In Spline | Spline Glyph |")
    md.append("|------|---------|------|----------|---------------|-----------|--------------|")
    for row in rows:
        glyph = row["spline_glyph_name"] or ""
        present = "yes" if row["spline_has_codepoint"] else "no"
        md.append(
            f"| {row['byte_hex']} | {row['unicode_codepoint']} | {row['character']} | {row['category']} | {row['policy_source']} | {present} | {glyph} |"
        )

    markdown_out.write_text("\n".join(md) + "\n")


if __name__ == "__main__":
    main()
