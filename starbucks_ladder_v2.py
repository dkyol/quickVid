#!/usr/bin/env python3
"""
starbucks_ladder_v2.py — v2 of the Starbucks siren carve ladder
(starbucks_watermelon_v2), built the same edit-not-generate way as
starbucks_ladder.py (see carvingSkill.MD Step 2), but starting from a
richer master target: SB_logo.jpg as the --reference source, styled to
match Final_look.jpg / the second reference (agent_generate_image...) —
no hands, resting on a surface, a dense flower-and-vine border with FOUR
carved flower rosettes, natural mottled dark-green rind outside the carve,
and an irregular scalloped carved-area edge instead of a clean ring.

Region mapping (same direction rule as v1's starbucks_ladder.py):
  - stage_A_outline    : subtractive, from master  (0%   — pure line-art)
  - stage_B_crown_star : additive,   from A         (~15% — crown + star)
  - stage_C_face        : additive,   from B         (~40% — + siren face)
  - stage_D_hair         : additive,   from C         (~65% — + hair waves)
  - stage_E_no_border    : subtractive, from master  (~85% — medallion done,
                             border ring still flat line-art)
  - stage_F_border_vines : additive,   from E         (~95% — vines/leaves
                             carved, the 4 flowers still flat outline —
                             isolates the flowers as the LAST, smallest,
                             most bounded carve for a canary-safe macro)

Usage:
    python starbucks_ladder_v2.py --master-gen 4
    # curate seeds/master_take{N}.png by eye -> rename keeper to seeds/master.png
    python starbucks_ladder_v2.py --dry-run
    python starbucks_ladder_v2.py
    python starbucks_ladder_v2.py --only stage_C_face
    python starbucks_ladder_v2.py --crops-only
"""

import argparse
import os
import re
import sys

from dotenv import load_dotenv

import make_ladder as ml

ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(ROOT, ".env"))

PROJECT = "starbucks_watermelon_v2"
REFERENCE = os.path.join("C:\\", "Users", "DKYLE", "Downloads", "SB_logo.jpg")

# NOT ml.KEEP — that constant says "keep... the hands... exactly the same",
# a leftover from v1's hands-holding master. Our v2 master has NO hands, so
# that clause would tell the edit model to preserve hands that don't exist
# (risk: it invents some). Own version, same intent, hands-free.
KEEP = ("Keep the melon's shape and position, the lighting and the "
        "background exactly the same as the original image. Only "
        "watermelon colors anywhere: dark green rind, pale green-white "
        "inner rind, cream pith — no grey, no black, no brown, no red "
        "flesh anywhere. No hands, no arms anywhere.")

# ---------------------------------------------------------------------------
# Master prompt — image-conditioned on SB_logo.jpg, styled to match
# Final_look.jpg and the agent_generate_image reference: no hands, resting
# on a plain surface, natural mottled rind, dense flower-vine border with
# 4 rosettes, scalloped (not ring-clean) carved-area edge.
# ---------------------------------------------------------------------------
MASTER_PROMPT_V2 = (
    "Photorealistic vertical 9:16 photograph, soft flat diffused daylight, "
    "no hard shadows, a plain light grey-white seamless background with a "
    "soft contact shadow beneath. A whole ripe dark green watermelon rests "
    "directly on a plain white surface, front-facing camera, filling most "
    "of the frame, NO hands or arms anywhere in the shot. Carve the "
    "attached reference image's exact siren medallion design — same "
    "shapes, same proportions, same silhouette, do not redesign or "
    "simplify it — into the rind in SHALLOW BAS-RELIEF, at most one to two "
    "centimeters deep, cut INTO the curved surface, nothing protruding "
    "beyond the melon's original surface, the melon's smooth round "
    "silhouette unbroken. The design reads through layer contrast alone: "
    "dark green outer rind left uncarved for the crown outline, the "
    "medallion ring line, the siren's hair-strand outlines and dark "
    "background inside the ring, pale green-white inner rind exposed for "
    "the crown interior, the star, the siren's face and the pale hair-wave "
    "shapes. Surrounding the medallion ring, carve a dense, richly "
    "detailed decorative border in traditional Thai fruit-carving style: "
    "an interlocking leaf-and-curling-vine pattern with exactly FOUR "
    "carved flower rosettes (each with layered overlapping petals in pale "
    "carved rind and a small distinct carved center) spaced evenly around "
    "the ring — roughly top, bottom, left and right — connected by curling "
    "carved vine tendrils and individual serrated leaf shapes. The outer "
    "edge of this carved border is IRREGULAR and organic, scalloped and "
    "slightly ragged where the carving stops — not a clean geometric "
    "circle — transitioning into the melon's natural UNCARVED rind beyond "
    "it. That natural rind shows authentic watermelon skin: dark green "
    "with subtle lighter jade mottled streaks and blotches, not a flat "
    "solid color. A few thin curled pale rind shavings and one or two "
    "small loose carved leaf or petal offcuts rest on the white surface in "
    "front of the melon. The ONLY colors in frame are watermelon colors — "
    "dark green rind with its natural mottling, pale green-white carved "
    "rind, cream pith; no red flesh, no grey, no black, no brown anywhere "
    "except the rind's own natural mottling. It is a carved watermelon, "
    "like traditional Thai fruit carving: not a sticker, not painted, not "
    "a flat print of the reference logo. Matte natural texture, crisp fine "
    "detail, no glow, no airbrush. No text, no watermark, no phone UI, no "
    "hands, no arms, no utensils in frame."
)

