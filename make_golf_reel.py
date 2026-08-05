#!/usr/bin/env python3
"""
make_golf_reel.py — Build a hole-by-hole 9:16 golf course tour from ./media/,
with a par/yardage card burned onto each hole and vertical drop-in transitions
between holes (instead of a hard cut or a straight horizontal stitch).

You normally do NOT run this by hand — follow SKILLS/golfCompliationskill.MD and
let Claude call it with the right flags after the hole data and script are
confirmed. It also works standalone once prompts/holes.json exists:

    # Front nine, 45s target, silent, vertical drop-in transitions:
    python make_golf_reel.py --nine front --target-seconds 45

    # Full 18, with a voiceover and captions:
    python make_golf_reel.py --nine both --target-seconds 90 \
        --sound voiceover --subtitles auto --transition slidedown

Ordering: media files are matched to hole slots by their numeric prefix
(01_, 02_, ...) — position 1 is hole 1 (front/both) or hole 10 (back). A slot
with no matching file gets a plain black placeholder, still carded with that
hole's par/yardage.

Reuses the ffmpeg/ASS-overlay plumbing already in make_reel.py (tool discovery,
subtitle burn-in, title/timer overlays, cover-crop/fit filters) rather than
re-implementing it.
"""

import argparse
import datetime
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

from PIL import Image, ImageOps

import make_reel as mr

ROOT = os.path.dirname(os.path.abspath(__file__))
MEDIA_DIR = os.path.join(ROOT, "media")
VO_DIR = os.path.join(ROOT, "voiceover")
FINAL_DIR = os.path.join(ROOT, "final")
PROMPTS_DIR = os.path.join(ROOT, "prompts")
TMP_DIR = os.path.join(ROOT, "_tmp_golf_build")

PREFIX_RE = re.compile(r"^(\d+)[_-]")

_CARD_ALIGN = {"top": 8, "middle": 5, "bottom": 2}


# --------------------------------------------------------------------------- #
# Hole data
# --------------------------------------------------------------------------- #
def load_holes_json(path):
    if not os.path.exists(path):
        sys.exit(f"ERROR: hole data file not found: {path}\n"
                 f"Create it first (see golfCompliationskill.MD step 4) - one "
                 f"entry per hole, e.g.:\n"
                 f'  {{"1": {{"par": 4, "yards": 385}}, "2": {{"par": 3, "yards": 162}}}}')
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.exit(f"ERROR: could not parse {path}: {e}")


def load_optional_json(path):
    if not path:
        return {}
    if not os.path.exists(path):
        sys.exit(f"ERROR: file not found: {path}")
    return json.loads(Path(path).read_text(encoding="utf-8"))


def hole_numbers_for(nine):
    if nine == "front":
        return list(range(1, 10))
    if nine == "back":
        return list(range(10, 19))
    return list(range(1, 19))


def gather_hole_files(media_dir, n_slots):
    """Map slot position (1-based, matching numeric filename prefix) -> file path."""
    if not os.path.isdir(media_dir):
        sys.exit(f"ERROR: media folder not found: {media_dir}")
    by_pos = {}
    for name in sorted(os.listdir(media_dir), key=mr.natural_key):
        ext = os.path.splitext(name)[1].lower()
        if ext not in mr.IMAGE_EXT and ext not in mr.VIDEO_EXT:
            continue
        m = PREFIX_RE.match(name)
        if not m:
            print(f"  NOTE: skipping '{name}' - no numeric prefix (01_, 02_, ...).")
            continue
        pos = int(m.group(1))
        if pos < 1 or pos > n_slots:
            print(f"  NOTE: '{name}' prefix {pos} is outside 1-{n_slots}; skipping.")
            continue
        if pos in by_pos:
            print(f"  NOTE: multiple files prefixed {pos:02d}_ - using "
                  f"'{os.path.basename(by_pos[pos])}', ignoring '{name}'.")
            continue
        by_pos[pos] = os.path.join(media_dir, name)
    return by_pos


# --------------------------------------------------------------------------- #
# Per-hole segment building
# --------------------------------------------------------------------------- #
def build_blank_segment(dst, dur):
    mr.run(["-f", "lavfi", "-i",
            f"color=c=black:s={mr.TARGET_W}x{mr.TARGET_H}:d={dur:.3f}:r={mr.FPS}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", dst], "blank")


