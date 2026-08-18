#!/usr/bin/env python3
"""
stitch_video.py — driver for SKILLS/stitchImageVideo.MD.

Chains N unrelated still images into one reel: one image-to-video
continuation per image on Google Veo (no last_frame/end-frame — each image
is an independent scene, there is no "next real frame" to land on), each
clip trimmed to end before it drifts away from what its seed photo actually
shows, joined with a blur-whip + speed-ramp transition that hides the hard
cut between two unrelated scenes.

Reuses veo_carve.py's Google API plumbing (client, generate, retry/quota
handling, aspect-letterbox guard) unchanged rather than re-deriving it — see
that file for the measured constraints (last_frame/1080p duration rules,
429-vs-503 handling) this script inherits by calling straight into it.

Three phases, run in order, each a separate subcommand:
  generate  — one raw i2v clip per image (paid; supports --takes/--rank/
              --promote exactly like veo_carve.py)
  sheet     — free ffmpeg contact sheet per clip, for finding the
              divergence point BY EYE (see stitchImageVideo.MD — do not
              trust score_clip's drift number alone, it's a shortlist tool)
  assemble  — free ffmpeg trim + blur-whip transition + concat, once every
              image's "cut_at" is filled in the job file

Job schema (jobs/<name>.json):
{
  "project": "trail_stitch",
  "model": "veo-3.1-lite-generate-preview",
  "aspect_ratio": "9:16",
  "resolution": "1080p",
  "duration": 8,
  "negative_prompt": "text overlays, watermark",
  "transition": {
    "whip_seconds": 0.4,     // how much source footage each whip eats, at
                              // both the tail of the outgoing clip and the
                              // head of the incoming clip
    "speed": 2.5,             // compression factor during the whip
    "xfade_seconds": 0.08,    // crossfade duration inside the whip
    "blur_sigma": 14          // constant gblur strength during the whip —
                              // see "known simplification" below
  },
  "images": [
    { "name": "01_trailhead", "seed": "seeds/trailhead.jpg",
      "prompt": "Continue this exact scene naturally, camera moving "
                "forward along the trail at a steady walking pace. Do not "
                "introduce any new people, animals, structures, or objects "
                "not already visible in the frame.",
      "negative_prompt": "new people, new buildings, sudden scene change",
      "cut_at": null }
  ]
}

`cut_at` is seconds into the RAW generated clip where you want the trim to
land — filled in by you after scrubbing the contact sheet, not computed by
this script. That human judgment call is the entire point of the technique
(see stitchImageVideo.MD's QC section); this script deliberately refuses to
assemble until every image has one.

Optional per-image `"speed"` (playback-rate multiplier, default 1.0) is
applied to the body segment only (not the whip, which has its own `speed` in
`transition`) — use it to equalize how fast forward-motion *reads* across
clips shot at different apparent paces, independent of `cut_at`.

Known simplification (see stitchImageVideo.MD "Open items"): the blur
during each whip is a CONSTANT sigma across the whole (very short, ~4-5
frame) whip window, not a per-frame ramp — ffmpeg's gblur does not reliably
support a time-varying sigma expression across builds, and at this length a
constant blur combined with the speed compression and crossfade reads fine
in practice. A directional/zoom blur is the noted upgrade path if a
constant gaussian blur doesn't sell the whip on real footage.

Usage:
    python stitch_video.py jobs/trail_stitch.json generate --dry-run
    python stitch_video.py jobs/trail_stitch.json generate
    python stitch_video.py jobs/trail_stitch.json generate --image 01_trailhead --takes 3
    python stitch_video.py jobs/trail_stitch.json rank --image 01_trailhead
    python stitch_video.py jobs/trail_stitch.json promote --image 01_trailhead --take 2
    python stitch_video.py jobs/trail_stitch.json sheet --image 01_trailhead --fps 4
    python stitch_video.py jobs/trail_stitch.json assemble
"""

