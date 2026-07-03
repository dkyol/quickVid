#!/usr/bin/env python3
"""
add_timer.py — Burn a running timer (precise to 1/100 s) over an already finished
reel. Use this AFTER the video is built, once you know how long it took to make.

By default it COUNTS DOWN: it starts at the time you say it took to create the
reel and reaches 00:00.00 exactly at the end of the video, compressed into the
reel's length. Example: "this reel took 23 minutes" on a 45s reel shows 23:00.00
at the start and ticks down to 00:00.00 over those 45 seconds.

    # countdown from how long it took you to make it (23 minutes) to zero:
    python add_timer.py --seconds 23:00
    python add_timer.py --seconds 1380           # same, in plain seconds

    # count UP instead (0 -> the value):
    python add_timer.py --seconds 23:00 --direction up

    # no --seconds: counts down from the reel's own length to zero:
    python add_timer.py

    # target a specific input / position / size:
    python add_timer.py --input final/reel_20260703_120000.mp4 \
                        --position middle --fontsize 90

Default input is the newest final/reel_*.mp4. Output is a new timestamped file
final/reel_<stamp>_timer.mp4 — the original is never overwritten.
"""

import argparse
import datetime
import glob
import os
import shutil
import sys

import make_reel as mr  # reuse ffmpeg discovery, the ASS timer builder, and burn


def newest_reel():
    reels = [f for f in glob.glob(os.path.join(mr.FINAL_DIR, "reel_*.mp4"))
             if "_timer" not in os.path.basename(f)]
    if not reels:
        sys.exit("ERROR: no final/reel_*.mp4 found. Build a reel first "
                 "(make_reel.py), then run add_timer.py.")
    return max(reels, key=os.path.getmtime)


def main():
    ap = argparse.ArgumentParser(description="Overlay a 1/100 s stopwatch on a reel.")
    ap.add_argument("--input", default=None,
                    help="Reel to stamp (default: newest final/reel_*.mp4).")
    ap.add_argument("--seconds", default=None,
                    help="How long it took to create this ('MM:SS.cc', "
                         "'HH:MM:SS.cc', or plain seconds). Default: reel length.")
    ap.add_argument("--direction", choices=["down", "up"], default="down",
                    help="down (default): start at --seconds, count to 0. "
                         "up: start at 0, count up to --seconds.")
    ap.add_argument("--position", choices=["top", "middle", "bottom"],
                    default="top", help="Where the timer sits (default top).")
    ap.add_argument("--fontsize", type=int, default=72,
                    help="Timer font size in px (default 72).")
    args = ap.parse_args()

    src = args.input or newest_reel()
    if not os.path.exists(src):
        sys.exit(f"ERROR: input not found: {src}")
    dur = mr.duration_of(src)
    target = mr.parse_duration(args.seconds) if args.seconds is not None else dur

    tmp = os.path.join(mr.ROOT, "_tmp_timer")
    os.makedirs(tmp, exist_ok=True)
    mr.TMP_DIR = tmp  # burn_subs runs ffmpeg with cwd=mr.TMP_DIR
    ass_path = os.path.join(tmp, "timer.ass")
    mr.write_timer_ass(ass_path, dur, target, fps=mr.FPS,
                       fontsize=args.fontsize, position=args.position,
                       direction=args.direction)

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = os.path.join(mr.FINAL_DIR, f"reel_{stamp}_timer.mp4")
    mr.burn_subs(src, out, "timer.ass")
    shutil.rmtree(tmp, ignore_errors=True)

    shown = mr._fmt_timer(target, target >= 3600)
    span = (f"{shown} -> 00:00.00" if args.direction == "down"
            else f"00:00.00 -> {shown}")
    print("\n" + "=" * 60)
    print("TIMER ADDED")
    print("=" * 60)
    print(f"Source:  {os.path.basename(src)}  ({dur:.2f}s)")
    print(f"Timer:   {span}  ({args.direction}, {args.position}, {mr.FPS} fps)")
    print(f"Output:  {out}")
    print("=" * 60)


if __name__ == "__main__":
    main()