def build_hole_video_segment(src, dst, planned_dur, max_clip=None, fit=False):
    """Normalize a hole's video to exactly planned_dur: trim if it runs long,
    hold the last frame if it runs short (a swing clip rarely lands on the nose)."""
    trim_target = min(planned_dur, max_clip) if max_clip else planned_dur
    raw = dst + ".raw.mp4"
    mr.normalize_video(src, raw, max_dur=trim_target, speed_to_fit=False, fit=fit)
    d0 = mr.duration_of(raw)
    if d0 < planned_dur - 0.05:
        mr.run(["-i", raw, "-vf",
                f"tpad=stop_mode=clone:stop_duration={planned_dur - d0:.3f}",
                "-t", f"{planned_dur:.3f}",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(mr.FPS),
                "-an", dst], "pad")
        os.remove(raw)
    elif d0 > planned_dur + 0.05:
        mr.run(["-i", raw, "-t", f"{planned_dur:.3f}",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(mr.FPS),
                "-an", dst], "trim")
        os.remove(raw)
    else:
        os.replace(raw, dst)


# --------------------------------------------------------------------------- #
# The hole card (hole #, par, yardage from the whites)
# --------------------------------------------------------------------------- #
def write_hole_card_ass(path, video_dur, hole_number, par, yards, handicap,
                        position="bottom", fontsize=72, font="Arial"):
    """Burn 'HOLE N' plus a smaller 'PAR X | Y YDS | HCP N' line under it, for
    the whole span of this hole's segment. Mirrors write_title_ass's ASS
    styling so the look matches the rest of the toolkit."""
    stat_bits = []
    if par:
        stat_bits.append(f"PAR {par}")
    if yards:
        stat_bits.append(f"{yards} YDS")
    if handicap:
        stat_bits.append(f"HCP {handicap}")
    stat_line = "   |   ".join(stat_bits)
    stat_fs = max(28, int(fontsize * 0.5))
    label = f"HOLE {hole_number}"
    text = label
    if stat_line:
        text += "\\N{\\fs" + str(stat_fs) + "}" + stat_line + "{\\r}"

    align = _CARD_ALIGN.get(position, 2)
    marginv = 0 if position == "middle" else 140
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\nWrapStyle: 0\n"
        f"PlayResX: {mr.TARGET_W}\nPlayResY: {mr.TARGET_H}\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, "
        "Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
        "MarginR, MarginV, Encoding\n"
        f"Style: Card,{font},{fontsize},&H00FFFFFF,&H00000000,&H64000000,"
        f"1,0,0,0,100,100,0,0,1,5,1,{align},80,80,{marginv},1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
        "Effect, Text\n"
        f"Dialogue: 0,{mr._ass_ts(0)},{mr._ass_ts(video_dur)},Card,,0,0,0,,{text}\n"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(header)


def write_course_title_ass(path, video_dur, name, location,
                           fontsize=88, font="Arial"):
    """Course name (big) + location (smaller line beneath), centered - the
    opening title card. Same Card style plumbing as write_hole_card_ass, just
    middle-aligned and rendered onto its own black segment rather than over
    hole 1's media."""
    loc_fs = max(28, int(fontsize * 0.45))
    text = name.strip()
    if location:
        text += "\\N{\\fs" + str(loc_fs) + "}" + location.strip() + "{\\r}"
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\nWrapStyle: 0\n"
        f"PlayResX: {mr.TARGET_W}\nPlayResY: {mr.TARGET_H}\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, "
        "Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
        "MarginR, MarginV, Encoding\n"
        f"Style: Card,{font},{fontsize},&H00FFFFFF,&H00000000,&H64000000,"
        f"1,0,0,0,100,100,0,0,1,5,1,5,80,80,0,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
        "Effect, Text\n"
        f"Dialogue: 0,{mr._ass_ts(0)},{mr._ass_ts(video_dur)},Card,,0,0,0,,{text}\n"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(header)


def build_title_segment(tmp_dir, dur, name, location, font):
    """Build the opening title card as its own normalized segment (black
    background + centered course name/location), so it can ride in the same
    xfade chain as the hole segments - segment zero, not a hard cut."""
    base_path = os.path.join(tmp_dir, "title_base.mp4")
    build_blank_segment(base_path, dur)
    ass_path = os.path.join(tmp_dir, "title_card.ass")
    write_course_title_ass(ass_path, dur, name, location, font=font)
    seg_path = os.path.join(tmp_dir, "title.mp4")
    burn_ass(base_path, seg_path, ass_path)
    return seg_path


