#!/usr/bin/env python3
"""
starbucks_ladder.py — project-specific carve ladder for the Starbucks siren
medallion (starbucks_watermelon), built the same way make_ladder.py's wolf
LADDER is: every rung is an EDIT of the master (or of another rung), never
fresh text-to-image (see carvingSkill.MD Step 2).

Region mapping used here (siren medallion has no ears/muzzle, so the wolf
LADDER's anatomy doesn't transfer word-for-word, but the DIRECTION rule
does):
  - stage_A_outline   : subtractive, from master  (0%   — pure line-art)
  - stage_B_crown_star: additive,   from A         (~15% — crown + star only)
  - stage_C_face       : additive,   from B         (~40% — + siren face)
  - stage_D_hair        : additive,   from C         (~70% — + hair waves)
  - stage_E_no_border   : subtractive, from master  (~90% — border ring only
                            missing; mirrors the wolf ladder's D_muzzle trick
                            of regressing a SPATIALLY SEPARATE region, which
                            edit models can do reliably, instead of trying to
                            un-carve the subject itself)

Usage:
    python starbucks_ladder.py --dry-run
    python starbucks_ladder.py
    python starbucks_ladder.py --only stage_C_face
    python starbucks_ladder.py --crops-only
"""

import argparse
import os
import sys

from dotenv import load_dotenv

import make_ladder as ml

ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(ROOT, ".env"))

PROJECT = "starbucks_watermelon"

KEEP = ml.KEEP  # identical color/composition guard used by the wolf ladder

LADDER = [
    ("stage_A_outline", "master",
     "Replace the entire carved Starbucks siren emblem — the crown, the "
     "star, the siren's face and hair, the circular medallion ring, and the "
     "leaf border — with the SAME design drawn ONLY as thin dark outline "
     "strokes on the smooth intact dark green watermelon rind: pure "
     "line-art like a marker sketch, no shading, no grey tones, no tonal "
     "rendering, no fill. Nothing is carved anywhere: no relief, no "
     "grooves, no pale inner rind, no shavings. The rind stays uniform dark "
     "green everywhere, its round silhouette unbroken. " + KEEP),

    ("stage_B_crown_star", "stage_A_outline",
     "Carve ONLY the crown and the star above it into shallow pale relief "
     "with a clean cut edge where the blade stopped, and let one small "
     "curl of green rind lift away there. Everything else in the image — "
     "the siren's face and hair, the medallion ring, and the whole leaf "
     "border — stays EXACTLY the flat dark line-art drawing on intact dark "
     "green rind that it is now. About one sixth of the design is carved. "
     + KEEP),

    ("stage_C_face", "stage_B_crown_star",
     "Keeping the already-carved crown and star exactly as they are, now "
     "ALSO carve the siren's face: forehead, closed eyes, nose and closed "
     "smiling mouth, with a clean cut edge running just below the chin. "
     "MATCH THE FINISHED CARVING'S RENDERING: the face keeps DARK GREEN "
     "rind for its outline strokes and PALE carved rind is used for the "
     "skin areas — do not carve the face into a flat solid shape, keep the "
     "linework crisp. The hair strands, the medallion ring, and the whole "
     "leaf border stay EXACTLY the flat dark line-art drawing on intact "
     "dark green rind. A few rind shavings lie on the surface below the "
     "melon. " + KEEP),

    ("stage_D_hair", "stage_C_face",
     "Keeping the already-carved crown, star and face exactly as they are, "
     "now ALSO carve the siren's wavy hair strands flanking the face into "
     "shallow pale relief, each wave a separate clean knife cut with dark "
     "green rind kept between the strands. MATCH THE FINISHED CARVING'S "
     "RENDERING: same wave shapes and spacing as the finished design, no "
     "redesign. The medallion ring and the whole leaf border stay EXACTLY "
     "the flat dark line-art drawing on intact dark green rind. More rind "
     "shavings lie on the surface below the melon. " + KEEP),

    ("stage_E_no_border", "master",
     "Remove ONLY the decorative leaf border ring that surrounds the "
     "medallion: replace it with flat thin dark line-art drawing on smooth "
     "intact dark green rind, as if the border has not been carved yet. "
     "The crown, star, siren's face and hair inside the medallion ring "
     "must stay EXACTLY as they are — identical carving, identical "
     "linework, identical shape, same style, not redrawn. Rind shavings "
     "are scattered on the surface below the melon. " + KEEP),
]

CROPS = [
    # name, source rung, (x, y, w, h) fractional box
    ("crown_star", "stage_C_face", (0.28, 0.24, 0.42, 0.22)),
    ("hair_wave", "stage_D_hair", (0.10, 0.42, 0.35, 0.28)),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    ap.add_argument("--crops-only", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    seeds_dir = os.path.join(ROOT, PROJECT, "seeds")
    os.makedirs(seeds_dir, exist_ok=True)
    master = os.path.join(seeds_dir, "master.png")
    if not os.path.isfile(master):
        sys.exit(f"ERROR: master not found: {master}")

    for name, source, prompt in LADDER:
        if args.crops_only:
            break
        if args.only and args.only != name:
            continue
        dst = os.path.join(seeds_dir, f"{name}.png")
        src = master if source == "master" \
            else os.path.join(seeds_dir, f"{source}.png")
        if args.dry_run:
            print(f"\n=== {name} <- {os.path.basename(src)}\n{prompt}")
            continue
        if not os.path.isfile(src):
            sys.exit(f"ERROR: {name} needs {os.path.basename(src)} first — "
                     f"build the ladder in order (drop --only).")
        ml.edit_with_gemini(prompt, src, dst)
        print(f"  [gemini] {os.path.basename(src)} -> {dst}")

    for name, source, box in CROPS:
        src = os.path.join(seeds_dir, f"{source}.png")
        dst = os.path.join(seeds_dir, f"crop_{name}.png")
        if args.dry_run:
            print(f"\n=== crop_{name} <- {os.path.basename(src)} box={box}")
            continue
        if not os.path.isfile(src):
            sys.exit(f"ERROR: crop source rung not found: {src}")
        ml.crop_master(src, dst, box)
        print(f"  [crop] {os.path.basename(src)} -> {dst}")

    if not args.dry_run:
        print(f"\nLadder in {seeds_dir}. EYEBALL EVERY RUNG before spending "
              f"on video.")


if __name__ == "__main__":
    main()
