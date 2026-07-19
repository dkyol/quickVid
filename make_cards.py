#!/usr/bin/env python3
"""Build 9:16 infographic cards (1080x1920) to use as reel frames.

Two halves:

  TOOLKIT  - generic, reusable. Background, header/footer chrome, panels,
             stat rows, tapered-limb + spline drawing primitives, a small
             map projection, and an icon set. Reuse this for any deck.
  DECK     - the cards for one specific reel. Replace this half per video;
             each card_*() returns an RGBA image at 2x and is downsampled
             on save.

Usage:  python make_cards.py [output_dir]

Notes for reuse are in ReadME.MD under "Infographic / data cards".
"""
import math
import os
import random
import sys
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

# ===================================================================
# TOOLKIT
# ===================================================================

S = 2                      # supersample factor; draw at 2x, downsample on save
W, H = 1080, 1920          # 9:16, the size make_reel.py expects
CW, CH = W * S, H * S

# Palette. Swap these for a different subject; everything below reads them.
BG        = (11, 13, 16)
BG_WARM   = (26, 16, 14)
INK       = (245, 242, 237)
MUTED     = (138, 145, 158)
DIM       = (80, 86, 96)
ORANGE    = (255, 107, 26)
RED       = (230, 50, 32)
EMBER     = (255, 176, 32)
PANEL     = (22, 25, 30)
PANEL_ED  = (42, 47, 56)
TISSUE    = (58, 26, 22)

FONTS = "C:/Windows/Fonts/"
BLACK_F = "seguibl.ttf"     # Segoe UI Black - headlines
BOLD_F  = "arialbd.ttf"
REG_F   = "arial.ttf"


def font(name, size):
    return ImageFont.truetype(FONTS + name, int(size * S))


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# ---------------------------------------------------------------- text
def text(d, xy, s, f, fill, anchor="la", spacing=0):
    """Draw text; `spacing` adds manual letter-spacing (PIL has none)."""
    if not spacing:
        d.text(xy, s, font=f, fill=fill, anchor=anchor)
        return
    sp = spacing * S
    widths = [d.textlength(ch, font=f) for ch in s]
    total = sum(widths) + sp * (len(s) - 1)
    x, y = xy
    if anchor[0] == "m":
        x -= total / 2
    elif anchor[0] == "r":
        x -= total
    va = "a" if len(anchor) < 2 else anchor[1]
    for ch, wch in zip(s, widths):
        d.text((x, y), ch, font=f, fill=fill, anchor="l" + va)
        x += wch + sp


def wrap(d, s, f, maxw):
    words, lines, cur = s.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def para(d, x, y, s, f, fill, maxw, lh):
    """Wrapped paragraph. Returns the y below the last line."""
    for ln in wrap(d, s, f, maxw):
        text(d, (x, y), ln, f, fill)
        y += lh
    return y


# ---------------------------------------------------------------- geometry
def catmull(pts, n=14, closed=True):
    """Smooth a control polygon into a spline. Use for organic shapes."""
    P = list(pts)
    ext = ([P[-1]] + P + [P[0], P[1]]) if closed else \
          ([P[0]] + P + [P[-1], P[-1]])
    out = []
    for i in range(len(ext) - 3):
        p0, p1, p2, p3 = ext[i:i + 4]
        for j in range(n):
            t = j / n
            t2, t3 = t * t, t * t * t
            x = 0.5 * (2 * p1[0] + (-p0[0] + p2[0]) * t +
                       (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
                       (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * (2 * p1[1] + (-p0[1] + p2[1]) * t +
                       (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
                       (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append((x, y))
    if not closed:
        out.append(P[-1])
    return out


def taper(d, pts, w0, w1, color):
    """Limb-like stroke: a smooth polyline that thins from w0 to w1.

    Reads as an athletic silhouette where a constant-width line reads as a
    stick figure. Ends are rounded so joints between limbs merge cleanly.
    """
    P = catmull(pts, n=10, closed=False)
    seg = [0.0]
    for i in range(1, len(P)):
        seg.append(seg[-1] + math.hypot(P[i][0] - P[i - 1][0],
                                        P[i][1] - P[i - 1][1]))
    total = seg[-1] or 1.0
    left, right = [], []
    for i, p in enumerate(P):
        j = min(i + 1, len(P) - 1)
        k = max(i - 1, 0)
        tx, ty = P[j][0] - P[k][0], P[j][1] - P[k][1]
        L = math.hypot(tx, ty) or 1
        nx, ny = -ty / L, tx / L
        hw = (w0 + (w1 - w0) * (seg[i] / total)) / 2
        left.append((p[0] + nx * hw, p[1] + ny * hw))
        right.append((p[0] - nx * hw, p[1] - ny * hw))
    d.polygon(left + right[::-1], fill=color)
    for p, r in ((P[0], w0 / 2), (P[-1], w1 / 2)):
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=color)


def masked(img, draw_fn, mask_poly):
    """Run draw_fn on a scratch layer, clipped to mask_poly, then composite.

    Keeps detail (bronchi, texture, hatching) strictly inside a shape.
    """
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(lay, "RGBA"))
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).polygon(mask_poly, fill=255)
    lay.putalpha(ImageChops.multiply(lay.getchannel("A"), m))
    img.alpha_composite(lay)


# ---------------------------------------------------------------- chrome
def glow(img, box, color, radius=90, alpha=110):
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).ellipse(box, fill=color + (alpha,))
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(radius * S)))