# --------------------------------------------------------------------------- #
# Hole layout thumbnail inset (broadcast-style corner accent, optional)
# --------------------------------------------------------------------------- #
_MAP_CORNER = {
    "top-right": lambda w, h, iw, ih, m: (w - iw - m, m),
    "top-left": lambda w, h, iw, ih, m: (m, m),
    "bottom-right": lambda w, h, iw, ih, m: (w - iw - m, h - ih - m),
    "bottom-left": lambda w, h, iw, ih, m: (m, h - ih - m),
}


def overlay_hole_map(src, dst, map_path, tmp_dir, position="top-right",
                     margin=40, max_w=190, max_h=340, border=4):
    """Composite the hole's layout thumbnail (map_path) into a corner of src,
    with a thin white border so it reads against varied photo backgrounds -
    an accent next to the stat card, not a replacement for it. Whatever the
    thumbnail's native aspect (course corridors are naturally long and thin,
    not square), it's fit inside (max_w, max_h) and cropped no further."""
    im = Image.open(map_path).convert("RGB")
    im.thumbnail((max_w, max_h))
    bordered = ImageOps.expand(im, border=border, fill="white")
    iw, ih = bordered.size
    inset_png = os.path.join(tmp_dir, "map_inset.png")
    bordered.save(inset_png)

    x, y = _MAP_CORNER.get(position, _MAP_CORNER["top-right"])(
        mr.TARGET_W, mr.TARGET_H, iw, ih, margin)

    # overlay's default eof_action=repeat means it never signals EOF on its
    # own just because src ends (the looped image input keeps "running"
    # forever) - -shortest alone doesn't reliably cut it, so force an
    # explicit -t at src's own duration instead of trusting stream EOF.
    src_dur = mr.duration_of(src)
    mr.run(["-i", src, "-loop", "1", "-i", inset_png,
            "-filter_complex", f"[0:v][1:v]overlay={x}:{y}:shortest=1",
            "-t", f"{src_dur:.3f}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-r", str(mr.FPS), "-an", dst], "map-overlay")
    os.remove(inset_png)


def burn_ass(src, dst, ass_path, style=None):
    """Same trick as make_reel.burn_subs (cwd = the .ass's folder, so the
    subtitles filter gets a bare filename - avoids Windows drive-colon
    escaping problems), parameterized to our own TMP_DIR. Works for both
    .ass (card/title/timer, style baked into the file) and .srt (captions,
    pass style=mr.SUB_STYLE)."""
    ass_dir = os.path.dirname(os.path.abspath(ass_path))
    ass_name = os.path.basename(ass_path)
    filt = f"subtitles={ass_name}"
    if style:
        filt += f":force_style='{style}'"
    audio_args = ["-c:a", "copy"] if mr.has_audio(src) else ["-an"]
    mr.run(["-i", os.path.abspath(src), "-vf", filt,
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(mr.FPS),
            *audio_args, os.path.abspath(dst)], "card-burn", cwd=ass_dir)


