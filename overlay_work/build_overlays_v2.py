#!/usr/bin/env python3
"""v2 rebuild of the three overlay assets, fixing issues found in the first
composited cut (dc_run_stitch_overlaid_trimmed.mp4):
  1. distance.png  - crop tight to the "6.20 / Miles" text bbox (was a wide
     canvas with the text jammed left, which is why it read off-center once
     composited) so the compositor can center it cleanly.
  2. stats.png      - erase the "Avg Heart Rate" cell (no real data, "--").
  3. route_line.png - bridge every real gap left by mile-marker pills / the
     "Washington, DC" label / the "295" shield sitting on top of the route
     stroke in the source screenshot (connected-components + a minimum
     spanning tree over cross-component nearest-endpoint distances, so every
     disconnected piece of the actual route gets one bridge stroke), then
     crop tight to content and let the compositor scale it up.
"""
import colorsys
import itertools

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage
from scipy.spatial.distance import cdist

ROOT = "C:/Users/DKYLE/Desktop/scripts/quickVid"
SRC_STATS_MAP = f"{ROOT}/media/run_race_drive/IMG_4587.jpg"
SRC_DIST = f"{ROOT}/media/run_race_drive/IMG_4589.jpg"
OUT = f"{ROOT}/overlay_work"


def key_white_to_alpha(im, white_thresh=235, feather=40):
    im = im.convert("RGB")
    px = im.load()
    w, h = im.size
    out = Image.new("RGBA", (w, h))
    opx = out.load()
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            mn = min(r, g, b)
            if mn >= white_thresh:
                a = 0
            elif mn <= white_thresh - feather:
                a = 255
            else:
                a = int(255 * (white_thresh - mn) / feather)
            opx[x, y] = (r, g, b, a)
    return out


def with_shadow(img, blur=7, shadow_alpha=210, grow=3):
    r, g, b, a = img.split()
    halo_a = a.filter(ImageFilter.MaxFilter(2 * grow + 1)).filter(ImageFilter.GaussianBlur(blur))
    halo_a = halo_a.point(lambda v: min(v, shadow_alpha))
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    shadow.putalpha(halo_a)
    return Image.alpha_composite(shadow, img)


def alpha_bbox(im, thresh=10, pad=0):
    a = np.array(im)[..., 3]
    ys, xs = np.where(a > thresh)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    w, h = im.size
    return (max(0, x0 - pad), max(0, y0 - pad),
            min(w, x1 + 1 + pad), min(h, y1 + 1 + pad))


# --------------------------------------------------------------------------
# distance card - tight crop so the compositor can truly center it
# --------------------------------------------------------------------------

def build_distance():
    dist = Image.open(SRC_DIST)
    dist_a = with_shadow(key_white_to_alpha(dist))
    box = alpha_bbox(dist_a, pad=18)
    cropped = dist_a.crop(box)
    cropped.save(f"{OUT}/distance.png")
    print("distance.png", cropped.size, "(cropped from", dist_a.size, ")")


# --------------------------------------------------------------------------
# stats grid - erase the Avg Heart Rate cell (middle column, row 2)
# --------------------------------------------------------------------------

def build_stats():
    full = Image.open(SRC_STATS_MAP)
    w, h = full.size
    stats_crop = full.crop((0, 0, w, 555))
    stats_a = with_shadow(key_white_to_alpha(stats_crop))

    # measured cell bbox: x 423-681, row2 y 277-555 in the pre-shadow crop;
    # pad generously since with_shadow grew the halo a few px past the glyphs
    arr = np.array(stats_a)
    arr[260:, 395:715, :] = 0
    stats_a = Image.fromarray(arr, "RGBA")
    stats_a.save(f"{OUT}/stats.png")
    print("stats.png", stats_a.size, "(Avg Heart Rate cell erased)")


# --------------------------------------------------------------------------
# route line - bridge every real gap, then crop tight to content
# --------------------------------------------------------------------------

