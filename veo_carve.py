#!/usr/bin/env python3
"""
veo_carve.py — Veo 3.1 path for carving reels (alternative to the
Hailuo+Grok split documented in imageGenSkill.MD).

Why this exists: Veo 3.1 is the only model reachable from this machine that
does BOTH jobs the montage needs —

  * first+last frame interpolation (`last_frame`), so a shot is guaranteed to
    start at ladder rung i and land on rung i+1; and
  * strong single-seed image-to-video WITH native synchronized audio,

which is what the Hailuo (progression, silent, 3:4) + Grok (motion + foley,
9:16 1080p) split was working around. It is also the family most likely used
by the reference reel.

Measured API constraints (2026-07-27):
  * `last_frame` REQUIRES duration_seconds=8. A 4s request 400s with
    INVALID_ARGUMENT, and older google-genai SDKs raise
    "last_frame parameter is not supported in Gemini API" — needs >= 2.x.
  * 1080p also requires 8s. 9:16 is supported natively (no cropping, unlike
    Hailuo which inherits the seed's aspect).
  * Veo is a paid-tier feature; a free-tier key 429s.

Usage:
    python veo_carve.py --job jobs/wolf_montage_v5.json --dry-run
    python veo_carve.py --job jobs/wolf_montage_v5.json --shot 07_mouth
    python veo_carve.py --job jobs/wolf_montage_v5.json          # all shots

A shot with "seed_end" is interpolated (rung -> rung); a shot without one is
plain image-to-video from its single seed. Existing clips are skipped unless
--force, so a re-roll costs one generation.
"""

import argparse
import json
import os
import subprocess
import sys
import time

from dotenv import load_dotenv

from carvegen.seeds import resolve_seed as resolve_seed_path

ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(ROOT, ".env"))

DEFAULT_MODEL = "veo-3.1-generate-preview"
FAST_MODEL = "veo-3.1-fast-generate-preview"
POLL_SECONDS = 10
TIMEOUT_SECONDS = 900
MAX_RETRIES = 4
RETRY_BACKOFF = [20, 45, 90]         # 503 only — see QuotaExhausted below

# Hard user-stated caps for the Veo 3 Fast key on this project: no more than
# 1 generate_videos submission per minute, no more than 10 per day. Enforced
# per-process (this script isn't invoked often enough in one day to need
# cross-process persistence) — every attempt, including 503 retries, counts,
# since each is a real request against the quota.
MIN_SUBMIT_INTERVAL = 61
DAILY_SUBMIT_CAP = 10
_last_submit_ts = [0.0]
_submit_count = [0]

# Applied to EVERY shot's prompt unconditionally, regardless of whether a
# job's own style_suffix remembers to say it. Added after the Starbucks
# carve (2026-07-30): each shot is an independent generation with no shared
# camera lock, so Veo is free to frame/zoom/position the hand-held subject
# slightly differently call to call even from visually-identical seeds — the
# melon visibly drifted in size/position across cuts in that reel. This does
# not fully fix it (framing still varies somewhat) but a job that forgets to
# ask for it drifts worse. See carvingSkill.MD Step 5/7 for the fuller
# writeup and the recut-side mitigation this alone can't replace.
DEFAULT_STYLE_GUARD = (
    "Static locked-off camera; the subject stays centered in frame and "
    "fills the same proportion of the frame as at the start of the shot; "
    "camera does not pan, drift, zoom or reframe during the shot."
)


def _throttle_submit():
    now = time.time()
    elapsed = now - _last_submit_ts[0]
    if _last_submit_ts[0] and elapsed < MIN_SUBMIT_INTERVAL:
        wait = MIN_SUBMIT_INTERVAL - elapsed
        print(f"  [throttle] waiting {wait:.0f}s to respect the 1/min cap")
        time.sleep(wait)
    _submit_count[0] += 1
    if _submit_count[0] > DAILY_SUBMIT_CAP:
        sys.exit(f"ERROR: hit the {DAILY_SUBMIT_CAP}/day Veo submission cap "
                 f"for this run. Stop and resume tomorrow, or raise "
                 f"DAILY_SUBMIT_CAP if the account limit is actually higher.")
    _last_submit_ts[0] = time.time()


