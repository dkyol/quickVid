#!/usr/bin/env python3
"""
chain_carve.py — Chained Montage pipeline (see imageGenSkill.MD).

Builds a long carving reel out of short Grok Imagine clips by chaining them:
each clip is generated image-to-video from the PREVIOUS clip's tail frame, so
continuity lives in the frames rather than in the model's memory. Each link is
prompted to advance exactly ONE stage; only the last link gets completion
language.

Each clip is then trimmed to its slot duration and the slots are concatenated.
The default trim mode is "tail" — keep the LAST `dur` seconds — which makes the
junctions frame-continuous: link i's cut ends on the very frame that link i+1
was generated from.

    python chain_carve.py --job jobs/wolf_chain.json --dry-run   # free preview
    python chain_carve.py --job jobs/wolf_chain.json             # generate all
    python chain_carve.py --job jobs/wolf_chain.json --stage 04_brow
    python chain_carve.py --job jobs/wolf_chain.json --stitch-only

Resumes by default: a link whose .mp4 already exists is reused (--force
regenerates). Re-rolling one bad link costs one generation, not the reel.
"""

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys

import generate_shots as gs
# NB: gs.resolve_seed returns a data URI for local files. Here we need the
# PATH (so it can be re-read per link), which is what carvegen's resolver gives.
from carvegen.seeds import resolve_seed as resolve_seed_path

ROOT = os.path.dirname(os.path.abspath(__file__))

DEFAULT_GEN_DURATION = 5      # generate longer than the slot, then trim
DEFAULT_SLOT = 1.3            # seconds of each clip that reach the reel
DEFAULT_MODEL = "grok-imagine-video-1.5"   # required for 1080p
DEFAULT_RESOLUTION = "1080p"
DEFAULT_ASPECT = "9:16"
TAIL_OFFSET = 0.25            # -sseof value; -0.04 silently writes NO file

OUT_W, OUT_H, OUT_FPS, OUT_AR = 1080, 1920, 30, 44100


# --------------------------------------------------------------------------- #
# ffmpeg helpers
# --------------------------------------------------------------------------- #
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


def run(args, label=""):
    r = subprocess.run([FF, "-y", "-loglevel", "error", *args],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"ERROR: ffmpeg failed{' (' + label + ')' if label else ''}:\n"
                 f"{r.stderr[-1500:]}")


def duration_of(path):
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries",
                        "format=duration", "-of",
                        "default=noprint_wrappers=1:nokey=1", path],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        sys.exit(f"ERROR: could not read duration of {path}")


def has_audio(path):
    r = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "a",
                        "-show_entries", "stream=codec_type", "-of",
                        "default=noprint_wrappers=1:nokey=1", path],
                       capture_output=True, text=True)
    return "audio" in r.stdout


def extract_tail_frame(clip, dst):
    """Grab a frame TAIL_OFFSET before EOF — the next link's seed.

    Do not shrink TAIL_OFFSET toward zero: -sseof -0.04 makes ffmpeg exit 0
    having written nothing, and it lands on motion-blurred final frames that
    poison the next generation.
    """
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    run(["-sseof", f"-{TAIL_OFFSET}", "-i", clip, "-update", "1", "-q:v", "2", dst],
        label=f"tail frame of {os.path.basename(clip)}")
    if not os.path.isfile(dst):
        sys.exit(f"ERROR: tail frame extraction produced no file for {clip}. "
                 f"Try raising TAIL_OFFSET.")
    return dst


def trim_slot(clip, dst, slot, mode="tail"):
    """Cut `slot` seconds out of `clip` and conform it for concatenation."""
    total = duration_of(clip)
    slot = min(slot, total)
    if mode == "tail":
        start = max(0.0, total - slot)
    elif mode == "head":
        start = 0.0
    else:
        # bare number = window starts at N seconds into the clip
        start = float(mode)
        latest = max(0.0, total - slot)
        if start > latest:
            print(f"  [warn] trim {start:.2f}s + slot {slot:.2f}s exceeds "
                  f"{os.path.basename(clip)} ({total:.2f}s); clamping to "
                  f"{latest:.2f}s")
            start = latest
    vf = (f"scale={OUT_W}:{OUT_H}:force_original_aspect_ratio=decrease,"
          f"pad={OUT_W}:{OUT_H}:(ow-iw)/2:(oh-ih)/2,fps={OUT_FPS},setsar=1")
    audio = has_audio(clip)
    args = ["-ss", f"{start:.3f}", "-t", f"{slot:.3f}", "-i", clip]
    if not audio:
        # silent clip: synthesize a matching silent track (input must precede
        # output options)
        args += ["-f", "lavfi", "-t", f"{slot:.3f}", "-i",
                 f"anullsrc=r={OUT_AR}:cl=stereo"]
    args += ["-vf", vf, "-c:v", "libx264", "-crf", "16", "-preset", "slow",
             "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", "-ar", str(OUT_AR), "-ac", "2"]
    if not audio:
        args += ["-shortest"]
    args += [dst]
    run(args, label=f"trim {os.path.basename(clip)}")
    return dst