def background(seed=0):
    """Near-black canvas with a warm vertical wash, smoke wisps and embers."""
    rnd = random.Random(seed)
    img = Image.new("RGBA", (CW, CH), BG + (255,))
    d = ImageDraw.Draw(img)

    for y in range(CH):
        t = (y / CH) ** 1.7
        d.line([(0, y), (CW, y)], fill=lerp(BG, BG_WARM, t * 0.9))

    lay = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    for _ in range(16):
        x0 = rnd.uniform(-0.15, 1.15) * CW
        y0 = rnd.uniform(0.0, 1.0) * CH
        amp = rnd.uniform(40, 150) * S
        length = rnd.uniform(0.25, 0.7) * CH
        col = ORANGE if rnd.random() < 0.55 else RED
        pts = [(x0 + math.sin(i / 40 * math.pi * rnd.uniform(1.2, 2.4) +
                              rnd.random()) * amp, y0 - length * i / 40)
               for i in range(41)]
        ld.line(pts, fill=col + (int(rnd.uniform(10, 24)),),
                width=int(rnd.uniform(10, 46) * S), joint="curve")
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(34 * S)))

    for _ in range(52):
        x, y = rnd.uniform(0, CW), rnd.uniform(0.3, 1.0) * CH
        r = rnd.uniform(1.0, 3.0) * S
        col = EMBER if rnd.random() < 0.6 else ORANGE
        d.ellipse([x - r, y - r, x + r, y + r],
                  fill=col + (int(rnd.uniform(22, 90)),))
    return img


def panel(d, box, radius=26):
    d.rounded_rectangle(box, radius=radius * S, fill=PANEL + (255,),
                        outline=PANEL_ED + (255,), width=int(2 * S))


def header(d, num, eyebrow, title, maxw=900):
    """Index chip + eyebrow + headline + accent rule. Top ~300px of the card."""
    x = 80 * S
    d.rounded_rectangle([x, 96 * S, 142 * S, 142 * S], radius=10 * S,
                        fill=ORANGE + (255,))
    text(d, (111 * S, 119 * S), num, font(BLACK_F, 26), (12, 12, 12),
         anchor="mm")
    text(d, (162 * S, 119 * S), eyebrow, font(BOLD_F, 25), ORANGE,
         anchor="lm", spacing=3.4)
    f = font(BLACK_F, 76)
    y = 190 * S
    for ln in wrap(d, title, f, maxw * S):
        text(d, (x, y), ln, f, INK)
        y += 86 * S
    d.rounded_rectangle([x, y + 16 * S, x + 118 * S, y + 24 * S],
                        radius=4 * S, fill=RED + (255,))


def footer(d, s):
    """Bottom-anchored source note. Wraps, so it never runs off-canvas."""
    f = font(REG_F, 20)
    lines = wrap(d, s, f, 900 * S)
    lh = 27 * S
    y = 1852 * S - lh * len(lines)
    d.line([(80 * S, y - 22 * S), (1000 * S, y - 22 * S)],
           fill=(36, 40, 47, 255), width=int(1.5 * S))
    for ln in lines:
        text(d, (80 * S, y), ln, f, DIM)
        y += lh