def route_line_mask_raw(im):
    """Same color-key as before, returns (rgba_array, keep_bool_array)."""
    im = im.convert("RGB")
    arr = np.array(im).astype(np.float32) / 255.0
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    mx = arr.max(axis=2)
    mn = arr.min(axis=2)
    v = mx
    s = np.where(mx > 0, (mx - mn) / np.where(mx == 0, 1, mx), 0)
    delta = mx - mn
    hue = np.zeros_like(mx)
    mr = (mx == r) & (delta != 0)
    mg = (mx == g) & (delta != 0)
    mb = (mx == b) & (delta != 0)
    hue[mr] = (((g - b) / np.where(delta == 0, 1, delta))[mr]) % 6
    hue[mg] = (((b - r) / np.where(delta == 0, 1, delta))[mg]) + 2
    hue[mb] = (((r - g) / np.where(delta == 0, 1, delta))[mb]) + 4
    hue_deg = hue * 60
    keep = (s >= 0.42) & (v >= 0.32) & (hue_deg >= 0) & (hue_deg <= 118)

    rgba = np.zeros((*mx.shape, 4), dtype=np.uint8)
    src = np.array(im)
    rgba[..., :3] = src
    rgba[..., 3] = np.where(keep, 255, 0).astype(np.uint8)
    return rgba, keep


def bridge_gaps(rgba, keep, min_size=50, max_bridge=250, stroke_w=34):
    lbl, n = ndimage.label(keep, structure=np.ones((3, 3)))
    sizes = ndimage.sum(keep, lbl, range(1, n + 1))
    comp_ids = [i + 1 for i, sz in enumerate(sizes) if sz >= min_size]

    rng = np.random.RandomState(0)
    pts_by_comp = {}
    for cid in comp_ids:
        ys, xs = np.where(lbl == cid)
        pts = np.stack([xs, ys], axis=1)
        if len(pts) > 600:
            idx = rng.choice(len(pts), 600, replace=False)
            pts = pts[idx]
        pts_by_comp[cid] = pts

    edges = []
    for a, b in itertools.combinations(comp_ids, 2):
        d = cdist(pts_by_comp[a], pts_by_comp[b])
        i, j = np.unravel_index(np.argmin(d), d.shape)
        edges.append((d[i, j], a, b, pts_by_comp[a][i], pts_by_comp[b][j]))
    edges.sort(key=lambda e: e[0])

    parent = {c: c for c in comp_ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry
            return True
        return False

    img = Image.fromarray(rgba, "RGBA")
    draw = ImageDraw.Draw(img)
    n_bridges = 0
    for d, a, b, pa, pb in edges:
        if not union(a, b):
            continue
        n_bridges += 1
        ca = tuple(int(c) for c in rgba[pa[1], pa[0], :3])
        cb = tuple(int(c) for c in rgba[pb[1], pb[0], :3])
        mid_color = tuple((ca[i] + cb[i]) // 2 for i in range(3))
        draw.line([tuple(pa), tuple(pb)], fill=(*mid_color, 255),
                   width=stroke_w, joint="curve")
        r = stroke_w // 2
        for p in (pa, pb):
            draw.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r],
                          fill=(*mid_color, 255))
    print(f"  bridged {n_bridges} gaps across {len(comp_ids)} route pieces "
          f"(max bridge dist {max(d for d,*_ in edges[:n_bridges]) if n_bridges else 0:.0f}px)")
    return np.array(img)


def build_route_line():
    full = Image.open(SRC_STATS_MAP)
    w, h = full.size
    map_crop = full.crop((0, 555, w, h))

    rgba, keep = route_line_mask_raw(map_crop)
    rgba = bridge_gaps(rgba, keep)

    out = Image.fromarray(rgba, "RGBA")
    # light morphological close to smooth the new bridge joins + any
    # remaining hairline gaps under thin labels, same as the original pass
    r_ch, g_ch, b_ch, a_ch = out.split()
    r_ch = r_ch.filter(ImageFilter.MaxFilter(7))
    g_ch = g_ch.filter(ImageFilter.MaxFilter(7))
    b_ch = b_ch.filter(ImageFilter.MaxFilter(7))
    a_ch = a_ch.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.MinFilter(7))
    out = Image.merge("RGBA", (r_ch, g_ch, b_ch, a_ch))

    out = with_shadow(out, blur=5, shadow_alpha=160, grow=2)

    box = alpha_bbox(out, pad=24)
    cropped = out.crop(box)
    cropped.save(f"{OUT}/route_line.png")
    print("route_line.png", cropped.size, "(cropped from", out.size, ")")


def main():
    build_distance()
    build_stats()
    build_route_line()


if __name__ == "__main__":
    main()