import argparse
import glob
import json
import math
import os
import shutil
import subprocess
import sys
import time

from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(ROOT, ".env"))

from carvegen.seeds import resolve_seed as resolve_seed_path
from veo_carve import (
    QuotaExhausted,
    check_seed_aspect,
    client,
    generate as veo_generate,
    score_clip,
)

LITE_MODEL = "veo-3.1-lite-generate-preview"
DEFAULT_TRANSITION = {
    "whip_seconds": 0.4,
    "speed": 2.5,
    "xfade_seconds": 0.08,
    "blur_sigma": 14,
}


def _ff():
    local = os.path.join(ROOT, "tools", "ffmpeg.exe")
    return local if os.path.exists(local) else "ffmpeg"


def _ffprobe():
    local = os.path.join(ROOT, "tools", "ffprobe.exe")
    return local if os.path.exists(local) else "ffprobe"


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"ERROR: command failed:\n{' '.join(cmd)}\n{r.stderr[-2000:]}")
    return r


def probe_duration(path):
    r = subprocess.run(
        [_ffprobe(), "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        sys.exit(f"ERROR: could not probe duration of {path}\n{r.stderr}")


def load_job(path):
    with open(path, "r", encoding="utf-8") as f:
        job = json.load(f)
    proj_dir = os.path.join(ROOT, job["project"])
    for sub in ("seeds", "media", "cut", "final", "contact_sheets"):
        os.makedirs(os.path.join(proj_dir, sub), exist_ok=True)
    job.setdefault("transition", {})
    for k, v in DEFAULT_TRANSITION.items():
        job["transition"].setdefault(k, v)
    return job, proj_dir


def raw_clip_path(proj_dir, name):
    return os.path.join(proj_dir, "media", f"veo_{name}.mp4")


def find_image(job, name):
    for im in job["images"]:
        if im["name"] == name:
            return im
    sys.exit(f"ERROR: no image named {name!r}. "
             f"Images: {', '.join(i['name'] for i in job['images'])}")


# --------------------------------------------------------------------------
# generate
# --------------------------------------------------------------------------

def cmd_generate(args, job, proj_dir):
    model = job.get("model", LITE_MODEL)
    aspect = job.get("aspect_ratio", "9:16")
    resolution = job.get("resolution", "1080p")
    duration = int(job.get("duration", 8))
    job_negative = job.get("negative_prompt")

    images = [im for im in job["images"]
              if not args.image or im["name"] == args.image]
    if args.image and not images:
        find_image(job, args.image)  # raises with the name list

    cl = None if args.dry_run else client()
    media_dir = os.path.join(proj_dir, "media")
    failed = []

    for im in images:
        name = im["name"]
        seed = resolve_seed_path(im["seed"], proj_dir)
        prompt = im["prompt"]
        negative = im.get("negative_prompt", job_negative)
        im_duration = int(im.get("duration", duration))

        if args.dry_run:
            print(f"\n=== {name} [i2v, no end frame] {os.path.basename(seed)}"
                  f"\n{prompt}"
                  f"\n  negative_prompt: {negative}"
                  f"\n  model={model} aspect={aspect} resolution={resolution} "
                  f"duration={im_duration}")
            continue

        check_seed_aspect(seed, aspect)

        want = args.takes if args.takes is not None else int(im.get("takes", 1))
        dst = raw_clip_path(proj_dir, name)
        targets = ([dst] if want == 1 else
                   [os.path.join(media_dir, f"veo_{name}_take{k}.mp4")
                    for k in range(1, want + 1)])

        got = 0
        for target in targets:
            if os.path.isfile(target) and not args.force:
                print(f"[skip] {os.path.basename(target)} exists")
                got += 1
                continue
            print(f"[{name}] generating -> {os.path.basename(target)}")
            out = veo_generate(cl, prompt, seed, target,
                               seed_end_path=None, model=model, aspect=aspect,
                               resolution=resolution, duration=im_duration,
                               negative=negative)
            if out:
                print(f"  -> {os.path.basename(target)}")
                got += 1
        if got == 0:
            failed.append(name)

    if args.dry_run:
        print("\n(dry run — nothing generated)")
    elif failed:
        sys.exit(f"\n{len(failed)} image(s) FAILED and need a re-roll: "
                 f"{', '.join(failed)}")


# --------------------------------------------------------------------------
# rank / promote — thin wrappers on veo_carve.score_clip, same caveats
# --------------------------------------------------------------------------

def cmd_rank(args, job, proj_dir):
    media_dir = os.path.join(proj_dir, "media")
    images = [im for im in job["images"]
              if not args.image or im["name"] == args.image]
    for im in images:
        name = im["name"]
        takes = sorted(glob.glob(os.path.join(media_dir, f"veo_{name}_take*.mp4")))
        if not takes:
            continue
        seed = resolve_seed_path(im["seed"], proj_dir)
        rows = []
        for t in takes:
            s = score_clip(t, seed_path=seed)
            if s:
                rows.append((s, os.path.basename(t)))
        if not rows:
            continue
        rows.sort(key=lambda r: (1e9 if math.isnan(r[0]["drift"]) else r[0]["drift"],
                                 r[0]["spike"]))
        print(f"\n{name}  (best first by 'drift' — SHORTLIST ONLY, eyeball "
              f"the actual clip before promoting; see stitchImageVideo.MD)")
        print(f"   {'take':40s} {'step':>7s} {'spike':>7s} {'drift':>7s} {'motion':>7s}")
        for s, fn in rows:
            def f(v):
                return "   -  " if math.isnan(v) else f"{v:6.1f}"
            print(f"   {fn:40s} {f(s['step'])} {f(s['spike'])} "
                  f"{f(s['drift'])} {f(s['motion'])}")


def cmd_promote(args, job, proj_dir):
    if not args.image or not args.take:
        sys.exit("ERROR: promote needs --image NAME --take K")
    media_dir = os.path.join(proj_dir, "media")
    src = os.path.join(media_dir, f"veo_{args.image}_take{args.take}.mp4")
    if not os.path.isfile(src):
        sys.exit(f"ERROR: take not found: {src}")
    dst = raw_clip_path(proj_dir, args.image)
    shutil.copyfile(src, dst)
    print(f"promoted {os.path.basename(src)} -> {os.path.basename(dst)}")


# --------------------------------------------------------------------------
# sheet — free contact-sheet scrub, the mandatory full-clip QC step
# --------------------------------------------------------------------------

def cmd_sheet(args, job, proj_dir):
    images = [im for im in job["images"]
              if not args.image or im["name"] == args.image]
    if args.image and not images:
        find_image(job, args.image)

    out_dir = os.path.join(proj_dir, "contact_sheets")
    for im in images:
        name = im["name"]
        clip = raw_clip_path(proj_dir, name)
        if not os.path.isfile(clip):
            print(f"[skip] {name}: no raw clip at {clip} yet")
            continue
        dur = probe_duration(clip)
        n_frames = max(1, math.ceil(dur * args.fps))
        cols = min(6, n_frames)
        rows = math.ceil(n_frames / cols)
        dst = os.path.join(out_dir, f"{name}_sheet.png")
        # No burned-in timestamp: drawtext needs a fontconfig/font-file setup
        # this machine's bundled ffmpeg.exe may not have, and a failed
        # drawtext call would take the whole sheet down with it. Tile index
        # -> time is a fixed formula instead (printed below) — reading off
        # "3rd tile, 2nd row" is enough to know the timestamp to the
        # 1/fps precision this step needs anyway.
        _run([_ff(), "-y", "-i", clip, "-vf",
              f"fps={args.fps},scale=240:-1,tile={cols}x{rows}",
              "-frames:v", "1", dst])
        print(f"[{name}] {dur:.1f}s @ {args.fps}fps -> {dst}")
        print(f"  {n_frames} frames, {cols} cols x {rows} rows, "
              f"left-to-right then top-to-bottom. "
              f"tile index k (0-based) = t = k / {args.fps} seconds.")
    print("\nScrub every sheet for the frame where content stops matching "
          "the seed photo. Then edit the job's \"cut_at\" for that image "
          "(seconds, with margin BEFORE that frame) and re-save.")


# --------------------------------------------------------------------------
# assemble — free trim + blur-whip transition + concat
# --------------------------------------------------------------------------

def _trim_segment(src, start, end, dst, extra_vf=None):
    dur = end - start
    if dur <= 0:
        sys.exit(f"ERROR: non-positive segment duration ({dur:.3f}s) trimming "
                 f"{src} [{start:.3f},{end:.3f}] — cut_at/whip_seconds don't "
                 f"leave room for a body segment; shorten whip_seconds or "
                 f"pick a later cut_at.")
    vf = "setpts=PTS-STARTPTS"
    if extra_vf:
        vf += "," + extra_vf
    # -ss/-t BEFORE -i so both are input options: exactly `dur` seconds of
    # SOURCE are read regardless of what a downstream setpts speed-change
    # does to the output timeline. Putting -t after -i makes ffmpeg treat it
    # as an OUTPUT duration cap instead — measured concretely on this
    # script: with that ordering, a 2.5x speed-up whip clip that should
    # compress to 0.16s instead came back at the full pre-speedup 0.4s,
    # because ffmpeg kept pulling source frames until the OUTPUT timeline
    # (already running fast) filled the requested 0.4s window, silently
    # reading extra source past the intended trim boundary.
    _run([_ff(), "-y", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", src,
          "-vf", vf, "-an", "-c:v", "libx264", "-crf", "16", "-preset",
          "slow", "-pix_fmt", "yuv420p", dst])


def _build_whip(src, start, end, speed, sigma, dst):
    """Trim [start,end], compress by `speed`, apply a constant blur.
    See module docstring for why the blur is constant, not ramped."""
    vf = (f"setpts=PTS-STARTPTS,setpts={1/speed:.6f}*PTS,"
          f"gblur=sigma={sigma}")
    _trim_segment(src, start, end, dst, extra_vf=vf)
    return (end - start) / speed


def _xfade(a, b, xfade_dur, dst):
    dur_a = probe_duration(a)
    offset = max(0.0, dur_a - xfade_dur)
    filt = f"[0:v][1:v]xfade=transition=fade:duration={xfade_dur:.3f}:offset={offset:.3f}[v]"
    _run([_ff(), "-y", "-i", a, "-i", b, "-filter_complex", filt,
          "-map", "[v]", "-an", "-c:v", "libx264", "-crf", "16",
          "-preset", "slow", "-pix_fmt", "yuv420p", dst])


def cmd_assemble(args, job, proj_dir):
    images = job["images"]
    if len(images) < 1:
        sys.exit("ERROR: job has no images")

    missing = [im["name"] for im in images if im.get("cut_at") is None]
    if missing:
        sys.exit(f"ERROR: cut_at not set for: {', '.join(missing)}. "
                 f"Run `sheet`, scrub the contact sheet by eye, and fill "
                 f"in cut_at (seconds) for every image before assembling — "
                 f"see stitchImageVideo.MD, this is a deliberate gate, not "
                 f"a missing feature.")

    t = job["transition"]
    whip = float(t["whip_seconds"])
    speed = float(t["speed"])
    xfade_dur = float(t["xfade_seconds"])
    sigma = t["blur_sigma"]

    cut_dir = os.path.join(proj_dir, "cut")
    n = len(images)
    segments = []  # ordered list of file paths to concat

    for i, im in enumerate(images):
        name = im["name"]
        clip = raw_clip_path(proj_dir, name)
        if not os.path.isfile(clip):
            sys.exit(f"ERROR: no raw clip for {name} at {clip} — run "
                     f"`generate` first.")
        cut_at = float(im["cut_at"])
        has_prev = i > 0
        has_next = i < n - 1
        reserve_head = whip if has_prev else 0.0
        reserve_tail = whip if has_next else 0.0

        body_speed = float(im.get("speed", 1.0))
        body_vf = f"setpts={1/body_speed:.6f}*PTS" if body_speed != 1.0 else None
        body_dst = os.path.join(cut_dir, f"{name}_body.mp4")
        _trim_segment(clip, reserve_head, cut_at - reserve_tail, body_dst,
                      extra_vf=body_vf)

        if has_prev:
            in_dst = os.path.join(cut_dir, f"{name}_in.mp4")
            _build_whip(clip, 0.0, whip, speed, sigma, in_dst)
            trans_dst = os.path.join(cut_dir, f"{images[i-1]['name']}__{name}_trans.mp4")
            _xfade(segments.pop(), in_dst, min(xfade_dur, whip / speed), trans_dst)
            segments.append(trans_dst)

        segments.append(body_dst)

        if has_next:
            out_dst = os.path.join(cut_dir, f"{name}_out.mp4")
            _build_whip(clip, cut_at - whip, cut_at, speed, sigma, out_dst)
            segments.append(out_dst)
        print(f"[{name}] body {reserve_head:.2f}-{cut_at - reserve_tail:.2f}s"
              f"{' + head whip' if has_prev else ''}"
              f"{' + tail whip' if has_next else ''}")

    stamp = time.strftime("%Y%m%d_%H%M%S")
    final_dst = os.path.join(proj_dir, "final", f"stitch_{job['project']}_{stamp}.mp4")

    inputs = []
    for s in segments:
        inputs += ["-i", s]
    concat_inputs = "".join(f"[{i}:v]" for i in range(len(segments)))
    filt = f"{concat_inputs}concat=n={len(segments)}:v=1:a=0[v]"
    _run([_ff(), "-y", *inputs, "-filter_complex", filt, "-map", "[v]",
          "-c:v", "libx264", "-crf", "18", "-preset", "slow",
          "-pix_fmt", "yuv420p", final_dst])

    print(f"\n-> {final_dst}")
    print("No audio bed included — this is silent b-roll by construction "
          "(native Veo audio across unrelated scenes won't cohere as a "
          "soundtrack; see stitchImageVideo.MD step 8). Add a music bed "
          "over the final file separately.")


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate")
    g.add_argument("--image", default=None)
    g.add_argument("--takes", type=int, default=None)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--force", action="store_true")
    g.set_defaults(func=cmd_generate)

    r = sub.add_parser("rank")
    r.add_argument("--image", default=None)
    r.set_defaults(func=cmd_rank)

    p = sub.add_parser("promote")
    p.add_argument("--image", required=True)
    p.add_argument("--take", required=True)
    p.set_defaults(func=cmd_promote)

    s = sub.add_parser("sheet")
    s.add_argument("--image", default=None)
    s.add_argument("--fps", type=float, default=4.0)
    s.set_defaults(func=cmd_sheet)

    a = sub.add_parser("assemble")
    a.set_defaults(func=cmd_assemble)

    args = ap.parse_args()
    job, proj_dir = load_job(args.job)
    args.func(args, job, proj_dir)


if __name__ == "__main__":
    try:
        main()
    except QuotaExhausted as e:
        sys.exit(
            "\n================ STOPPED: quota exhausted (429) ================\n"
            f"{e}\n\n"
            "NOT retried, and remaining images were NOT attempted. This error\n"
            "cannot tell a per-model daily limit apart from a project safety\n"
            "quota — see veo_carve.py's QuotaExhausted docstring for the full\n"
            "explanation. Check billing/quotas before re-running; completed\n"
            "clips are already saved and generate will skip them.\n"
            "===============================================================")