def stat_row(d, y, items, x0=80, x1=1000):
    """Evenly spaced big-number/label pairs. Use '|' to split label lines."""
    span = (x1 - x0) / len(items)
    for i, (big, lab) in enumerate(items):
        cx = (x0 + span * (i + 0.5)) * S
        text(d, (cx, y * S), big, font(BLACK_F, 54), EMBER, anchor="ma")
        for j, ln in enumerate(lab.split("|")):
            text(d, (cx, (y + 70 + j * 26) * S), ln, font(BOLD_F, 21),
                 MUTED, anchor="ma", spacing=1.6)
        if i:
            d.line([((x0 + span * i) * S, (y + 6) * S),
                    ((x0 + span * i) * S, (y + 106) * S)],
                   fill=(48, 53, 62, 255), width=int(1.5 * S))


# ---------------------------------------------------------------- maps
NA = [
    (-168, 66), (-166, 60), (-160, 58), (-152, 59), (-146, 60), (-136, 59),
    (-130, 54), (-125, 49), (-124, 43), (-121, 36), (-117, 32), (-114, 28),
    (-110, 23), (-105, 19), (-98, 16), (-92, 15), (-88, 16), (-88, 21),
    (-91, 19), (-95, 19), (-97, 22), (-97, 26), (-94, 29), (-89, 29),
    (-84, 30), (-82, 26), (-80, 25), (-81, 31), (-76, 35), (-75, 38),
    (-73, 41), (-70, 42), (-66, 44), (-64, 46), (-59, 46), (-56, 50),
    (-56, 53), (-61, 57), (-64, 60), (-70, 62), (-78, 62), (-77, 66),
    (-70, 68), (-80, 70), (-90, 70), (-100, 69), (-112, 68), (-125, 70),
    (-135, 69), (-150, 71), (-160, 71),
]
HUDSON = [(-94, 59), (-88, 63), (-81, 62), (-78, 57), (-80, 52), (-86, 51),
          (-91, 54)]
CANADA = [
    (-141, 69.5), (-141, 60), (-136, 59), (-130, 54), (-125, 49), (-95, 49),
    (-88, 48), (-84, 46), (-82, 42), (-79, 43), (-76, 45), (-71, 45),
    (-67, 47), (-64, 46), (-59, 46), (-56, 50), (-56, 53), (-61, 57),
    (-64, 60), (-70, 62), (-78, 62), (-77, 66), (-70, 68), (-80, 70),
    (-90, 70), (-100, 69), (-112, 68), (-125, 70), (-135, 69),
]
DC = (-77.0, 38.9)
FIRE_PTS = [(-115, 57), (-106, 56), (-97, 55), (-88, 51), (-75, 51),
            (-124, 55), (-68, 52), (-110, 62)]


class Proj:
    """Equirectangular projection fitted to a target box, aspect preserved."""

    def __init__(self, pts, box):
        lons, lats = [p[0] for p in pts], [p[1] for p in pts]
        self.lon0, self.lon1 = min(lons), max(lons)
        self.lat0, self.lat1 = min(lats), max(lats)
        self.k = math.cos(math.radians((self.lat0 + self.lat1) / 2))
        bw, bh = (self.lon1 - self.lon0) * self.k, self.lat1 - self.lat0
        x0, y0, x1, y1 = box
        self.s = min((x1 - x0) / bw, (y1 - y0) / bh)
        self.ox = x0 + ((x1 - x0) - bw * self.s) / 2
        self.oy = y0 + ((y1 - y0) - bh * self.s) / 2

    def __call__(self, lon, lat):
        return (self.ox + (lon - self.lon0) * self.k * self.s,
                self.oy + (self.lat1 - lat) * self.s)


def basemap(d, p, land=(28, 32, 38), can=(92, 29, 19)):
    d.polygon([p(*q) for q in NA], fill=land + (255,),
              outline=(52, 58, 66, 255), width=int(2 * S))
    d.polygon([p(*q) for q in CANADA], fill=can + (255,),
              outline=ORANGE + (230,), width=int(3 * S))
    d.polygon(catmull([p(*q) for q in HUDSON], 10), fill=(14, 17, 21, 255))