class QuotaExhausted(RuntimeError):
    """429 RESOURCE_EXHAUSTED — never retried, always aborts the run.

    A 429 from this API is NOT diagnostic. The body is only code/message/
    status (verified: no retryDelay, no quotaMetric, no QuotaFailure), and
    the same generic "You exceeded your current quota" text is returned for
    BOTH a per-model daily request limit AND a project-level Cloud safety
    quota triggered by a spend spike. Those need opposite responses: one
    clears on its own, the other stays until a human raises it in the Cloud
    Console.

    Retrying was actively harmful — it ground through backoffs for 49 minutes
    against a clamp that was never going to yield (2026-07-27), and every
    attempt is another request against the limit. Continuing to the NEXT shot
    is equally pointless: if the project is out of quota, every subsequent
    submit fails the same way.

    So: stop immediately, say what is known and what is not, and let the
    operator check billing. Only 503 UNAVAILABLE (model genuinely busy) is
    retried.
    """


def client():
    key = os.getenv("GOOGLE_API_KEY")
    if not key:
        sys.exit("ERROR: GOOGLE_API_KEY not set in .env")
    from google import genai
    return genai.Client(api_key=key)


ASPECT_RATIOS = {"9:16": 9 / 16, "16:9": 16 / 9}


def check_seed_aspect(path, aspect):
    """Warn when a seed's shape does not match the requested output aspect.

    Veo honours the seed's framing: hand it a 3:4 still and ask for 9:16 and
    it LETTERBOXES — measured 2026-07-27, every v5 clip came back 1080x1920
    with only 1080x1440 of content and 240px black bars top and bottom, i.e.
    a quarter of a Reels frame wasted. The code is correct in that case and a
    diff review cannot see it, because the defect lives in the PNG's pixel
    dimensions rather than in any source line. Hence this guard.
    """
    want = ASPECT_RATIOS.get(aspect)
    if not want:
        return
    from PIL import Image
    w, h = Image.open(path).size
    got = w / h
    if abs(got - want) > 0.02:
        print(f"  [WARN] seed {os.path.basename(path)} is {w}x{h} "
              f"(aspect {got:.3f}) but output is {aspect} ({want:.3f}). "
              f"Veo will letterbox — regenerate the seed at {aspect}.")


def load_image(path):
    from google.genai import types
    mime = "image/png" if path.lower().endswith(".png") else "image/jpeg"
    with open(path, "rb") as f:
        return types.Image(image_bytes=f.read(), mime_type=mime)


def generate(cl, prompt, seed_path, dst, seed_end_path=None,
             model=DEFAULT_MODEL, aspect="9:16", resolution="1080p",
             duration=8, negative=None):
    from google.genai import types

    cfg = {"aspect_ratio": aspect, "resolution": resolution,
           "duration_seconds": duration, "number_of_videos": 1}
    if negative:
        cfg["negative_prompt"] = negative
    if seed_end_path and duration != 8:
        # interpolation: pinned at both ends. 8s is mandatory here —
        # 4s returns INVALID_ARGUMENT. Say so instead of silently overriding.
        print(f"  [warn] last_frame requires 8s; overriding duration={duration}")
        duration = 8
    if resolution == "1080p" and duration != 8:
        print(f"  [warn] 1080p requires 8s; overriding duration={duration}")
        duration = 8
    cfg["duration_seconds"] = duration
    if seed_end_path:
        cfg["last_frame"] = load_image(seed_end_path)

    # 503 = model busy, genuinely transient, worth a retry.
    # 429 = quota exhausted, NOT retryable — see QuotaExhausted.
    op = None
    for attempt in range(MAX_RETRIES):
        try:
            _throttle_submit()
            op = cl.models.generate_videos(
                model=model, prompt=prompt, image=load_image(seed_path),
                config=types.GenerateVideosConfig(**cfg))
            break
        except Exception as e:
            msg = str(e)
            code = getattr(e, "code", None) or getattr(e, "status_code", None)
            if code == 429 or "RESOURCE_EXHAUSTED" in msg:
                raise QuotaExhausted(msg[:400]) from e
            busy = code == 503 or "UNAVAILABLE" in msg
            if not busy or attempt == MAX_RETRIES - 1:
                print(f"  ERROR: submit failed: {msg[:200]}")
                return None
            wait = RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)]
            print(f"  [retry {attempt + 1}/{MAX_RETRIES - 1}] 503 model busy "
                  f"— waiting {wait}s")
            time.sleep(wait)
    if op is None:
        return None

    waited = 0
    while not op.done:
        if waited > TIMEOUT_SECONDS:
            print(f"  ERROR: Veo timed out after {waited}s")
            return None
        time.sleep(POLL_SECONDS)
        waited += POLL_SECONDS
        try:
            op = cl.operations.get(op)
        except Exception as e:
            msg = str(e)
            if getattr(e, "code", None) == 429 or "RESOURCE_EXHAUSTED" in msg:
                raise QuotaExhausted(msg[:400]) from e
            raise
        print(f"  ...generating ({waited}s)")

    if getattr(op, "error", None):
        print(f"  ERROR: Veo failed: {op.error}")
        return None
    vids = getattr(op.response, "generated_videos", None) if op.response else None
    if not vids:
        # Completed with no output = the RAI safety filter withheld the video
        # (a normal outcome for gory-sounding prompts, not an API bug). Report
        # and let the caller move on to the remaining shots.
        print("  ERROR: Veo returned no video (safety filter likely withheld "
              "it). Soften the prompt's flesh/knife language and re-roll this "
              "shot.")
        return None
    vid = vids[0]
    cl.files.download(file=vid.video)
    vid.video.save(dst)
    return dst