def concat(clips, dst, crossfade=0.0):
    """Hard-cut concatenation (crossfade=0). A montage cuts; it does not fade."""
    args = []
    for c in clips:
        args += ["-i", c]
    if crossfade <= 0:
        streams = "".join(f"[{i}:v][{i}:a]" for i in range(len(clips)))
        fc = f"{streams}concat=n={len(clips)}:v=1:a=1[v][a]"
    else:
        # xfade chain: only worth it to take the edge off a jarring junction
        vprev, aprev, offset, parts = "[0:v]", "[0:a]", 0.0, []
        for i in range(1, len(clips)):
            offset += duration_of(clips[i - 1]) - crossfade
            vout, aout = f"[v{i}]", f"[a{i}]"
            parts.append(f"{vprev}[{i}:v]xfade=transition=fade:"
                         f"duration={crossfade}:offset={offset:.3f}{vout}")
            parts.append(f"{aprev}[{i}:a]acrossfade=d={crossfade}{aout}")
            vprev, aprev = vout, aout
        fc = ";".join(parts)
        fc += f";{vprev}null[v];{aprev}anull[a]"
    args += ["-filter_complex", fc, "-map", "[v]", "-map", "[a]",
             "-c:v", "libx264", "-crf", "16", "-preset", "slow",
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", dst]
    run(args, label="concat")
    return dst


# --------------------------------------------------------------------------- #
# Prompt building
# --------------------------------------------------------------------------- #
BASE = ("Hyper-realistic extreme macro process video: a small sharp carving knife "
        "carves a {subject} into a {material}. {palette} "
        "EXTREME MACRO — the carved surface fills the entire frame edge to edge, "
        "the {material}'s outline and silhouette are NOT visible, no table and no "
        "background objects in shot. Material is REMOVED by the blade: real cut "
        "depth with undercuts and cast shadows, each stroke a separate cut, and "
        "any drawn guide line is destroyed by the cut that follows it — never "
        "shaded or painted over. Soft flat diffused light, no hard shadows, no sun "
        "stripes. Matte natural texture, no glow, no airbrush, no neon. Subtle "
        "handheld micro-movement and shallow focus. Photorealistic, ultra-detailed. "
        "No text, no watermark.")

# The red-flesh clause is GATED: leaving it in every link is what bled hot red
# across the whole subject on the first run (measured 1.9x the reference's
# saturation). Only stages with "allow_flesh": true may mention it.
PALETTE = {
    "watermelon": ("The subject is rendered ENTIRELY in the melon's own layers — "
                   "dark green rind for the nose and dark markings, and pale "
                   "cream-white carved rind as the fur/skin with the melon's "
                   "green striations as natural shading. It is a carved "
                   "watermelon, not painted, not a grey animal."),
    "wood": ("The subject is rendered ENTIRELY in the wood's own material — grain "
             "running through the form, pale fresh-cut facets where the blade has "
             "passed, darker aged surface elsewhere, curled shavings falling. "
             "Bare carved wood, not painted, not stained."),
    "soap": ("The subject is rendered ENTIRELY in the soap's own material — waxy "
             "matte surface, pale translucent edges where thin, fine curled "
             "shavings falling away. Carved soap, not painted."),
}

NO_FLESH = ("NO red flesh anywhere in this shot — the blade has not cut through "
            "the pale rind layer yet. Only greens and cream-whites.")

FLESH_OK = ("Vivid red juicy flesh shows ONLY inside the single deepest cut, a "
            "small area; everywhere else stays green rind and cream-white carved "
            "rind.")

BOUND = ("Advance the carving ONLY as described above and no further; the rest of "
         "the subject is unchanged from how it starts this shot.")

FINISH = ("By the end the ENTIRE {subject} is carved in deep three-dimensional "
          "relief — a finished hero reveal, wiped clean.")


def build_prompt(job, stage, is_last):
    material = job.get("material", "watermelon")
    base = BASE.format(subject=job["subject"], material=material,
                       palette=PALETTE.get(material, PALETTE["watermelon"]))
    flesh = FLESH_OK if stage.get("allow_flesh") else NO_FLESH
    tail = (FINISH.format(subject=job["subject"]) if is_last else BOUND)
    extra = stage.get("prompt_extra", "")
    return f"{base} THIS SHOT: {stage['delta']} {flesh} {tail} {extra}".strip()


# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True, help="Path to a chain job JSON.")
    ap.add_argument("--stage", default=None,
                    help="Regenerate only this stage by name (its seed must "
                         "already exist from a previous run).")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print every prompt and slot plan, generate nothing.")
    ap.add_argument("--stitch-only", action="store_true",
                    help="Skip generation; re-trim and re-stitch existing clips.")
    ap.add_argument("--force", action="store_true",
                    help="Regenerate links even if their .mp4 already exists.")
    args = ap.parse_args()

    with open(args.job, "r", encoding="utf-8") as f:
        job = json.load(f)

    project = job["project"]
    proj_dir = os.path.join(ROOT, project)
    media_dir = os.path.join(proj_dir, "media")
    seeds_dir = os.path.join(proj_dir, "seeds")
    cut_dir = os.path.join(proj_dir, "cut")
    final_dir = os.path.join(proj_dir, "final")
    for d in (media_dir, seeds_dir, cut_dir, final_dir):
        os.makedirs(d, exist_ok=True)

    model = job.get("video_model", DEFAULT_MODEL)
    resolution = job.get("resolution", DEFAULT_RESOLUTION)
    aspect = job.get("aspect_ratio", DEFAULT_ASPECT)
    gen_dur = job.get("gen_duration", DEFAULT_GEN_DURATION)
    crossfade = job.get("crossfade", 0.0)
    stages = job["stages"]

    seed = job.get("seed_start")
    if not seed:
        sys.exit("ERROR: job needs \"seed_start\" (the before-frame).")

    print(f"Chain: {len(stages)} links, model={model}, {resolution}, "
          f"{gen_dur}s each -> slots totalling "
          f"{sum(s.get('slot', DEFAULT_SLOT) for s in stages):.1f}s")

    manifest = {"project": project, "job": os.path.abspath(args.job),
                "model": model, "resolution": resolution,
                "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "links": []}

    cuts = []
    for i, stage in enumerate(stages):
        name = stage["name"]
        is_last = (i == len(stages) - 1)
        slot = stage.get("slot", DEFAULT_SLOT)
        clip = os.path.join(media_dir, f"{name}.mp4")
        next_seed = os.path.join(seeds_dir, f"chain_{i + 1:02d}.png")
        prompt = build_prompt(job, stage, is_last)

        # The seed for link i is the tail frame of link i-1 (or seed_start).
        seed_path = resolve_seed_path(seed, proj_dir) if i == 0 else seed

        if args.dry_run:
            print(f"\n=== {name} (slot {slot}s, seed={os.path.basename(str(seed_path))})")
            print(prompt)
            seed = next_seed          # pretend, to show the chain
            continue

        run_this = not args.stitch_only and (args.stage in (None, name))
        if run_this and os.path.isfile(clip) and not args.force:
            print(f"[skip] {name} exists -> {clip}")
            run_this = False

        if run_this:
            print(f"\n[{i + 1}/{len(stages)}] {name} "
                  f"(seed={os.path.basename(str(seed_path))})")
            image_url = (gs.file_to_data_uri(seed_path)
                         if not str(seed_path).startswith("http") else seed_path)
            url = gs.generate_video(prompt, model, aspect, gen_dur, image_url,
                                    resolution=resolution)
            gs.download(url, clip)
            print(f"  -> {clip}")

        if not os.path.isfile(clip):
            sys.exit(f"ERROR: {clip} missing — generate it before stitching "
                     f"(drop --stitch-only, or run --stage {name}).")

        # Tail frame feeds the next link AND is the frame the cut ends on,
        # which is what makes the junction continuous.
        extract_tail_frame(clip, next_seed)
        seed = next_seed

        cut = os.path.join(cut_dir, f"{i:02d}_{name}.mp4")
        trim_slot(clip, cut, slot, stage.get("trim", "tail"))
        cuts.append(cut)
        manifest["links"].append({"name": name, "slot": slot, "clip": clip,
                                  "cut": cut, "next_seed": next_seed,
                                  "prompt": prompt})

    if args.dry_run:
        print("\n(dry run — nothing generated)")
        return

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = os.path.join(final_dir, f"{project}_chain_{stamp}.mp4")
    concat(cuts, out, crossfade)
    manifest["output"] = out
    with open(os.path.join(final_dir, f"{project}_chain_{stamp}_manifest.json"),
              "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nDone -> {out}  ({duration_of(out):.2f}s)")


if __name__ == "__main__":
    main()