def arrow(d, p0, p1, color, width=7, head=26, alpha=255, curve=0.22):
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    cx = (x0 + x1) / 2 - dy * curve
    cy = (y0 + y1) / 2 + dx * curve
    pts = []
    for i in range(41):
        t = i / 40
        u = 1 - t
        pts.append((u * u * x0 + 2 * u * t * cx + t * t * x1,
                    u * u * y0 + 2 * u * t * cy + t * t * y1))
    d.line(pts, fill=color + (alpha,), width=int(width * S), joint="curve")
    ax, ay = pts[-1]
    ang = math.atan2(ay - pts[-4][1], ax - pts[-4][0])
    h = head * S
    d.polygon([(ax, ay),
               (ax - h * math.cos(ang - 0.42), ay - h * math.sin(ang - 0.42)),
               (ax - h * math.cos(ang + 0.42), ay - h * math.sin(ang + 0.42))],
              fill=color + (alpha,))


# ---------------------------------------------------------------- icons
def icon_sun(d, cx, cy, r, color=ORANGE):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color + (255,),
              width=int(6 * S))
    d.ellipse([cx - r * .5, cy - r * .5, cx + r * .5, cy + r * .5],
              fill=color + (255,))
    for i in range(8):
        a = i * math.pi / 4
        d.line([(cx + math.cos(a) * r * 1.34, cy + math.sin(a) * r * 1.34),
                (cx + math.cos(a) * r * 1.74, cy + math.sin(a) * r * 1.74)],
               fill=color + (255,), width=int(6 * S))


def icon_drought(d, cx, cy, r, color=ORANGE):
    top = cy + r * .1
    d.arc([cx - r * 1.55, top - r * .6, cx + r * 1.55, top + r * .6],
          200, 340, fill=color + (255,), width=int(6 * S))
    for cr in ([(-.9, .2), (-.68, .6), (-.95, 1.0)],
               [(-.2, .16), (-.04, .64), (-.34, 1.08)],
               [(.5, .18), (.4, .56), (.76, 1.0)],
               [(1.0, .26), (1.16, .66)]):
        d.line([(cx + a * r, top + b * r) for a, b in cr],
               fill=color + (210,), width=int(5 * S), joint="curve")
    dx, dy, dr = cx, cy - r * 1.1, r * .5
    d.polygon([(dx, dy - dr * 1.5), (dx + dr * .92, dy + dr * .35),
               (dx, dy + dr * 1.05), (dx - dr * .92, dy + dr * .35)],
              outline=color + (255,), width=int(5 * S))
    d.line([(dx - dr * 1.35, dy + dr * 1.25), (dx + dr * 1.35, dy - dr * 1.35)],
           fill=RED + (255,), width=int(6 * S))


def icon_bolt(d, cx, cy, r, color=EMBER):
    p = [(.10, -1.0), (-.62, .12), (-.12, .12), (-.34, 1.0),
         (.62, -.16), (.10, -.16)]
    d.polygon([(cx + a * r, cy + b * r) for a, b in p], fill=color + (255,))


def icon_flame(d, cx, cy, r, color=ORANGE, inner=EMBER):
    ctrl = [(0, -1.30), (.46, -.62), (.62, -.05), (.50, .58), (0, .84),
            (-.50, .58), (-.62, -.05), (-.46, -.62)]
    d.polygon(catmull([(cx + a * r, cy + b * r) for a, b in ctrl]),
              fill=color + (255,))
    d.polygon(catmull([(cx + a * r * .54, cy + r * .22 + b * r * .54)
                       for a, b in ctrl]), fill=inner + (255,))


# Anatomical lobe outline: narrow apex, convex lateral border, wide base,
# concave medial border (cardiac notch). Mirrored for the other side.
_LOBE = [(.16, -.60), (.44, -.72), (.78, -.44), (.98, .02), (1.00, .52),
         (.82, .86), (.46, .92), (.34, .50), (.30, .00), (.22, -.32)]


