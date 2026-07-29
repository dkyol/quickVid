#!/usr/bin/env python3
"""
make_ladder.py — build the montage's seed ladder from ONE master still
(see imageGenSkill.MD, "The stage ladder is built by EDITING, not generating").

v2 of this script generated every rung with fresh text-to-image. Measured
result (2026-07-26 wolf run): Grok t2i rendered nearly every rung as a
FINISHED carve regardless of the "nothing carved yet" language, and two macro
rungs came back as a photoreal living wolf — which is exactly what the video
model then animated. Fresh t2i cannot hold a progression; edits of one master
can, because the edit model keeps composition and only changes what you name.

The v3 flow:

  1. Generate master candidates (finished wide hero, palette-correct):
       python make_ladder.py --project wolf_watermelon \
           --subject "snarling gray wolf head" --master-gen 4
     Curate by eye; the keeper becomes seeds/master.png.

  2. Build the regression rungs (later stages first — each is an EDIT of the
     master, so geometry/palette/lighting stay identical across the ladder):
       python make_ladder.py --project wolf_watermelon \
           --subject "snarling gray wolf head" --master seeds/master.png

  3. Cut macro rungs as CROPS of the master (free, identity-perfect):
       python make_ladder.py --project wolf_watermelon --master seeds/master.png \
           --crop brow:0.20,0.15,0.55,0.30 --crop mouth:0.25,0.55,0.50,0.30
     (fractional x,y,w,h of the master; crops are resized to 9:16.)

Regenerate one rung: add --only stage_A_outline.
"""

import argparse
import os
import sys

from dotenv import load_dotenv

import generate_shots as gs

ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(ROOT, ".env"))

# ---------------------------------------------------------------------------
# Master prompt (t2i, curated by eye). Two hard-won rules are baked in:
#  - the WHOLE visible rind carries carved decorative texture (the reference
#    reel's melon is patterned edge to edge; a subject on smooth rind reads as
#    a printed decal, not a carving);
#  - an explicit "not a living animal" guard (two v2 rungs came alive).
# ---------------------------------------------------------------------------
MASTER_PROMPT = (
    "Photorealistic vertical 9:16 photograph, soft flat diffused daylight, no "
    "hard shadows, plain light grey seamless background. A whole watermelon "
    "fills most of the frame, held steady by two hands. A {subject} is carved "
    "into the rind in SHALLOW BAS-RELIEF — at most one or two centimeters "
    "deep, cut INTO the curved surface, nothing protruding beyond the melon's "
    "original surface, the melon's smooth round silhouette unbroken. The "
    "design reads through layer contrast alone: dark green outer rind left "
    "uncarved as the nose, pupils and every dark marking, pale green-white "
    "inner rind exposed as the fur with each tuft a separate shallow knife "
    "cut, and a small area of vivid red flesh ONLY inside the open mouth. The "
    "ONLY colors in frame are watermelon colors — dark green rind, pale "
    "green-white inner rind, cream pith, red flesh; no grey, no black, no "
    "brown anywhere. The rest of the visible rind around the {subject} is "
    "covered edge to edge in a shallow carved decorative leaf pattern — no "
    "smooth untouched rind in frame. It is a carved watermelon, like "
    "traditional Thai fruit carving: not a living animal, no real fur, not "
    "painted, not a sculpture bust. Matte natural texture, no glow, no "
    "airbrush. No text, no watermark, no phone UI."
)

# ---------------------------------------------------------------------------
# Regression rungs: edits applied to the master, ordered latest -> earliest.
# Every rung inherits the master's framing, so the ladder is monotonic by
# construction — the melon can only ever look LESS carved than the master.
# ---------------------------------------------------------------------------
KEEP = ("Keep the melon's shape and position, the hands, the lighting and the "
        "background exactly the same as the original image. Only watermelon "
        "colors anywhere: dark green rind, pale green-white inner rind, cream "
        "pith, red flesh — no grey, no black, no brown.")

