#!/usr/bin/env python3
"""make_chip.py — render a "hook chip": the rounded text lozenge that top
creators burn over the first seconds of a reel ("🚨 Nobody is Talking About
This"). Outputs a transparent PNG sized for a 1080x1920 frame, ready to be
overlaid by compose_reel.py (or any editor).

Why a PNG and not ffmpeg drawtext: drawtext can't do rounded chips or color
emoji. PIL + Segoe UI Emoji can.

Usage:
    python make_chip.py --text "🚨 Nobody is Talking About This"
    python make_chip.py --text "WAIT FOR IT..." --style light --fontsize 66

Writes chips/<slug>.png by default and prints the path + pixel size.
Import `render_chip()` to get a PIL image programmatically.
"""
import argparse
import os
import re
import sys
import unicodedata

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
CHIP_DIR = os.path.join(ROOT, "chips")

S = 2  # supersample: draw at 2x, downsample on save for crisp edges

FONTS = "C:/Windows/Fonts/"
TEXT_FONT = "seguibl.ttf"    # Segoe UI Black — same headline face as the cards
EMOJI_FONT = "seguiemj.ttf"  # Segoe UI Emoji — color glyphs

STYLES = {
    # name: (box RGBA, text RGB)
    "dark":  ((16, 16, 16, 242), (255, 255, 255)),
    "light": ((245, 245, 245, 242), (16, 16, 16)),
}

# Emoji and pictographs live (almost) entirely above the BMP's letter blocks.
# Misc symbols / dingbats / arrows start at U+2190; supplemental emoji at
# U+1F000+. Variation selectors and ZWJ ride along with the emoji run.
_EMOJI_JOINERS = {0xFE0E, 0xFE0F, 0x200D, 0x20E3}


def _is_emoji(ch):
    cp = ord(ch)
    if cp in _EMOJI_JOINERS:
        return True
    if 0x1F000 <= cp <= 0x1FAFF or 0x2600 <= cp <= 0x27BF:
        return True
    if 0x2190 <= cp <= 0x2BFF and unicodedata.category(ch) == "So":
        return True
    return False


def _runs(s):
    """Split a string into (text, is_emoji) runs so each gets the right font."""
    out = []
    for ch in s:
        e = _is_emoji(ch)
        if out and out[-1][1] == e:
            out[-1][0] += ch
        else:
            out.append([ch, e])
    return [(t, e) for t, e in out]


def _measure(d, s, ftext, femoji):
    return sum(d.textlength(t, font=(femoji if e else ftext))
               for t, e in _runs(s))


def _draw_mixed(d, x, y, s, ftext, femoji, fill):
    """Draw a mixed text/emoji string at (x, y) with vertical-center anchor."""
    for t, e in _runs(s):
        f = femoji if e else ftext
        if e:
            # embedded_color pulls the glyph's own COLR palette; fill is ignored
            d.text((x, y), t, font=f, anchor="lm", embedded_color=True)
        else:
            d.text((x, y), t, font=f, fill=fill, anchor="lm")
        x += d.textlength(t, font=f)
    return x


def _wrap(d, s, ftext, femoji, maxw):
    words, lines, cur = s.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if _measure(d, t, ftext, femoji) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def render_chip(text, fontsize=58, max_width=920, style="dark",
                pad_x=42, pad_y=26, radius=30, line_gap=8):
    """Render the chip and return a PIL RGBA image (final 1x scale).

    All dimension args are in 1080x1920-frame pixels.
    """
    box_col, txt_col = STYLES[style]
    ftext = ImageFont.truetype(FONTS + TEXT_FONT, fontsize * S)
    femoji = ImageFont.truetype(FONTS + EMOJI_FONT, fontsize * S)

    scratch = Image.new("RGBA", (8, 8))
    d = ImageDraw.Draw(scratch)
    lines = _wrap(d, text.strip(), ftext, femoji, (max_width - 2 * pad_x) * S)
    widths = [_measure(d, ln, ftext, femoji) for ln in lines]
    line_h = int(fontsize * 1.22) * S

    w = int(max(widths)) + 2 * pad_x * S
    h = line_h * len(lines) + (line_gap * S) * (len(lines) - 1) + 2 * pad_y * S

    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius * S, fill=box_col)
    y = pad_y * S + line_h // 2
    for ln, lw in zip(lines, widths):
        _draw_mixed(d, (w - lw) / 2, y, ln, ftext, femoji, txt_col)
        y += line_h + line_gap * S

    return img.resize((w // S, h // S), Image.LANCZOS)


def _slug(text, limit=40):
    s = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()
    return (s[:limit].rstrip("_")) or "chip"


def main():
    ap = argparse.ArgumentParser(description="Render a hook-text chip PNG.")
    ap.add_argument("--text", required=True, help="Chip text (emoji welcome).")
    ap.add_argument("--out", default=None,
                    help="Output PNG path (default chips/<slug>.png).")
    ap.add_argument("--fontsize", type=int, default=58,
                    help="Text size in 1080-frame px (default 58).")
    ap.add_argument("--max-width", type=int, default=920,
                    help="Widest the chip may grow before wrapping (default 920).")
    ap.add_argument("--style", choices=sorted(STYLES), default="dark",
                    help="dark = black box / white text (default); light = inverse.")
    args = ap.parse_args()

    img = render_chip(args.text, fontsize=args.fontsize,
                      max_width=args.max_width, style=args.style)
    out = args.out or os.path.join(CHIP_DIR, _slug(args.text) + ".png")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    img.save(out, "PNG")
    print(f"wrote {out}  ({img.width}x{img.height})")


if __name__ == "__main__":
    main()