def icon_lungs(img, cx, cy, r, color=ORANGE, fill_col=TISSUE):
    """Lungs with a recursive bronchial tree clipped inside each lobe."""
    d = ImageDraw.Draw(img, "RGBA")
    d.line([(cx, cy - r * 1.18), (cx, cy - r * .74)], fill=color + (255,),
           width=int(11 * S))

    for sgn in (-1, 1):
        lobe = catmull([(cx + sgn * a * r, cy + b * r) for a, b in _LOBE])
        d.polygon(lobe, fill=fill_col + (255,), outline=color + (255,),
                  width=int(7 * S))
        hilum = (cx + sgn * r * .30, cy - r * .02)
        d.line([(cx, cy - r * .72), hilum], fill=color + (255,),
               width=int(8 * S))

        def tree(ld, p, ang, length, width, depth):
            q = (p[0] + math.cos(ang) * length, p[1] + math.sin(ang) * length)
            ld.line([p, q], fill=color + (215,), width=max(int(width), 1))
            if depth:
                for da in (-0.52, 0.46):
                    tree(ld, q, ang + da, length * .74, width * .68, depth - 1)

        # Grow the tree from the hilum outward; the mask trims any overshoot.
        masked(img, lambda ld, h=hilum, s=sgn: (
            tree(ld, h, math.radians(20) * s if s > 0 else math.pi - math.radians(20),
                 r * .34, 7 * S, 4),
            tree(ld, h, math.radians(-38) * s if s > 0 else math.pi + math.radians(38),
                 r * .28, 6 * S, 3),
            tree(ld, h, math.radians(76) * s if s > 0 else math.pi - math.radians(76),
                 r * .30, 6 * S, 3),
        ), lobe)


def icon_runner(d, cx, cy, r, color=INK):
    """Running silhouette built from tapered limbs, leaning into the stride."""
    c = color + (255,)
    hip = (cx - r * .12, cy + r * .18)
    sho = (cx + r * .18, cy - r * .50)

    # trailing leg first so the near leg overlaps it
    taper(d, [hip, (cx - r * .52, cy + r * .44), (cx - r * .80, cy + r * .74)],
          r * .30, r * .13, c)
    taper(d, [(cx - r * .80, cy + r * .74), (cx - r * 1.00, cy + r * .70)],
          r * .13, r * .09, c)
    taper(d, [sho, (cx - r * .42, cy - r * .30), (cx - r * .70, cy - r * .58)],
          r * .19, r * .10, c)

    taper(d, [sho, hip], r * .38, r * .30, c)                      # torso
    taper(d, [hip, (cx + r * .46, cy + r * .30), (cx + r * .30, cy + r * .80)],
          r * .30, r * .13, c)                                     # lead leg
    taper(d, [(cx + r * .30, cy + r * .80), (cx + r * .54, cy + r * .86)],
          r * .13, r * .09, c)                                     # lead foot
    taper(d, [sho, (cx + r * .64, cy - r * .34), (cx + r * .54, cy + r * .06)],
          r * .19, r * .10, c)                                     # lead arm

    hr = r * .19
    hx, hy = cx + r * .36, cy - r * .84
    d.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=c)


def icon_beaver(d, cx, cy, r, color=ORANGE):
    body = catmull([(cx + a * r, cy + b * r) for a, b in
                    [(-.02, -.46), (.36, -.36), (.66, -.04), (.68, .30),
                     (.40, .56), (-.16, .60), (-.50, .42), (-.58, .04),
                     (-.40, -.30)]])
    tail = catmull([(cx + a * r, cy + b * r) for a, b in
                    [(.58, .22), (1.02, .06), (1.42, .22), (1.34, .54),
                     (.86, .64), (.62, .52)]], 8)
    d.polygon(tail, fill=(46, 22, 18, 255), outline=color + (255,),
              width=int(5 * S))
    for i in (1, 2, 3):
        t = i / 4
        d.line([(cx + r * (.66 + .70 * t), cy + r * (.20 - .02 * t)),
                (cx + r * (.68 + .66 * t), cy + r * (.56 + .02 * t))],
               fill=color + (140,), width=int(3 * S))
    d.polygon(body, fill=TISSUE + (255,), outline=color + (255,),
              width=int(6 * S))
    hx, hy, hr = cx - r * .66, cy - r * .40, r * .32
    d.ellipse([hx + hr * .16, hy - hr * 1.34, hx + hr * .90, hy - hr * .60],
              fill=TISSUE + (255,), outline=color + (255,), width=int(4 * S))
    d.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=TISSUE + (255,),
              outline=color + (255,), width=int(6 * S))
    d.ellipse([hx - hr * .56, hy - hr * .26, hx - hr * .22, hy + hr * .08],
              fill=color + (255,))
    d.ellipse([hx - hr * 1.12, hy + hr * .22, hx - hr * .74, hy + hr * .58],
              fill=color + (255,))
    d.rectangle([hx - hr * .72, hy + hr * .58, hx - hr * .40, hy + hr * 1.06],
                fill=EMBER + (255,))