W, H = 96, 170          # analysis resolution


def _ff():
    local = os.path.join(ROOT, "tools", "ffmpeg.exe")
    return local if os.path.exists(local) else "ffmpeg"


def _frames(path):
    """Decode a clip (or a still) to a small greyscale array stack."""
    import numpy as np
    r = subprocess.run([_ff(), "-v", "error", "-i", path,
                        "-vf", f"fps=15,scale={W}:{H},format=gray",
                        "-f", "rawvideo", "-"], capture_output=True)
    a = np.frombuffer(r.stdout, dtype=np.uint8)
    n = len(a) // (W * H)
    if n < 1:
        return None
    return a[:n * W * H].reshape(n, H, W).astype(float)


def score_clip(path, seed_path=None, target_path=None):
    """Objective proxies for the failures actually observed on this project.

    Motion smoothness alone was not enough: it caught a mushy shaving but
    would have missed BOTH of the montage's worst moments. So we also track
    how the frame moves away from its seed over time:

      spike  — worst frame-to-frame jump. Catches the end-frame snap, a
               teleporting knife, a scene flip.
      step   — biggest single jump in distance-from-seed. This is the
               "half the face removed in one sweep" detector: plausible
               carving raises the curve gradually, an implausible removal
               puts a step in it.
      drift  — distance from seed at the END. For a bounded i2v shot this
               should stay small; a large value means the model redesigned
               the subject (the wolf-identity change at a cut).
      land   — distance from the target rung at the end, when one is given.
               Low = the interpolation actually arrived.

    Returns a dict, or None if the clip could not be decoded.
    """
    import numpy as np
    a = _frames(path)
    if a is None or len(a) < 3:
        return None
    inter = np.abs(np.diff(a, axis=0)).mean(axis=(1, 2))
    out = {"motion": float(inter.mean()), "spike": float(inter.max()),
           "step": float("nan"), "drift": float("nan"), "land": float("nan")}

    if seed_path and os.path.isfile(seed_path):
        s = _frames(seed_path)
        if s is not None:
            dseed = np.abs(a - s[0]).mean(axis=(1, 2))
            out["step"] = float(np.diff(dseed).max()) if len(dseed) > 1 else 0.0
            out["drift"] = float(dseed[-3:].mean())
    if target_path and os.path.isfile(target_path):
        t = _frames(target_path)
        if t is not None:
            out["land"] = float(np.abs(a[-3:] - t[0]).mean())
    return out