LADDER = [
    ("stage_A_outline", "master",
     "Replace the entire carved Starbucks siren emblem — the crown, the "
     "star, the siren's face and hair, the circular medallion ring, and "
     "the flower-and-vine border — with the SAME design drawn ONLY as "
     "thin dark outline strokes on the smooth intact dark green watermelon "
     "rind: pure line-art like a marker sketch, no shading, no grey tones, "
     "no tonal rendering, no fill. Nothing is carved anywhere: no relief, "
     "no grooves, no pale inner rind, no shavings, no debris on the "
     "surface. The rind stays uniform dark green (with its natural subtle "
     "mottling only) everywhere, its round silhouette unbroken. No hands, "
     "no arms. " + KEEP),

    ("stage_B_crown_star", "stage_A_outline",
     "Carve ONLY the crown and the star above it into shallow pale relief "
     "with a clean cut edge where the blade stopped, and let one small "
     "curl of green rind lift away there. The knife touches NOTHING else. "
     "The siren's hair strands remain COMPLETELY UNCARVED right now — "
     "still only thin dark outline strokes on smooth intact dark green "
     "rind, exactly like the face, the medallion ring and the border: no "
     "pale relief anywhere in the hair, no wavy carved bands, no "
     "alternating light/dark strands yet, just the flat line drawing. "
     "Everything else in the image — the siren's face and hair, the "
     "medallion ring, and the whole flower-and-vine border — stays "
     "EXACTLY the flat dark line-art drawing on intact dark green rind "
     "that it is now. About one sixth of the design is carved. No hands, "
     "no arms. " + KEEP),

    ("stage_C_face", "stage_B_crown_star",
     "Keeping the already-carved crown and star exactly as they are, now "
     "ALSO carve the siren's face: forehead, closed eyes, nose and closed "
     "smiling mouth, with a clean cut edge running just below the chin. "
     "MATCH THE FINISHED CARVING'S RENDERING: the face keeps DARK GREEN "
     "rind for its outline strokes and PALE carved rind is used for the "
     "skin areas — do not carve the face into a flat solid shape, keep "
     "the linework crisp. The hair strands remain COMPLETELY UNCARVED "
     "right now, exactly as they were before this edit — still only thin "
     "dark outline strokes on smooth intact dark green rind, no pale "
     "relief, no wavy carved bands. The hair strands, the medallion ring, "
     "and the whole flower-and-vine border stay EXACTLY the flat dark "
     "line-art drawing on intact dark green rind. A few rind shavings lie "
     "on the surface in front of the melon. No hands, no arms. " + KEEP),

    ("stage_D_hair", "stage_C_face",
     "Keeping the already-carved crown, star and face exactly as they "
     "are, now ALSO carve the siren's wavy hair strands flanking the face "
     "into shallow pale relief, each wave a separate clean knife cut with "
     "dark green rind kept between the strands. MATCH THE FINISHED "
     "CARVING'S RENDERING: same wave shapes and spacing as the finished "
     "design, no redesign. The medallion ring and the whole "
     "flower-and-vine border stay EXACTLY the flat dark line-art drawing "
     "on intact dark green rind. More rind shavings lie on the surface in "
     "front of the melon. No hands, no arms. " + KEEP),

    ("stage_E_no_border", "master",
     "Remove ONLY the decorative flower-and-vine border ring that "
     "surrounds the medallion: replace it with flat thin dark line-art "
     "drawing on smooth intact dark green rind — the vines, leaves and "
     "all four flowers visible only as outline, nothing carved there, no "
     "relief anywhere in the border band. The crown, star, siren's face "
     "and hair inside the medallion ring must stay EXACTLY as they are — "
     "identical carving, identical linework, identical shape, same style, "
     "not redrawn. Rind shavings are scattered on the surface in front of "
     "the melon. No hands, no arms. " + KEEP),

    ("stage_F_border_vines", "stage_E_no_border",
     "Keeping the medallion (crown, star, face, hair) EXACTLY as already "
     "carved, now carve ONLY the vine tendrils and leaf shapes of the "
     "border into shallow pale relief, clean cut edges, a few curls of "
     "rind lifting away. The FOUR flower rosettes stay COMPLETELY "
     "UNCARVED — still just their thin dark outline on smooth intact dark "
     "green rind, no petals carved, no relief, no fill on the flowers "
     "yet. More rind shavings and one small leaf offcut lie on the "
     "surface in front of the melon. No hands, no arms. " + KEEP),
]