def icon_hands_fire(d, cx, cy, r, color=ORANGE):
    icon_flame(d, cx, cy - r * .28, r * .50, color=RED, inner=EMBER)
    for sgn in (-1, 1):
        pts = [(cx + sgn * math.sin(math.pi * (.06 + .88 * i / 24)) * r * 1.04,
                cy + r * .40 -
                math.cos(math.pi * (.06 + .88 * i / 24)) * r * .56)
               for i in range(25)]
        d.line(pts, fill=color + (255,), width=int(8 * S), joint="curve")
        d.line([(cx + sgn * r * 1.00, cy + r * .76),
                (cx + sgn * r * 1.18, cy + r * 1.04)],
               fill=color + (255,), width=int(8 * S))


def aqi_bar(d, x0, y, x1, h, marker_label):
    bands = [("0", (46, 160, 96)), ("50", (222, 190, 60)),
             ("100", (240, 140, 40)), ("150", (226, 62, 44)),
             ("200", (150, 60, 160)), ("300+", (120, 40, 48))]
    seg = (x1 - x0) / len(bands)
    for i, (lab, col) in enumerate(bands):
        a, b = x0 + seg * i, x0 + seg * (i + 1)
        d.rounded_rectangle([a + 3 * S, y, b - 3 * S, y + h], radius=h * .34,
                            fill=col + (255,))
        text(d, ((a + b) / 2, y + h + 14 * S), lab, font(BOLD_F, 21), MUTED,
             anchor="ma")
    mx = x0 + seg * 4.6
    d.polygon([(mx, y - 12 * S), (mx - 13 * S, y - 34 * S),
               (mx + 13 * S, y - 34 * S)], fill=INK + (255,))
    text(d, (mx, y - 78 * S), marker_label, font(BLACK_F, 24), INK,
         anchor="ma", spacing=1.5)


# ===================================================================
# DECK - replace this half per video
# ===================================================================
# Copy written to read as current: no year on any card face, so the deck
# doesn't date. Years live only in the source footers.

def card1():
    img = background(seed=11)
    glow(img, [-260 * S, 260 * S, 640 * S, 1120 * S], RED, 150, 44)
    d = ImageDraw.Draw(img, "RGBA")
    header(d, "01", "THE CAUSE", "What Started the Fires?")

    p = Proj(NA, (548 * S, 392 * S, 1012 * S, 812 * S))
    basemap(d, p)
    for lon, lat in FIRE_PTS:
        x, y = p(lon, lat)
        d.ellipse([x - 7 * S, y - 7 * S, x + 7 * S, y + 7 * S],
                  fill=EMBER + (255,))
        d.ellipse([x - 15 * S, y - 15 * S, x + 15 * S, y + 15 * S],
                  outline=EMBER + (105,), width=int(2 * S))
    text(d, (780 * S, 838 * S), "CANADA", font(BLACK_F, 26), ORANGE,
         anchor="ma", spacing=4)

    y = 430
    for name, sub, ic in (
        ("EXTREME HEAT", "Spring ran far hotter than normal", icon_sun),
        ("DEEP DROUGHT", "Forests dried to tinder", icon_drought),
        ("LIGHTNING", "Ignited most of the area burned", icon_bolt),
    ):
        cx, cy = 148 * S, (y + 46) * S
        d.ellipse([cx - 58 * S, cy - 58 * S, cx + 58 * S, cy + 58 * S],
                  fill=(26, 20, 20, 255), outline=(58, 40, 34, 255),
                  width=int(2 * S))
        ic(d, cx, cy, 30 * S)
        text(d, (232 * S, (y + 12) * S), name, font(BLACK_F, 34), INK)
        para(d, 232 * S, (y + 58) * S, sub, font(REG_F, 24), MUTED,
             290 * S, 32 * S)
        y += 210

    panel(d, [80 * S, 1150 * S, 1000 * S, 1396 * S])
    text(d, (540 * S, 1192 * S), "A RECORD WITHOUT PRECEDENT",
         font(BLACK_F, 26), ORANGE, anchor="ma", spacing=3)
    stat_row(d, 1254, [("6,600+", "FIRES"), ("~18M", "HECTARES|BURNED"),
                       ("2×", "THE PREVIOUS|RECORD")])
    para(d, 80 * S, 1470 * S,
         "Heat and drought loaded the gun. Lightning pulled the trigger — "
         "across a whole continent at once.",
         font(BOLD_F, 33), INK, 900 * S, 46 * S)
    footer(d, "Sources: Natural Resources Canada; CIFFC season totals for the "
              "2023 Canadian wildfire season. Area-burned estimates range "
              "16.5–18.5M hectares by source.")
    return img