# Build DIRECTION is the thing that makes or breaks this ladder.
#
# Measured twice (v4 rungs, then v5 rungs rebuilt with gemini-3-pro-image):
# asking an edit model to REGRESS a finished carving to a half-carved state
# does not work. It cannot un-carve. v5's regression-only attempt came back
# non-monotonic — mean abs diff from master A 22.23 / B 13.82 / C 13.09 /
# D 19.42 / E 5.31, i.e. B and C both landed near-finished and D scored
# FURTHER from the master than either.
#
# What works: regress only the two edits that are subtractive in an easy way
# (strip everything to line-art; close the mouth), then build the middle rungs
# FORWARD from the outline by ADDING carved area one region at a time. Additive
# edits are what these models are good at, and each rung still descends from
# the one master, so the subject never drifts.
#
# Carved area steps roughly evenly: 0 / 15 / 40 / 70 / 90 / 100 %.
# `source` names the image being edited: "master" or another rung.
LADDER = [
    # --- subtractive, from the master: strip it all back to the drawing ---
    ("stage_A_outline", "master",
     "Replace the entire carved {subject} and the carved decorative border "
     "with the SAME design drawn ONLY as thin dark outline strokes on the "
     "smooth intact dark green watermelon rind — pure line-art like a marker "
     "sketch: no shading, no grey tones, no tonal rendering, no fill. Nothing "
     "is carved anywhere: no relief, no grooves, no pale inner rind, no red "
     "flesh, no shavings. The rind stays uniform dark green everywhere. "
     + KEEP),
    # --- additive, each from the rung before it ---
    ("stage_B_first_cuts", "stage_A_outline",
     "Carve ONLY the {subject}'s two ears and the top of the skull: cut those "
     "areas into shallow pale relief with a clean cut edge where the blade "
     "stopped, and let one curl of green rind lift away there. Everything "
     "else in the image — the rest of the face, the mouth, and the whole "
     "decorative border — stays EXACTLY the flat dark line-art drawing on "
     "intact dark green rind that it is now. About one sixth of the design is "
     "carved. No red flesh anywhere. " + KEEP),
    # NB the MATCH clause: without it the forward chain drifts into carving
    # each region as a solid pale shape, so the face reads completely
    # different from the finished master and the last transition has to
    # re-render the whole face instead of just adding the border.
    ("stage_C_upper_face", "stage_B_first_cuts",
     "Keeping the already-carved ears and skull exactly as they are, now ALSO "
     "carve the forehead, brow and both eyes, with individual fur cuts and a "
     "clean cut edge running across the middle of the face. MATCH THE "
     "FINISHED CARVING'S RENDERING: the face keeps DARK GREEN rind for its "
     "dark mask and markings, and PALE carved rind is used ONLY for the fur "
     "strokes, eyebrows and eye detail — do not carve the face into a solid "
     "pale shape. Below the cut edge — muzzle, mouth, cheeks, ruff — and the "
     "whole decorative border stay EXACTLY the flat dark line-art drawing on "
     "intact dark green rind. A few rind shavings lie on the surface below "
     "the melon. No red flesh anywhere. " + KEEP),
    ("stage_D_muzzle", "stage_C_upper_face",
     "Keeping everything already carved exactly as it is, now ALSO carve the "
     "muzzle and both cheeks with fur cuts, leaving the dark green rind as "
     "the nose and keeping the mouth CLOSED. MATCH THE FINISHED CARVING'S "
     "RENDERING: dark green rind stays as the face's dark markings and the "
     "pale carved rind is only the fur strokes and muzzle highlights — the "
     "face must NOT become a solid pale shape. The outer ruff and the whole "
     "decorative border still stay the flat dark line-art drawing on intact "
     "dark green rind. More rind shavings have piled up below the melon. No "
     "red flesh anywhere. " + KEEP),
    # --- subtractive, from the master: the one easy backwards edit ---
    ("stage_E_closed_mouth", "master",
     "Close the {subject}'s mouth: replace the open red-flesh mouth with a "
     "closed mouth carved as shallow pale relief. NO red flesh visible "
     "anywhere in the image. Everything else stays exactly as carved. "
     + KEEP),
]


def gemini_client():
    from google import genai
    key = os.getenv("GOOGLE_API_KEY")
    if not key:
        sys.exit("ERROR: --engine gemini needs GOOGLE_API_KEY in .env")
    return genai.Client(api_key=key)


def _save_first_image(response, dst):
    for cand in (response.candidates or []):
        for part in (cand.content.parts or []):
            blob = getattr(part, "inline_data", None)
            if blob and blob.data:
                with open(dst, "wb") as f:
                    f.write(blob.data)
                return dst
    return None


