#!/usr/bin/env python3
"""
plan_seeds.py — Given a reference video you want to replicate, work out HOW
MANY seed frames you need and WHERE (their timestamps), extract the
reference frame at each of those moments so you can recreate them in your
own style, and scaffold a shots.json wired to those seeds.

Why seeds at intervals? image_to_video locks only the FIRST frame and then
drifts over a few seconds. To hold a reference's look/pacing across a longer
clip you re-seed periodically: each seed anchors the start of a segment,
build_reel.py stitches the segments with crossfades. Default: one seed every
4 s (override with --every), which keeps each generated segment inside the
window where it stays faithful to its seed.

Usage:
    python plan_seeds.py "C:/path/to/reference.mp4" --project wolf_reel
    python plan_seeds.py "ref.mp4" --project wolf_reel --every 3
    python plan_seeds.py "ref.mp4" --project wolf_reel --count 3

Outputs (under <repo>/<project>/):
    reference_frames/ref_TT.TTs.png   one extracted frame per seed moment
    shots.planned.json                a shots.json scaffold; fill in prompts,
                                      supply your seed images, then rename to
                                      shots.json and run generate_shots.py.

You then create ONE seed image per moment (your wolf version of that exact
frame), drop them in <project>/seeds/ named seed_01.png, seed_02.png, ...,
and run the normal pipeline. See imageGenSkill.MD sections 3 and 6.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def _find(binary):
    local = os.path.join(ROOT, "tools", binary + ".exe")
    if os.path.exists(local):
        return local
    onpath = shutil.which(binary)
    if onpath:
        return onpath
    sys.exit(f"ERROR: could not find {binary}. Put {binary}.exe in ./tools/.")


FF = _find("ffmpeg")
FFPROBE = _find("ffprobe")


def duration_of(path):
    r = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    try:
        return float(r.stdout.strip())
    except ValueError:
        sys.exit(f"ERROR: could not read duration of {path}")


def extract_frame(video, t, dst):
    subprocess.run([FF, "-y", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1",
                    "-q:v", "2", dst], capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reference", help="Path to the reference video to replicate.")
    ap.add_argument("--project", required=True,
                     help="Project folder name under the repo root.")
    ap.add_argument("--every", type=float, default=4.0,
                     help="Seconds between seeds (default 4). Lower = more "
                          "seeds, tighter fidelity, more generations/cost.")
    ap.add_argument("--count", type=int, default=None,
                     help="Force exactly this many seeds (overrides --every); "
                          "they are spread evenly across the reference.")
    ap.add_argument("--aspect-ratio", default="9:16")
    args = ap.parse_args()

    if not os.path.isfile(args.reference):
        sys.exit(f"ERROR: reference video not found: {args.reference}")

    dur = duration_of(args.reference)
    project_root = os.path.join(ROOT, args.project)
    frames_dir = os.path.join(project_root, "reference_frames")
    seeds_dir = os.path.join(project_root, "seeds")
    os.makedirs(frames_dir, exist_ok=True)
    os.makedirs(seeds_dir, exist_ok=True)

    # Seed timestamps = the START of each segment.
    if args.count:
        n = max(1, args.count)
        # Evenly spaced starts across the clip (last start leaves one segment).
        if n == 1:
            starts = [0.0]
        else:
            step = dur / n
            starts = [round(i * step, 2) for i in range(n)]
    else:
        starts = [round(t, 2) for t in _frange(0.0, dur, args.every)]
        if not starts:
            starts = [0.0]
    # Segment boundaries: each segment runs from its start to the next start
    # (last one to end of clip).
    bounds = starts + [round(dur, 2)]

    print(f"Reference: {args.reference}")
    print(f"Duration : {dur:.2f}s")
    print(f"Plan     : {len(starts)} seed(s), one every "
          f"~{args.every if not args.count else round(dur/len(starts),2)}s\n")

    shots = []
    for i, t in enumerate(starts, start=1):
        seg_len = round(bounds[i] - bounds[i - 1], 2)
        frame_name = f"ref_{t:05.2f}s.png"
        frame_path = os.path.join(frames_dir, frame_name)
        extract_frame(args.reference, t, frame_path)
        seed_name = f"seed_{i:02d}.png"
        print(f"  Seed {i:>2}: reference t={t:>6.2f}s  ->  segment {seg_len:>5.2f}s")
        print(f"          reference frame : {os.path.relpath(frame_path, ROOT)}")
        print(f"          you provide     : {args.project}/seeds/{seed_name}")
        shots.append({
            "name": f"{i:02d}_seg",
            "type": "image_to_video",
            "seed": seed_name,
            "duration": int(round(seg_len)) if seg_len >= 1 else 1,
            "seconds": seg_len,
            "prompt": "DESCRIBE the carving motion for this segment "
                      "(what the knife reveals between this seed and the next)."
        })

    scaffold = {
        "project": args.project,
        "crossfade": 0.3,
        "width": 1080, "height": 1920, "fps": 30,
        "image_model": "grok-imagine-image",
        "video_model": "grok-imagine-video",
        "aspect_ratio": args.aspect_ratio,
        "shots": shots,
    }
    out = os.path.join(project_root, "shots.planned.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(scaffold, f, indent=2)

    print(f"\nWrote scaffold -> {os.path.relpath(out, ROOT)}")
    print("Next: recreate each reference frame above as your own seed image, "
          f"save as {args.project}/seeds/seed_01.png .. seed_{len(starts):02d}.png, "
          "fill in each shot's prompt, rename shots.planned.json -> shots.json, "
          "then: python generate_shots.py --shots "
          f"{args.project}/shots.json && python build_reel.py --shots "
          f"{args.project}/shots.json")


def _frange(start, stop, step):
    vals, t = [], start
    while t < stop - 0.01:
        vals.append(t)
        t += step
    return vals


if __name__ == "__main__":
    main()