def card2():
    img = background(seed=23)
    glow(img, [120 * S, 320 * S, 980 * S, 1040 * S], RED, 170, 50)
    d = ImageDraw.Draw(img, "RGBA")
    header(d, "02", "THE SMOKE JOURNEY", "How Smoke Reaches D.C.")

    p = Proj(NA, (110 * S, 424 * S, 990 * S, 1184 * S))
    basemap(d, p, can=(88, 28, 18))

    lay = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    for i in range(9):
        t = i / 8
        a, b = p(-108 + t * 22, 57 - t * 2), p(-79 - t * 3, 39 + t * 3)
        ld.line([a, ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 - 40 * S), b],
                fill=ORANGE + (44,), width=int(64 * S), joint="curve")
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(26 * S)))

    for lon, lat in FIRE_PTS:
        x, y = p(lon, lat)
        d.ellipse([x - 8 * S, y - 8 * S, x + 8 * S, y + 8 * S],
                  fill=EMBER + (255,))
    for src in ((-104, 56), (-92, 54), (-80, 52)):
        arrow(d, p(*src), p(-77.6, 40.2), ORANGE, width=6, head=24,
              alpha=225, curve=0.16)

    dx, dy = p(*DC)
    d.ellipse([dx - 34 * S, dy - 34 * S, dx + 34 * S, dy + 34 * S],
              outline=INK + (90,), width=int(2 * S))
    d.ellipse([dx - 13 * S, dy - 13 * S, dx + 13 * S, dy + 13 * S],
              fill=INK + (255,))
    text(d, (dx - 52 * S, dy - 14 * S), "WASHINGTON, D.C.",
         font(BLACK_F, 26), INK, anchor="ra", spacing=1.6)
    text(d, (dx - 52 * S, dy + 20 * S), "Orange skies at noon",
         font(REG_F, 23), MUTED, anchor="ra")

    panel(d, [80 * S, 1250 * S, 1000 * S, 1496 * S])
    text(d, (540 * S, 1292 * S), "A CONVEYOR BELT IN THE SKY",
         font(BLACK_F, 26), ORANGE, anchor="ma", spacing=3)
    stat_row(d, 1354, [("1,500+", "MILES|TRAVELED"),
                       ("CODE RED", "AIR QUALITY|ALERTS"),
                       ("100M+", "AMERICANS|UNDER ALERTS")])
    para(d, 80 * S, 1570 * S,
         "A stalled low over the Northeast wraps the jet stream south — "
         "funneling smoke straight down the East Coast.",
         font(BOLD_F, 33), INK, 900 * S, 46 * S)
    footer(d, "Sources: NOAA/NWS smoke-transport analyses; AirNow; D.C. DOEE "
              "Code Red advisory, June 2023. Reported peak AQI varies by "
              "monitor and source.")
    return img