def generate_master_gemini(prompt, dst, aspect="9:16",
                           model="gemini-3-pro-image"):
    """Text-to-image master at a NATIVE aspect ratio.

    Must match the video job's aspect_ratio: Veo honours the seed's framing,
    so a 3:4 master makes every 9:16 clip letterbox (measured on v5 — 240px
    black bars top and bottom, a quarter of the frame). Grok's image endpoint
    has no aspect control and emits 864x1152, which is why the master moved
    here.
    """
    from google.genai import types
    cl = gemini_client()
    r = cl.models.generate_content(
        model=model, contents=[prompt],
        config=types.GenerateContentConfig(
            image_config=types.ImageConfig(aspect_ratio=aspect)))
    if not _save_first_image(r, dst):
        sys.exit(f"ERROR: {model} returned no image: "
                 f"{getattr(r, 'text', '')[:300]}")
    return dst


def edit_with_gemini(prompt, master, dst,
                     model="gemini-3-pro-image"):
    """Regress a rung using Gemini image editing instead of xAI.

    Preferred engine: it holds "change ONLY this region" far better than
    grok-imagine-image-quality, which is what let v4's rungs bunch up at the
    finished end of the ladder. Needs GOOGLE_API_KEY.
    """
    from google import genai
    from google.genai import types

    key = os.getenv("GOOGLE_API_KEY")
    if not key:
        sys.exit("ERROR: --engine gemini needs GOOGLE_API_KEY in .env")
    cl = genai.Client(api_key=key)
    with open(master, "rb") as f:
        img = types.Part.from_bytes(data=f.read(), mime_type="image/png")

    r = cl.models.generate_content(model=model, contents=[prompt, img])
    for cand in (r.candidates or []):
        for part in (cand.content.parts or []):
            blob = getattr(part, "inline_data", None)
            if blob and blob.data:
                with open(dst, "wb") as f:
                    f.write(blob.data)
                return dst
    sys.exit(f"ERROR: {model} returned no image for {os.path.basename(dst)}: "
             f"{getattr(r, 'text', '')[:300]}")


