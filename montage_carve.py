#!/usr/bin/env python3
"""
montage_carve.py — INDEPENDENT-shot montage pipeline (see imageGenSkill.MD).

Supersedes chain_carve.py. Each shot is generated from its own seed still, with
only a small local motion, and the shots are hard-cut together. Nothing is fed
forward, so a bad shot cannot poison the rest — the failure mode that killed the
chained run.

The reference reel's energy comes from CUTTING BETWEEN SCALES (wide -> macro ->
wide), not from any shot transforming. Measured on the reference: mean
inter-frame RMS ~30 (churn) with only ~23 net start->end change. Match that by
varying framing per shot while keeping each shot's own motion small.

    python montage_carve.py --job jobs/wolf_montage.json --dry-run
    python montage_carve.py --job jobs/wolf_montage.json
    python montage_carve.py --job jobs/wolf_montage.json --shot 03_eye
    python montage_carve.py --job jobs/wolf_montage.json --stitch-only
"""

import argparse
import datetime
import json
import os
import sys

import generate_shots as gs
import chain_carve as cc          # reuse trim/concat/probe helpers
from carvegen.seeds import resolve_seed as resolve_seed_path

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    ap.add_argument("--shot", default=None, help="Generate/regenerate one shot.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--stitch-only", action="store_true")
    ap.add_argument("--from-prefix", default=None, metavar="PREFIX",
                    help="Before stitching, copy media/<PREFIX><name>.mp4 over "
                         "media/m_<name>.mp4 for every shot (e.g. veo_). "
                         "Errors if any source is missing — prevents silently "
                         "stitching a stale clip left by an earlier run.")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    with open(args.job, "r", encoding="utf-8") as f:
        job = json.load(f)

    project = job["project"]
    proj_dir = os.path.join(ROOT, project)
    media_dir = os.path.join(proj_dir, "media")
    cut_dir = os.path.join(proj_dir, "cut")
    final_dir = os.path.join(proj_dir, "final")
    for d in (media_dir, cut_dir, final_dir):
        os.makedirs(d, exist_ok=True)

    model = job.get("video_model", "grok-imagine-video-1.5")
    resolution = job.get("resolution", "1080p")
    aspect = job.get("aspect_ratio", "9:16")
    gen_dur = job.get("gen_duration", 5)
    crossfade = job.get("crossfade", 0.0)
    style = job.get("style_suffix", "")
    shots = job["shots"]

    total = sum(s.get("slot", 1.4) for s in shots)
    print(f"Montage: {len(shots)} independent shots, model={model}, {resolution}, "
          f"{gen_dur}s each -> {total:.1f}s reel")

    if args.shot and args.shot not in {s["name"] for s in shots}:
        sys.exit(f"ERROR: no shot named {args.shot!r} in {args.job}. "
                 f"Shots: {', '.join(s['name'] for s in shots)}")

    if args.from_prefix:
        import shutil
        missing = [s["name"] for s in shots if not os.path.isfile(
            os.path.join(media_dir, f"{args.from_prefix}{s['name']}.mp4"))]
        if missing:
            sys.exit(f"ERROR: --from-prefix {args.from_prefix}: missing "
                     f"{', '.join(args.from_prefix + m + '.mp4' for m in missing)}")
        for s in shots:
            shutil.copyfile(
                os.path.join(media_dir, f"{args.from_prefix}{s['name']}.mp4"),
                os.path.join(media_dir, f"m_{s['name']}.mp4"))
        print(f"[copy] {len(shots)} clips {args.from_prefix}* -> m_*")

    manifest = {"project": project, "job": os.path.abspath(args.job),
                "model": model, "resolution": resolution,
                "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "shots": []}
    cuts = []

    for i, shot in enumerate(shots):
        name = shot["name"]
        slot = shot.get("slot", 1.4)
        clip = os.path.join(media_dir, f"m_{name}.mp4")
        prompt = f"{shot['prompt']} {style}".strip()

        if args.dry_run:
            print(f"\n=== {name} [{shot.get('scale','?')}] slot={slot}s "
                  f"seed={shot['seed']}\n{prompt}")
            continue

        run_this = not args.stitch_only and (args.shot in (None, name))
        # stitch-only never touches a seed image — don't die on a cleaned
        # seeds/ folder when every clip needed for the concat is present
        seed_path = (resolve_seed_path(shot["seed"], proj_dir)
                     if run_this else shot["seed"])
        # skip-if-exists only applies to sweep runs; an explicit --shot NAME
        # means "re-roll this one", which was its documented purpose all along
        if run_this and args.shot is None and os.path.isfile(clip) \
                and not args.force:
            print(f"[skip] {name} exists")
            run_this = False

        if run_this:
            print(f"\n[{i+1}/{len(shots)}] {name} [{shot.get('scale','?')}] "
                  f"seed={os.path.basename(seed_path)}")
            url = gs.generate_video(prompt, model, aspect, gen_dur,
                                    gs.file_to_data_uri(seed_path),
                                    resolution=resolution)
            gs.download(url, clip)
            print(f"  -> {clip}")

        if not os.path.isfile(clip):
            sys.exit(f"ERROR: {clip} missing — generate it first "
                     f"(--shot {name}).")

        cut = os.path.join(cut_dir, f"m{i:02d}_{name}.mp4")
        cc.trim_slot(clip, cut, slot, shot.get("trim", 0.5))
        cuts.append(cut)
        manifest["shots"].append({"name": name, "scale": shot.get("scale"),
                                  "slot": slot, "seed": seed_path,
                                  "clip": clip, "cut": cut, "prompt": prompt})

    if args.dry_run:
        print("\n(dry run — nothing generated)")
        return

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = os.path.join(final_dir, f"{project}_montage_{stamp}.mp4")
    cc.concat(cuts, out, crossfade)
    manifest["output"] = out
    with open(os.path.join(final_dir, f"{project}_montage_{stamp}_manifest.json"),
              "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nDone -> {out}  ({cc.duration_of(out):.2f}s)")


if __name__ == "__main__":
    main()