def card3():
    img = background(seed=37)
    glow(img, [200 * S, 380 * S, 900 * S, 960 * S], RED, 150, 48)
    icon_lungs(img, 366 * S, 630 * S, 158 * S)
    d = ImageDraw.Draw(img, "RGBA")
    header(d, "03", "THE TOLL", "How Smoke Affects Runners")

    icon_runner(d, 808 * S, 626 * S, 152 * S, color=INK)
    for ox, oy in ((-64, -30), (52, 22), (-24, 74), (74, -46)):
        x, y = 366 * S + ox * S, 630 * S + oy * S
        d.ellipse([x - 9 * S, y - 9 * S, x + 9 * S, y + 9 * S],
                  fill=RED + (255,))
    text(d, (366 * S, 812 * S), "INFLAMMATION", font(BLACK_F, 25), RED,
         anchor="ma", spacing=2.4)
    text(d, (808 * S, 812 * S), "REDUCED VO₂", font(BLACK_F, 25), EMBER,
         anchor="ma", spacing=2.4)

    panel(d, [80 * S, 880 * S, 1000 * S, 1122 * S])
    text(d, (124 * S, 918 * S), "+12.8", font(BLACK_F, 92), EMBER)
    text(d, (124 * S, 1032 * S), "SECONDS ADDED TO A 5K",
         font(BLACK_F, 26), INK, spacing=2.2)
    para(d, 530 * S, 928 * S,
         "Measured in NCAA distance runners over 21 days of elevated PM2.5 — "
         "sustained exposure, not one bad-air day.",
         font(REG_F, 23), MUTED, 420 * S, 32 * S)

    y = 1162 * S
    for lab, body in (
        ("PARTICLES GO DEEP",
         "Hard breathing pulls air in through the mouth, past the nose's "
         "filter — PM2.5 reaches the alveoli and the blood."),
        ("AIRWAYS TIGHTEN",
         "Inflammation narrows airways and blunts oxygen delivery, so race "
         "pace costs more effort."),
    ):
        text(d, (80 * S, y), lab, font(BLACK_F, 36), INK)
        y = para(d, 80 * S, y + 48 * S, body, font(REG_F, 26), MUTED,
                 880 * S, 36 * S) + 26 * S

    text(d, (80 * S, 1480 * S), "RUN BY THE NUMBER", font(BLACK_F, 30), INK)
    aqi_bar(d, 80 * S, 1600 * S, 1000 * S, 30 * S, "PEAK SMOKE EVENT")
    for i, (a, b) in enumerate((("UNDER 100", "Train normally"),
                                ("100–150", "Ease intensity"),
                                ("OVER 150", "Take it indoors"))):
        x = (80 + i * 307) * S
        text(d, (x, 1690 * S), a, font(BLACK_F, 26), ORANGE, spacing=1.4)
        text(d, (x, 1726 * S), b, font(REG_F, 25), MUTED)

    footer(d, "Sources: NCAA 5K performance & PM2.5 exposure study "
              "(334 male runners); EPA AQI activity guidance.")
    return img


def card4():
    img = background(seed=53)
    glow(img, [140 * S, 440 * S, 960 * S, 1180 * S], ORANGE, 165, 40)
    d = ImageDraw.Draw(img, "RGBA")
    header(d, "04", "THE FIX", "How We Can Help Prevent Mega Fires")

    y = 450
    for ic, name, body, col in (
        (icon_flame, "PRESCRIBED BURNS",
         "Low-intensity fire set on purpose clears the fuel that turns a "
         "spark into a megafire.", ORANGE),
        (icon_hands_fire, "INDIGENOUS FIRE PRACTICE",
         "Cultural burning has shaped these forests for millennia — "
         "First Nations-led crews are bringing it back.", EMBER),
        (icon_beaver, "BEAVERS",
         "Their dams spread water across the valley floor, holding wet, "
         "green refuges that fire runs around.", ORANGE),
    ):
        panel(d, [80 * S, y * S, 1000 * S, (y + 268) * S])
        cx, cy = 216 * S, (y + 134) * S
        d.ellipse([cx - 92 * S, cy - 92 * S, cx + 92 * S, cy + 92 * S],
                  fill=(26, 20, 19, 255), outline=(60, 42, 34, 255),
                  width=int(2 * S))
        ic(d, cx, cy, 56 * S, color=col)
        text(d, (350 * S, (y + 56) * S), name, font(BLACK_F, 37), INK)
        para(d, 350 * S, (y + 112) * S, body, font(REG_F, 26), MUTED,
             590 * S, 36 * S)
        y += 300

    para(d, 80 * S, 1440 * S,
         "We can't stop the lightning. We can starve the fire of fuel.",
         font(BLACK_F, 42), INK, 900 * S, 56 * S)
    d.rounded_rectangle([80 * S, 1596 * S, 198 * S, 1604 * S], radius=4 * S,
                        fill=RED + (255,))
    footer(d, "Sources: USFS & Parks Canada prescribed-fire programs; "
              "First Nations cultural burning initiatives; beaver-wetland "
              "fire-refugia research (Fairfax & Whittle, 2020).")
    return img


CARDS = (card1, card2, card3, card4)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(out, exist_ok=True)
    for i, fn in enumerate(CARDS, start=1):
        img = fn().convert("RGB").resize((W, H), Image.LANCZOS)
        path = os.path.join(out, f"card{i}.png")
        img.save(path, "PNG")
        print("wrote", path)


if __name__ == "__main__":
    main()