# --------------------------------------------------------------------------- #
# Vertical drop-in transitions between holes
# --------------------------------------------------------------------------- #
def chain_xfade(segments, durations, transition, trans_dur, dst):
    """Chain hole segments with ffmpeg's xfade filter (slidedown by default)
    so each hole drops into frame over the previous one, instead of a hard
    cut or a plain concat. Returns the final stitched duration."""
    n = len(segments)
    if n == 1:
        shutil.copyfile(segments[0], dst)
        return durations[0]

    max_allowed = min(min(durations[i], durations[i + 1]) for i in range(n - 1)) * 0.8
    td = min(trans_dur, max_allowed) if max_allowed > 0 else trans_dur
    if td < trans_dur - 0.001:
        print(f"  NOTE: transition duration clamped to {td:.2f}s "
              f"(a hole segment is short).")

    inputs = []
    for s in segments:
        inputs += ["-i", s]

    filter_parts = []
    cum_len = durations[0]
    prev_label = "0:v"
    for i in range(1, n):
        offset = max(0.0, cum_len - td)
        out_label = f"v{i}"
        filter_parts.append(
            f"[{prev_label}][{i}:v]xfade=transition={transition}:"
            f"duration={td:.3f}:offset={offset:.3f}[{out_label}]"
        )
        cum_len = cum_len + durations[i] - td
        prev_label = out_label

    mr.run([*inputs, "-filter_complex", ";".join(filter_parts),
            "-map", f"[{prev_label}]",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(mr.FPS), "-an",
            dst], "xfade")
    return cum_len


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(
        description="Build a hole-by-hole 9:16 golf course reel from ./media/")
    ap.add_argument("--nine", choices=["front", "back", "both"], required=True,
                    help="Which holes are in ./media/: front (1-9), back "
                         "(10-18), or both (1-18).")
    ap.add_argument("--holes-json", default=os.path.join(PROMPTS_DIR, "holes.json"),
                    help="Per-hole par/yardage data (default prompts/holes.json). "
                         'Format: {"1": {"par": 4, "yards": 385}, ...}')
    ap.add_argument("--hole-seconds", type=float, default=4.0,
                    help="Default seconds each hole is on screen (default 4.0). "
                         "Ignored per-hole where --target-seconds or "
                         "--hole-seconds-json says otherwise.")
    ap.add_argument("--target-seconds", default=None,
                    help="Target TOTAL reel length ('MM:SS' or seconds). When "
                         "set, hole time is split evenly across the holes in "
                         "scope (minus the transition overlaps), overriding "
                         "--hole-seconds.")
    ap.add_argument("--hole-seconds-json", default=None,
                    help="Optional per-hole override, same key format as "
                         "--holes-json, e.g. {\"7\": 6.0} to linger on the "
                         "signature hole. Overrides the computed default for "
                         "just those holes.")
    ap.add_argument("--max-clip-seconds", type=float, default=0.0,
                    help="Trim each hole's source video to at most this many "
                         "seconds of real footage before holding the last "
                         "frame to fill the rest of its on-screen time "
                         "(0 = use the full planned duration as the trim cap).")
    ap.add_argument("--fit", action="store_true",
                    help="Fit media inside the 9:16 frame with letterbox bars "
                         "instead of cropping to fill. Use for landscape shots.")
    ap.add_argument("--no-ken-burns", action="store_true",
                    help="Disable the slow zoom on still hole photos.")
    ap.add_argument("--transition", default="slidedown",
                    help="ffmpeg xfade transition between holes (default "
                         "slidedown - the next hole drops in from above). "
                         "wipedown is a harder-edged alternative; slideup/"
                         "wipeup/slideleft/slideright etc. also work.")
    ap.add_argument("--transition-duration", type=float, default=0.5,
                    help="Seconds each hole-to-hole transition takes (default "
                         "0.5; auto-clamped shorter for very short holes).")
    ap.add_argument("--card-position", choices=["top", "middle", "bottom"],
                    default="bottom", help="Where the hole card sits (default bottom).")
    ap.add_argument("--card-fontsize", type=int, default=72,
                    help="Hole-number font size in px (default 72); the par/"
                         "yardage line renders at about half that.")
    ap.add_argument("--no-map-inset", action="store_true",
                    help="Skip the hole layout thumbnail inset even where "
                         "holes.json has one (the stat card still shows).")
    ap.add_argument("--map-position",
                    choices=["top-right", "top-left", "bottom-right", "bottom-left"],
                    default="top-right",
                    help="Corner for the hole layout thumbnail inset (default "
                         "top-right, clear of the bottom stat card).")
    ap.add_argument("--map-max-width", type=int, default=420,
                    help="Max width in px of the layout thumbnail inset (default "
                         "420). Matches the native size produced by the "
                         "rotate-to-vertical thumbnail pipeline (tee->green "
                         "always rotated to point up, ~420x720) - large and "
                         "always portrait, not a small corner accent.")
    ap.add_argument("--map-max-height", type=int, default=720,
                    help="Max height in px of the layout thumbnail inset (default 720).")
    ap.add_argument("--font", default="Arial",
                    help="Font family for the hole card, title, and captions.")
    ap.add_argument("--course-title", default=None,
                    help="Course name for the opening title card (e.g. "
                         "'Langston Golf Course'). When set, a title segment "
                         "is built and dropped into hole 1 the same way one "
                         "hole drops into the next - not a hard cut.")
    ap.add_argument("--course-location", default=None,
                    help="Location line under the course name on the title "
                         "card (e.g. 'Washington, D.C.').")
    ap.add_argument("--course-title-seconds", type=float, default=2.5,
                    help="How long the opening title card holds before "
                         "dropping into hole 1 (default 2.5).")
    ap.add_argument("--sound", choices=["none", "voiceover"], default="none",
                    help="none = silent reel. voiceover = mux the --vo audio "
                         "(course-description narration).")
    ap.add_argument("--vo", default=None,
                    help="Path to the voiceover audio file. If omitted, the "
                         "first audio file in ./voiceover/ is used.")
    ap.add_argument("--subtitles", choices=["none", "auto", "file"], default="none",
                    help="none = no captions. auto = evenly-timed captions from "
                         "the narration script. file = burn a provided .srt.")
    ap.add_argument("--sub-script", default=None,
                    help="Text file the auto captions are built from "
                         "(default: prompts/script.txt).")
    ap.add_argument("--sub-file", default=None,
                    help="Path to a .srt file to burn in (with --subtitles file).")
    ap.add_argument("--title", default=None,
                    help="Optional intro headline (e.g. the course name) over "
                         "the first few seconds of the finished reel.")
    ap.add_argument("--title-seconds", type=float, default=3.0,
                    help="How long the title shows (default 3.0; 0 = whole reel).")
    ap.add_argument("--title-position", choices=["top", "middle", "bottom"],
                    default="top", help="Where the title sits (default top).")
    ap.add_argument("--title-fontsize", type=int, default=64,
                    help="Title font size in px (default 64).")
    ap.add_argument("--timer", action="store_true",
                    help="Burn a running timer (1/100 s) over the whole reel.")
    ap.add_argument("--timer-seconds", default=None,
                    help="How long the compilation took to make (timer's "
                         "starting value). Default: the reel's own length.")
    ap.add_argument("--timer-direction", choices=["down", "up"], default="down")
    ap.add_argument("--timer-position", choices=["top", "middle", "bottom"],
                    default="top")
    ap.add_argument("--timer-fontsize", type=int, default=72)
    ap.add_argument("--timer-font", default=None,
                    help="Defaults to --font; pass a monospace font (e.g. "
                         "'Consolas') to keep the digits from shifting width.")
    args = ap.parse_args()
    t_start = time.time()

    os.makedirs(FINAL_DIR, exist_ok=True)
    if os.path.isdir(TMP_DIR):
        shutil.rmtree(TMP_DIR)
    os.makedirs(TMP_DIR)

    holes_data = load_holes_json(args.holes_json)
    hole_seconds_override = load_optional_json(args.hole_seconds_json)

    hole_numbers = hole_numbers_for(args.nine)
    n_holes = len(hole_numbers)
    by_pos = gather_hole_files(MEDIA_DIR, n_holes)

    missing = [hole_numbers[p - 1] for p in range(1, n_holes + 1) if p not in by_pos]
    if missing:
        print(f"Missing media for hole(s) {', '.join(str(h) for h in missing)} "
              f"- inserting blank placeholders.")
    no_data = [h for h in hole_numbers if str(h) not in holes_data]
    if no_data:
        print(f"  NOTE: no par/yardage in {os.path.basename(args.holes_json)} for "
              f"hole(s) {', '.join(str(h) for h in no_data)} - card will show the "
              f"hole number only.")

    # Plan each hole's on-screen time.
    max_clip = args.max_clip_seconds if args.max_clip_seconds else None
    if args.target_seconds is not None:
        target = mr.parse_duration(args.target_seconds)
        # chain_xfade's stitched output = sum(durations) - transition_dur*(n-1),
        # so each hole's raw duration needs to ADD BACK the overlap it'll lose
        # in stitching, not subtract it again.
        overlap = args.transition_duration * (n_holes - 1) if n_holes > 1 else 0.0
        default_dur = max(1.0, (target + overlap) / n_holes)
        print(f"\nTarget {target:g}s across {n_holes} holes -> "
              f"~{default_dur:.2f}s/hole (before per-hole overrides).")
    else:
        default_dur = args.hole_seconds

    planned = {h: hole_seconds_override.get(str(h), default_dur) for h in hole_numbers}

    # Build each hole's segment (media normalized to plan length + card burned in).
    segments, durations = [], []
    no_map_holes = []
    print()

    if args.course_title:
        title_seg = build_title_segment(TMP_DIR, args.course_title_seconds,
                                        args.course_title, args.course_location,
                                        args.font)
        segments.append(title_seg)
        durations.append(mr.duration_of(title_seg))
        loc_note = f" / {args.course_location}" if args.course_location else ""
        print(f"  Title card: \"{args.course_title}{loc_note}\" "
              f"({args.course_title_seconds:g}s, drops into hole {hole_numbers[0]}).")

    for i, hole in enumerate(hole_numbers, start=1):
        dur = planned[hole]
        src = by_pos.get(i)
        base_path = os.path.join(TMP_DIR, f"hole_{hole:02d}_base.mp4")

        if src is None:
            build_blank_segment(base_path, dur)
            source_note = "blank placeholder"
        else:
            ext = os.path.splitext(src)[1].lower()
            if ext in mr.IMAGE_EXT:
                mr.normalize_image(src, base_path, dur,
                                   ken_burns=not args.no_ken_burns, fit=args.fit)
            else:
                build_hole_video_segment(src, base_path, dur,
                                         max_clip=max_clip, fit=args.fit)
            source_note = os.path.basename(src)

        stats = holes_data.get(str(hole), {})
        par, yards, handicap = stats.get("par"), stats.get("yards"), stats.get("handicap")

        map_rel = stats.get("map")
        map_path = os.path.join(ROOT, map_rel) if map_rel else None
        has_map = bool(map_path and not args.no_map_inset and os.path.exists(map_path))
        if has_map:
            mapped_path = os.path.join(TMP_DIR, f"hole_{hole:02d}_mapped.mp4")
            overlay_hole_map(base_path, mapped_path, map_path, TMP_DIR,
                             position=args.map_position, margin=40,
                             max_w=args.map_max_width, max_h=args.map_max_height)
            base_path = mapped_path
        elif map_rel and not args.no_map_inset:
            print(f"  NOTE: hole {hole} lists a map ('{map_rel}') but the file "
                  f"is missing - card will show without the thumbnail.")

        card_ass = os.path.join(TMP_DIR, f"hole_{hole:02d}_card.ass")
        write_hole_card_ass(card_ass, dur, hole, par, yards, handicap,
                            position=args.card_position,
                            fontsize=args.card_fontsize, font=args.font)
        seg_path = os.path.join(TMP_DIR, f"hole_{hole:02d}.mp4")
        burn_ass(base_path, seg_path, card_ass)

        real_dur = mr.duration_of(seg_path)
        segments.append(seg_path)
        durations.append(real_dur)
        stat_bits = []
        if par:
            stat_bits.append(f"par {par}")
        if yards:
            stat_bits.append(f"{yards} yds")
        if handicap:
            stat_bits.append(f"hcp {handicap}")
        stat_str = " / ".join(stat_bits) if stat_bits else "no data"
        map_flag = " [map]" if has_map else ""
        print(f"  Hole {hole:>2}: {source_note:<28} {stat_str:<24} {real_dur:.2f}s{map_flag}")
        if not has_map and not args.no_map_inset:
            no_map_holes.append(hole)

    # Chain with vertical drop-in transitions.
    video_only = os.path.join(TMP_DIR, "video_only.mp4")
    vid_dur = chain_xfade(segments, durations, args.transition,
                          args.transition_duration, video_only)
    vid_dur = mr.duration_of(video_only)
    print(f"\nStitched video length: {vid_dur:.1f}s "
          f"({args.transition} transitions, {args.transition_duration:g}s each)")

    budget = mr.word_budget(vid_dur)
    print(f"Script budget: about {budget} words of narration fit this reel "
          f"(~{mr.WPM} words/min).")

    # Audio.
    base = os.path.join(TMP_DIR, "base.mp4")
    if args.sound == "none":
        shutil.copyfile(video_only, base)
    else:
        vo = args.vo
        if not vo:
            cand = [os.path.join(VO_DIR, n) for n in sorted(os.listdir(VO_DIR))
                    if os.path.splitext(n)[1].lower() in
                    {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}]
            if not cand:
                sys.exit("ERROR: --sound voiceover but no --vo given and "
                         "./voiceover/ has no audio file.")
            vo = cand[0]
        if not os.path.exists(vo):
            sys.exit(f"ERROR: voiceover file not found: {vo}")
        vo_dur = mr.duration_of(vo)
        print(f"Voiceover: {os.path.basename(vo)} ({vo_dur:.1f}s)")
        if vo_dur > vid_dur + 0.3:
            print(f"  WARNING: the voiceover ({vo_dur:.1f}s) is longer than the "
                  f"visuals ({vid_dur:.1f}s). The end will be cut off - raise "
                  f"--target-seconds or shorten the script.")
        mr.run(["-i", video_only, "-i", vo,
                "-filter_complex",
                f"[1:a]aresample=48000,apad,atrim=0:{vid_dur:.3f},"
                f"asetpts=PTS-STARTPTS[a]",
                "-map", "0:v:0", "-map", "[a]",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
                "-shortest", base], "mux")

    base_dur = mr.duration_of(base)
    current = base

    # Captions.
    if args.subtitles != "none":
        srt_path = os.path.join(TMP_DIR, "subs.srt")
        if args.subtitles == "file":
            if not args.sub_file or not os.path.exists(args.sub_file):
                sys.exit("ERROR: --subtitles file requires an existing --sub-file <path.srt>.")
            shutil.copyfile(args.sub_file, srt_path)
        else:
            src = args.sub_script or os.path.join(PROMPTS_DIR, "script.txt")
            if not os.path.exists(src):
                sys.exit(f"ERROR: --subtitles auto needs script text. Provide "
                         f"--sub-script <file> or create prompts/script.txt "
                         f"(not found: {src}).")
            captions = mr.split_captions(Path(src).read_text(encoding="utf-8"))
            if not captions:
                sys.exit("ERROR: subtitle script is empty.")
            mr.write_srt(captions, base_dur, srt_path)
            print(f"Captions: {len(captions)} lines over {base_dur:.1f}s")
        withsubs = os.path.join(TMP_DIR, "withsubs.mp4")
        burn_ass(current, withsubs, srt_path, style=mr.SUB_STYLE)
        current = withsubs

    # Intro title (e.g. the course name).
    if args.title:
        title_ass = os.path.join(TMP_DIR, "title.ass")
        mr.write_title_ass(title_ass, base_dur, args.title,
                           seconds=args.title_seconds,
                           fontsize=args.title_fontsize,
                           position=args.title_position, font=args.font)
        withtitle = os.path.join(TMP_DIR, "withtitle.mp4")
        burn_ass(current, withtitle, title_ass)
        current = withtitle
        span = ("whole reel" if args.title_seconds <= 0
                else f"first {min(args.title_seconds, base_dur):.1f}s")
        print(f"Title: \"{args.title}\" ({args.title_position}, {span}).")

    # Timer.
    if args.timer:
        target = (mr.parse_duration(args.timer_seconds)
                  if args.timer_seconds is not None else base_dur)
        ass_path = os.path.join(TMP_DIR, "timer.ass")
        mr.write_timer_ass(ass_path, base_dur, target, fps=mr.FPS,
                           fontsize=args.timer_fontsize,
                           position=args.timer_position,
                           direction=args.timer_direction,
                           font=args.timer_font or args.font)
        withtimer = os.path.join(TMP_DIR, "withtimer.mp4")
        burn_ass(current, withtimer, ass_path)
        current = withtimer
        shown = mr._fmt_timer(target, target >= 3600)
        span = (f"{shown} -> 00:00.00" if args.timer_direction == "down"
                else f"00:00.00 -> {shown}")
        print(f"Timer: {span} across the {base_dur:.1f}s reel ({args.timer_position}).")

    # Finalize.
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    final_path = os.path.join(FINAL_DIR, f"golf_reel_{stamp}.mp4")
    shutil.copyfile(current, final_path)

    shutil.rmtree(TMP_DIR, ignore_errors=True)
    elapsed = time.time() - t_start
    print("\n" + "=" * 60)
    print("GOLF REEL READY")
    print("=" * 60)
    holes_line = f"Holes:    {args.nine} ({n_holes})"
    if missing:
        holes_line += f", {len(missing)} blank placeholder(s)"
    print(f"File:     {final_path}")
    print(holes_line)
    if not args.no_map_inset:
        if no_map_holes:
            print(f"Map:      no layout thumbnail for hole(s) "
                  f"{', '.join(str(h) for h in no_map_holes)}")
        else:
            print("Map:      layout thumbnail inset on every hole")
    print(f"Length:   {mr.duration_of(final_path):.1f}s   "
          f"Format: {mr.TARGET_W}x{mr.TARGET_H} (9:16)")
    print(f"Built in: {elapsed:.2f}s")
    print("Upload this to Instagram as a Reel.")
    if args.sound == "none":
        print("Tip: add music on Instagram's 'Add audio' screen during upload.")
    print("=" * 60)


if __name__ == "__main__":
    main()
