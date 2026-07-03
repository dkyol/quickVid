#!/usr/bin/env python3
"""
script_fit.py — Once your photos/videos are in ./media/, this tells you how LONG
the reel will be and therefore how many WORDS of voiceover/caption script fit.
Run it BEFORE generating a voiceover so the narration matches the visuals; if the
script is too long, summarize it down to the reported budget first.

It does NOT render anything (fast): it just adds up the still durations and the
real length of each video clip, using the same rules as make_reel.py.

    python script_fit.py                     # projected length + word budget
    python script_fit.py --image-seconds 4   # match your make_reel.py setting
    python script_fit.py --max-clip-seconds 6
    python script_fit.py --script prompts/script.txt   # also grades your script

Plan for a TARGET length (recommends the photo-flash speed to hit it):
    python script_fit.py --target 20            # aim for a 20s reel
    python script_fit.py --band sweet-spot      # 15-30s -> uses the midpoint

Length bands: max-reach 7-15s, sweet-spot 15-30s, deep 30-60s, long-form 60-1200s.
Speaking pace defaults to ~150 words/minute; change it with --wpm.
"""

import argparse
import os
import sys

import make_reel as mr  # reuse media discovery, ffprobe, and the word-budget math


def project_duration(image_seconds, max_clip_seconds):
    total = 0.0
    n_img = n_vid = 0
    for f in mr.gather_media():
        ext = os.path.splitext(f)[1].lower()
        if ext in mr.IMAGE_EXT:
            total += image_seconds
            n_img += 1
        else:
            d = mr.duration_of(f)
            if max_clip_seconds and d > max_clip_seconds:
                d = max_clip_seconds
            total += d
            n_vid += 1
    return total, n_img, n_vid


def main():
    ap = argparse.ArgumentParser(description="Report the reel length and the "
                                             "voiceover/script word budget.")
    ap.add_argument("--target", default=None,
                    help="Target TOTAL reel length ('MM:SS' or seconds). Recommends "
                         "the photo-flash speed to hit it.")
    ap.add_argument("--band", choices=list(mr.LENGTH_BANDS),
                    help="Length band instead of --target; uses the band midpoint.")
    ap.add_argument("--image-seconds", type=float, default=3.0,
                    help="Seconds each still photo is shown (match make_reel.py). "
                         "Ignored when --target/--band is given.")
    ap.add_argument("--max-clip-seconds", type=float, default=0.0,
                    help="Cap each source video at this many seconds (0 = full).")
    ap.add_argument("--wpm", type=float, default=mr.WPM,
                    help=f"Narration pace in words/minute (default {mr.WPM}).")
    ap.add_argument("--script", default=os.path.join(mr.ROOT, "prompts", "script.txt"),
                    help="Script text file to grade against the budget.")
    args = ap.parse_args()

    max_clip = args.max_clip_seconds or None
    image_seconds = args.image_seconds
    target = None
    if args.band:
        lo, hi = mr.LENGTH_BANDS[args.band]
        target = (lo + hi) / 2
    if args.target is not None:
        target = mr.parse_duration(args.target)

    if target is not None:
        media = mr.gather_media()
        plan = mr.plan_pacing(media, target, max_clip=max_clip)
        n_img, n_vid = plan["n_img"], plan["n_vid"]
        if plan["image_seconds"] is not None:
            image_seconds = plan["image_seconds"]
        dur = plan["total"]
        print("=" * 60)
        print("LENGTH PLAN")
        print("=" * 60)
        print(f"Target:       {target:g}s")
        print(f"Media:        {n_img} photo(s) + {n_vid} clip(s) "
              f"({plan['video_time']:.1f}s of video)")
        if plan["image_seconds"] is not None:
            print(f"Recommended:  photos flash at {image_seconds:.2f}s each  "
                  f"(build with: make_reel.py --target-seconds {target:g})")
        for note in plan["notes"]:
            print(f"  NOTE: {note}")
        print(f"Projected:    ~{dur:.1f}s")
        print("-" * 60)
    else:
        dur, n_img, n_vid = project_duration(image_seconds, args.max_clip_seconds)

    budget = mr.word_budget(dur, args.wpm)
    # a comfortable window: a bit slower .. a bit faster than the target pace
    low = mr.word_budget(dur, args.wpm - 20)
    high = mr.word_budget(dur, args.wpm + 15)

    print("=" * 60)
    print("REEL LENGTH & SCRIPT BUDGET")
    print("=" * 60)
    print(f"Media:        {n_img} photo(s) @ {image_seconds:g}s + "
          f"{n_vid} video clip(s)")
    print(f"Reel length:  ~{dur:.1f}s")
    print(f"Voiceover budget: about {budget} words  "
          f"(comfortable range {low}-{high} words at ~{args.wpm:g} wpm)")

    if os.path.exists(args.script):
        text = open(args.script, encoding="utf-8").read()
        have = mr.count_words(text)
        print("-" * 60)
        print(f"Your script ({os.path.relpath(args.script, mr.ROOT)}): {have} words")
        if have <= high:
            print("  -> Fits. Good to generate the voiceover.")
        else:
            over = have - budget
            secs_over = over / (args.wpm / 60)
            print(f"  -> TOO LONG by ~{over} words (~{secs_over:.0f}s of extra "
                  f"speech). Summarize it down to about {budget} words, or add "
                  f"more/longer media, or build with --fit-audio to stretch the "
                  f"visuals to the voiceover.")
    else:
        print("-" * 60)
        print(f"No script found at {os.path.relpath(args.script, mr.ROOT)}. "
              f"Aim for about {budget} words when you write it.")
    print("=" * 60)


if __name__ == "__main__":
    main()