def rank_takes(media_dir, shots, proj_dir):
    """Score every take of every shot and print them best-first.

    Sorted by `drift`, then `spike`. That ordering is empirical, not a guess:
    scored against the four clips whose quality was already known (2026-07-28),
    drift separated them 2:1 while `step` did not discriminate at all —

        clip                        step  spike  drift
        05_muzzle  (bad: sweep)      4.8   19.3   27.8
        07_border  (bad: drift)      6.1   35.2   28.0
        08_mouth   (good)            4.2    8.8   14.0
        04_eye     (good i2v)        5.7   18.8   10.7

    Both observed failures are really "the model changed too much from its
    seed", which is exactly what drift measures. `step` is still printed, but
    do not rank on it. This shortlists; it does not decide.

    IMPORTANT: drift is only comparable BETWEEN TAKES OF THE SAME SHOT. Its
    absolute value depends on how much uncarved area the seed has and on
    hands/shavings entering frame — a perfectly bounded v8 take scored 41.6,
    higher than a genuinely broken v6 clip at 27.8. Never threshold it across
    shots.
    """
    import glob
    import math
    for shot in shots:
        name = shot["name"]
        takes = sorted(glob.glob(os.path.join(media_dir,
                                              f"veo_{name}_take*.mp4")))
        if not takes:
            continue
        try:
            seed = resolve_seed_path(shot["seed"], proj_dir)
        except SystemExit:
            seed = None
        target = None
        if shot.get("seed_end"):
            try:
                target = resolve_seed_path(shot["seed_end"], proj_dir)
            except SystemExit:
                target = None

        rows = []
        for t in takes:
            s = score_clip(t, seed, target)
            if s:
                rows.append((s, os.path.basename(t)))
        if not rows:
            continue
        rows.sort(key=lambda r: (1e9 if math.isnan(r[0]["drift"])
                                 else r[0]["drift"], r[0]["spike"]))
        print(f"\n{name}   (best first by 'drift' = stayed closest to its seed)")
        print(f"   {'take':40s} {'step':>7s} {'spike':>7s} {'drift':>7s} "
              f"{'land':>7s} {'motion':>7s}")
        for s, fn in rows:
            def f(v):
                return "   -  " if math.isnan(v) else f"{v:6.1f}"
            print(f"   {fn:40s} {f(s['step'])} {f(s['spike'])} "
                  f"{f(s['drift'])} {f(s['land'])} {f(s['motion'])}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    ap.add_argument("--shot", default=None, help="Generate one shot by name.")
    ap.add_argument("--model", default=DEFAULT_MODEL,
                    help=f"Veo model id (use {FAST_MODEL} for cheap tests).")
    ap.add_argument("--takes", type=int, default=None, metavar="N",
                    help="Generate N takes per shot as veo_<name>_takeK.mp4 "
                         "and leave selection to you. Cherry-picking is the "
                         "cheapest quality lever in this pipeline — physics "
                         "in 1s cuts is largely a selection effect. Follow "
                         "with --rank, then --promote.")
    ap.add_argument("--rank", action="store_true",
                    help="Score existing takes for a shot (or all shots) by "
                         "motion smoothness and print them best-first. Free, "
                         "no API calls. Use it to shortlist before eyeballing.")
    ap.add_argument("--promote", default=None, metavar="TAKE_FILE",
                    help="Copy a chosen take over veo_<shot>.mp4 (needs "
                         "--shot). e.g. --shot 06_nose --promote 3")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    with open(args.job, "r", encoding="utf-8") as f:
        job = json.load(f)

    proj_dir = os.path.join(ROOT, job["project"])
    media_dir = os.path.join(proj_dir, "media")
    os.makedirs(media_dir, exist_ok=True)

    style = job.get("style_suffix", "")
    negative = job.get("negative_prompt")
    aspect = job.get("aspect_ratio", "9:16")
    resolution = job.get("resolution", "1080p")
    duration = int(job.get("duration", job.get("gen_duration", 8)))

    if args.shot and args.shot not in {s["name"] for s in job["shots"]}:
        sys.exit(f"ERROR: no shot named {args.shot!r} in {args.job}. "
                 f"Shots: {', '.join(s['name'] for s in job['shots'])}")

    names = [s["name"] for s in job["shots"]
             if not args.shot or s["name"] == args.shot]

    if args.rank:
        rank_takes(media_dir,
                   [s for s in job["shots"] if s["name"] in names], proj_dir)
        return

    if args.promote:
        if not args.shot:
            sys.exit("ERROR: --promote needs --shot NAME")
        src = os.path.join(media_dir, f"veo_{args.shot}_take{args.promote}.mp4")
        if not os.path.isfile(src):
            src = os.path.join(media_dir, args.promote)
        if not os.path.isfile(src):
            sys.exit(f"ERROR: take not found: {args.promote}")
        import shutil
        dst = os.path.join(media_dir, f"veo_{args.shot}.mp4")
        shutil.copyfile(src, dst)
        print(f"promoted {os.path.basename(src)} -> {os.path.basename(dst)}")
        return

    cl = None if args.dry_run else client()

    failed = []
    for shot in job["shots"]:
        name = shot["name"]
        if args.shot and args.shot != name:
            continue
        dst = os.path.join(media_dir, f"veo_{name}.mp4")
        prompt = f"{shot['prompt']} {style} {DEFAULT_STYLE_GUARD}".strip()
        seed = resolve_seed_path(shot["seed"], proj_dir)
        seed_end = (resolve_seed_path(shot["seed_end"], proj_dir)
                    if shot.get("seed_end") else None)

        if args.dry_run:
            kind = "interpolate" if seed_end else "i2v"
            print(f"\n=== {name} [{kind}] {os.path.basename(seed)}"
                  f"{' -> ' + os.path.basename(seed_end) if seed_end else ''}"
                  f"\n{prompt}")
            continue

        if args.takes == 1 and os.path.isfile(dst) and not args.force:
            print(f"[skip] {name} exists")
            continue

        print(f"\n[{name}] {os.path.basename(seed)}"
              f"{' -> ' + os.path.basename(seed_end) if seed_end else ''}")
        check_seed_aspect(seed, aspect)
        if seed_end:
            check_seed_aspect(seed_end, aspect)

        # multi-take: never overwrite veo_<name>.mp4 — takes are candidates,
        # promotion is a separate deliberate step
        # per-shot "takes" in the job lets one run spend more on the shots
        # that actually vary. --takes must be able to OVERRIDE DOWNWARD too:
        # defaulting it to 1 made "--takes 1" indistinguishable from "unset",
        # so the job's takes:3 silently won and spent two extra generations.
        want = args.takes if args.takes is not None else int(shot.get("takes", 1))
        targets = ([dst] if want == 1 else
                   [os.path.join(media_dir, f"veo_{name}_take{k}.mp4")
                    for k in range(1, want + 1)])
        got = 0
        for target in targets:
            if args.takes > 1 and os.path.isfile(target) and not args.force:
                print(f"  [skip] {os.path.basename(target)} exists")
                got += 1
                continue
            out = generate(cl, prompt, seed, target, seed_end,
                           model=args.model, aspect=aspect,
                           resolution=resolution,
                           duration=int(shot.get("duration", duration)),
                           negative=negative)
            if out:
                print(f"  -> {os.path.basename(target)}")
                got += 1
        if got == 0:
            failed.append(name)

    if args.dry_run:
        print("\n(dry run — nothing generated)")
    elif failed:
        sys.exit(f"\n{len(failed)} shot(s) FAILED and need a re-roll: "
                 f"{', '.join(failed)}")


if __name__ == "__main__":
    try:
        main()
    except QuotaExhausted as e:
        sys.exit(
            "\n================ STOPPED: quota exhausted (429) ================\n"
            f"{e}\n\n"
            "NOT retried, and remaining shots were NOT attempted — every one\n"
            "would fail the same way and each attempt counts against the limit.\n\n"
            "This error CANNOT tell you which of these it is:\n"
            "  (a) a per-model daily request limit  -> clears at midnight PT\n"
            "  (b) a project safety quota from a spend spike -> stays until\n"
            "      raised in Cloud Console (IAM & Admin -> Quotas), and will\n"
            "      NOT clear on its own\n"
            "The response body carries no retryDelay or quotaMetric to tell\n"
            "them apart, and an AI Studio API key cannot read Cloud Quotas.\n\n"
            "Check billing/quotas in the Cloud Console before re-running.\n"
            "Any completed takes are already saved; re-running skips them.\n"
            "===============================================================")