def crop_master(source, dst, box):
    """Fractional crop (x,y,w,h of the source image), resized to 9:16.

    The box is expanded to 9:16 around its own center, then SHIFTED back
    inside the image if it overhangs an edge — never clamped in one
    dimension only, which would squash the geometry when resized (measured:
    a low-in-frame crop clamped to 0.78 aspect got squeezed ~40%% wide).
    """
    from PIL import Image
    img = Image.open(source)
    W, H = img.size
    x, y, w, h = box
    px, py, pw, ph = int(x * W), int(y * H), int(w * W), int(h * H)
    target = 9 / 16
    if pw / ph > target:
        ph = int(pw / target)
    else:
        pw = int(ph * target)
    # if the 9:16 box is bigger than the image, shrink it keeping the aspect
    scale = min(W / pw, H / ph, 1.0)
    pw, ph = int(pw * scale), int(ph * scale)
    # center on the original box, then shift fully inside the frame
    cx = int((x + w / 2) * W)
    cy = int((y + h / 2) * H)
    px = min(max(0, cx - pw // 2), W - pw)
    py = min(max(0, cy - ph // 2), H - ph)
    img.crop((px, py, px + pw, py + ph)).resize((1080, 1920),
                                                 Image.LANCZOS).save(dst)
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default="wolf_watermelon")
    ap.add_argument("--subject", default="snarling gray wolf head")
    ap.add_argument("--master-gen", type=int, default=0, metavar="N",
                    help="Generate N master candidates and stop (curate by eye).")
    ap.add_argument("--master", default=None,
                    help="Path to the curated master still; builds the "
                         "regression rungs from it.")
    ap.add_argument("--crop", action="append", default=[],
                    metavar="NAME[:SOURCE]:X,Y,W,H",
                    help="Cut a macro rung as a fractional crop. SOURCE is a "
                         "rung name (e.g. stage_C_upper_face) and should "
                         "almost always be a PARTIAL rung — cropping the "
                         "master was the v4 mistake. Omitting SOURCE crops "
                         "the master. Repeatable.")
    ap.add_argument("--aspect", default="9:16",
                    help="Aspect ratio for generated masters. MUST match the "
                         "video job's aspect_ratio or Veo letterboxes.")
    ap.add_argument("--crops-only", action="store_true",
                    help="Skip the (paid) ladder edits; only cut crops. Use "
                         "when the rungs are already built and QC'd.")
    ap.add_argument("--only", default=None, help="Build one regression rung.")
    ap.add_argument("--engine", choices=("gemini", "grok"), default="gemini",
                    help="Edit engine for the regression rungs. gemini "
                         "(gemini-3-pro-image) holds region-limited edits "
                         "better; grok is the xAI /images/edits path.")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    seeds_dir = os.path.join(ROOT, args.project, "seeds")
    os.makedirs(seeds_dir, exist_ok=True)

    if args.master_gen:
        prompt = MASTER_PROMPT.format(subject=args.subject)
        if args.dry_run:
            print(f"=== master x{args.master_gen}\n{prompt}")
            return
        import re
        taken = [int(m.group(1)) for f in os.listdir(seeds_dir)
                 if (m := re.match(r"master_take(\d+)\.png$", f))]
        # max-index, not count: curation deletes takes, and counting would
        # renumber into a surviving keeper and overwrite it
        i = max(taken, default=0)
        if args.engine == "gemini":
            for _ in range(args.master_gen):
                i += 1
                dst = os.path.join(seeds_dir, f"master_take{i}.png")
                generate_master_gemini(prompt, dst, aspect=args.aspect)
                print(f"  [{args.aspect}] -> {dst}")
        else:
            for d in gs.generate_image(prompt, "grok-imagine-image-quality",
                                        n=args.master_gen):
                i += 1
                dst = os.path.join(seeds_dir, f"master_take{i}.png")
                gs.download(d["url"], dst)
                print(f"  -> {dst}  (WARNING: Grok emits 3:4 — a 9:16 video "
                      f"job will letterbox this)")
        print("\nCurate by eye; rename the keeper to seeds/master.png, then "
              "re-run with --master.")
        return

    if not args.master:
        sys.exit("Pass --master-gen N to make candidates, or --master <path> "
                 "to build the ladder.")

    master = args.master if os.path.isfile(args.master) \
        else os.path.join(ROOT, args.project, args.master)
    if not os.path.isfile(master):
        sys.exit(f"ERROR: master not found: {args.master}")

    for name, source, body in LADDER:
        if args.crops_only:
            break
        if args.only and args.only != name:
            continue
        prompt = body.format(subject=args.subject)
        dst = os.path.join(seeds_dir, f"{name}.png")
        src = master if source == "master" \
            else os.path.join(seeds_dir, f"{source}.png")
        if args.dry_run:
            print(f"\n=== {name} [{args.engine}] <- {os.path.basename(src)}"
                  f"\n{prompt}")
            continue
        if not os.path.isfile(src):
            sys.exit(f"ERROR: {name} needs {os.path.basename(src)} first — "
                     f"build the ladder in order (drop --only).")
        if args.engine == "gemini":
            edit_with_gemini(prompt, src, dst)
        else:
            gs.download(gs.edit_image(prompt, src), dst)
        print(f"  [{args.engine}] {os.path.basename(src)} -> {dst}")

    for spec in args.crop:
        parts = spec.split(":")
        if len(parts) == 2:
            name, boxs = parts
            src = master
        elif len(parts) == 3:
            name, source, boxs = parts
            src = os.path.join(seeds_dir, f"{source}.png")
            if not os.path.isfile(src):
                sys.exit(f"ERROR: crop source rung not found: {src}")
        else:
            sys.exit(f"ERROR: bad --crop spec {spec!r} "
                     f"(want NAME[:SOURCE]:X,Y,W,H)")
        box = tuple(float(v) for v in boxs.split(","))
        dst = os.path.join(seeds_dir, f"crop_{name}.png")
        if args.dry_run:
            print(f"\n=== crop_{name} <- {os.path.basename(src)} box={box}")
            continue
        crop_master(src, dst, box)
        print(f"  [crop] {os.path.basename(src)} -> {dst}")

    if not args.dry_run:
        print(f"\nLadder in {seeds_dir}. EYEBALL EVERY RUNG before spending on "
              f"video — a bad rung poisons its shot.")


if __name__ == "__main__":
    main()