CROPS = [
    # name, source rung, (x, y, w, h) fractional box — all from stage_F:
    # medallion (crown/star/face/hair) matches master exactly there, vines
    # are carved, and the 4 flowers are still flat outline — one source
    # serves every macro, including the flower "before" frame.
    ("crown_star", "stage_F_border_vines", (0.24, 0.28, 0.40, 0.24)),
    ("hair_wave", "stage_F_border_vines", (0.44, 0.46, 0.22, 0.28)),
    ("face", "stage_F_border_vines", (0.28, 0.44, 0.32, 0.26)),
    ("flower_tl_outline", "stage_F_border_vines", (0.05, 0.26, 0.30, 0.22)),
]


# Hand-built end-frame for the ONE small bounded transition shot (the
# top-left flower, outline -> carved). Per carvingSkill.MD Step 5: pin BOTH
# the start and end frame for any shot showing a small state change and
# interpolate between them, rather than open-ended i2v with nothing to
# anchor where the shot should land.
END_FRAMES = [
    ("hair_wave_deepened", "crop_hair_wave",
     "Deepen ONE of the already-carved hair wave grooves with a short clean "
     "knife stroke, lifting one thin curl of rind that falls away. The "
     "freshly cut surface directly under the lifted curl, and the curl's "
     "own inner surface, must be solid pale green-white -- NEVER dark "
     "green underneath, not even a thin dark line. Everything else in the "
     "image -- every other hair wave, the medallion ring, the border "
     "scrollwork -- stays EXACTLY pixel-identical, not redrawn, not "
     "shifted. No hands, no arms. " + KEEP),
    ("flower_tl_carved", "crop_flower_tl_outline",
     "Carve ONLY this one flower rosette into shallow pale relief, matching "
     "the finished carving's style: layered overlapping petals in pale "
     "carved rind with crisp dark green outline strokes between petals, and "
     "a small distinct carved center. Let one thin curl of dark green rind "
     "lift and fall away near the flower onto the surface below. Everything "
     "else in the image — the vine, the leaf, the carved leaf edges, the "
     "background rind and its natural mottling, the framing — stays "
     "EXACTLY pixel-identical, not redrawn, not shifted. No hands, no "
     "arms. " + KEEP),
]


def gemini_master_gen(dst, aspect="9:16"):
    if not os.path.isfile(REFERENCE):
        sys.exit(f"ERROR: reference logo not found: {REFERENCE}")
    return ml.generate_master_from_reference(MASTER_PROMPT_V2, REFERENCE, dst,
                                              aspect=aspect)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--master-gen", type=int, default=0,
                     help="Generate N master candidates and stop.")
    ap.add_argument("--aspect", default="9:16")
    ap.add_argument("--only", default=None)
    ap.add_argument("--crops-only", action="store_true")
    ap.add_argument("--end-frames-only", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    seeds_dir = os.path.join(ROOT, PROJECT, "seeds")
    os.makedirs(seeds_dir, exist_ok=True)

    if args.master_gen:
        if args.dry_run:
            print(f"=== master x{args.master_gen} <- {REFERENCE}\n"
                  f"{MASTER_PROMPT_V2}")
            return
        taken = [int(m.group(1)) for f in os.listdir(seeds_dir)
                 if (m := re.match(r"master_take(\d+)\.png$", f))]
        i = max(taken, default=0)
        for _ in range(args.master_gen):
            i += 1
            dst = os.path.join(seeds_dir, f"master_take{i}.png")
            gemini_master_gen(dst, aspect=args.aspect)
            print(f"  [{args.aspect}] <- {os.path.basename(REFERENCE)} -> {dst}")
        print("\nCurate by eye; rename the keeper to seeds/master.png, then "
              "re-run without --master-gen.")
        return

    master = os.path.join(seeds_dir, "master.png")
    if not os.path.isfile(master):
        sys.exit(f"ERROR: master not found: {master} — run --master-gen "
                  f"first and curate a keeper.")

    if args.end_frames_only:
        for name, source, prompt in END_FRAMES:
            dst = os.path.join(seeds_dir, f"{name}.png")
            src = os.path.join(seeds_dir, f"{source}.png")
            if args.dry_run:
                print(f"\n=== {name} <- {os.path.basename(src)}\n{prompt}")
                continue
            if not os.path.isfile(src):
                sys.exit(f"ERROR: end-frame source not found: {src}")
            ml.edit_with_gemini(prompt, src, dst)
            print(f"  [gemini] {os.path.basename(src)} -> {dst}")
        return

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
        print(f"\nLadder in {seeds_dir}. EYEBALL EVERY RUNG at full "
              f"resolution before spending on video.")


if __name__ == "__main__":
    main()
