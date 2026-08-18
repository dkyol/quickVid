#!/usr/bin/env python3
"""Build the three transparent overlay assets for the DC run stitch:
  1. distance.png   - IMG_4589 "6.20 / Miles" card, white keyed to transparent
  2. stats.png       - top stat-grid crop of IMG_4587, white keyed to transparent
  3. route_line.png  - map crop of IMG_4587, basemap stripped, only the
                        colored GPS route line + start/end dots kept
All output at native crop resolution, RGBA PNG, ready for ffmpeg overlay.
"""
import colorsys
from PIL import Image, ImageFilter

ROOT = "C:/Users/DKYLE/Desktop/scripts/quickVid"
SRC_STATS_MAP = f"{ROOT}/media/run_race_drive/IMG_4587.jpg"
SRC_DIST = f"{ROOT}/media/run_race_drive/IMG_4589.jpg"
OUT = f"{ROOT}/overlay_work"


def key_white_to_alpha(im, white_thresh=235, feather=40):
    """Alpha = 0 where pixel is near-white, 255 where pixel is dark/saturated
    content, linear ramp between. Keeps original RGB (unmultiplied)."""
    im = im.convert("RGB")
    px = im.load()
    w, h = im.size
    out = Image.new("RGBA", (w, h))
    opx = out.load()
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            # "whiteness" = how close to pure white this pixel is
            mn = min(r, g, b)
            if mn >= white_thresh:
                a = 0
            elif mn <= white_thresh - feather:
                a = 255
            else:
                a = int(255 * (white_thresh - mn) / feather)
            opx[x, y] = (r, g, b, a)
    return out


def route_line_mask(im, hue_lo=0, hue_hi=118, sat_min=0.42, val_min=0.32):
    """Keep only saturated route-line colors (red/orange/yellow/green hues),
    drop everything else (roads, water, parks, labels, chips, attribution)."""
    im = im.convert("RGB")
    px = im.load()
    w, h = im.size
    out = Image.new("RGBA", (w, h))
    opx = out.load()
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            hh, ss, vv = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            hue_deg = hh * 360
            if ss >= sat_min and vv >= val_min and hue_lo <= hue_deg <= hue_hi:
                opx[x, y] = (r, g, b, 255)
            else:
                opx[x, y] = (0, 0, 0, 0)

    # Bridge small gaps left where mile-marker pills / labels sat on top of
    # the route line and occluded its color in the source photo: the true
    # color under a pill is simply gone, so approximate it by dilating RGB
    # from nearby line pixels (max-filter picks up the bright neighboring
    # route color), while alpha gets a proper morphological close
    # (dilate+erode) so the line's own width doesn't grow, only the gaps fill.
    r_ch, g_ch, b_ch, a_ch = out.split()
    r_ch = r_ch.filter(ImageFilter.MaxFilter(7))
    g_ch = g_ch.filter(ImageFilter.MaxFilter(7))
    b_ch = b_ch.filter(ImageFilter.MaxFilter(7))
    a_ch = a_ch.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.MinFilter(7))
    out = Image.merge("RGBA", (r_ch, g_ch, b_ch, a_ch))
    return out


def with_shadow(img, blur=7, shadow_alpha=210, grow=3):
    """Legibility halo for text over unpredictable video backgrounds: a
    blurred black copy of the alpha silhouette sits behind the original
    (dilated slightly first so the halo reads past the glyph edges), so
    dark text stays readable over bright/busy footage instead of vanishing
    into it (measured problem: plain black text disappeared into a tree
    canopy background at full render)."""
    r, g, b, a = img.split()
    halo_a = a.filter(ImageFilter.MaxFilter(2 * grow + 1)).filter(ImageFilter.GaussianBlur(blur))
    halo_a = halo_a.point(lambda v: min(v, shadow_alpha))
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    shadow.putalpha(halo_a)
    out = Image.alpha_composite(shadow, img)
    return out


def main():
    # --- distance card ---
    dist = Image.open(SRC_DIST)
    dist_a = with_shadow(key_white_to_alpha(dist))
    dist_a.save(f"{OUT}/distance.png")
    print("distance.png", dist_a.size)

    # --- stats + map source ---
    full = Image.open(SRC_STATS_MAP)
    w, h = full.size
    print("IMG_4587 size", w, h)

    # stat grid: top region above the map (measured boundary, see probe crops)
    stats_crop = full.crop((0, 0, w, 555))
    stats_a = with_shadow(key_white_to_alpha(stats_crop))
    stats_a.save(f"{OUT}/stats.png")
    print("stats.png", stats_a.size)

    # map region: everything below the stat grid
    map_crop = full.crop((0, 555, w, h))
    route_a = with_shadow(route_line_mask(map_crop), blur=5, shadow_alpha=160, grow=2)
    route_a.save(f"{OUT}/route_line.png")
    print("route_line.png", route_a.size)


if __name__ == "__main__":
    main()
