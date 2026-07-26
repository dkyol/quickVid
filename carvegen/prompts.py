"""Prompt engineering for continuous carving process videos.

The heart of the product. A good carving clip needs, in every segment:
  1. the RIGHT MATERIAL BEHAVIOR (rind->pith->flesh, or wood grain->shavings),
  2. the RIGHT STAGE of the process (outline / peeling / deep / final),
  3. SUBJECT CONSISTENCY (same subject, same framing, locked camera),
  4. a strong NEGATIVE prompt to suppress the usual AI failure modes.

`build_segment_prompt()` composes these from a Job + Segment. `enhance()` is a
light refiner that appends the shared cinematography/quality clause. Swap
subjects/materials by changing the Job, not the templates.
"""

from textwrap import dedent

# --------------------------------------------------------------------------- #
# Materials — the layer stack the knife/chisel reveals, plus debris + wetness.
# This is what makes the carve read as REAL rather than a morphing render.
# --------------------------------------------------------------------------- #
MATERIALS = {
    "watermelon": {
        "surface": "the smooth dark-green striped watermelon rind",
        "outer_layer": "dark green rind",
        "mid_layer": "firm pale white pith / rind layer",
        "inner_layer": "vivid red juicy flesh with black seeds",
        "debris": "thin curls of green rind peeling away and dropping, wet "
                  "shavings collecting below",
        "wetness": "glossy moisture, juice sheen on the blade, droplets",
        "tool": "a small sharp paring/carving knife",
        "palette_rule": "the subject is rendered ENTIRELY in the melon's own "
                        "layers — dark green rind for outlines, nose and dark "
                        "markings, pale carved rind as the fur/skin with the "
                        "melon's green striations as natural shading, and red "
                        "flesh only where cut deepest (open mouth, tongue, inner "
                        "ears). It is a carved watermelon, not painted, not a "
                        "grey sculpture.",
    },
    "wood": {
        "surface": "the solid wood block with visible grain",
        "outer_layer": "rough outer wood",
        "mid_layer": "pale carved heartwood",
        "inner_layer": "deep smooth polished wood facets",
        "debris": "long curling wood shavings flying off, sawdust settling",
        "wetness": "fine tool marks catching soft light, satin sheen",
        "tool": "a chisel and gouge",
        "palette_rule": "the subject is carved from one continuous piece of "
                        "wood — warm grain flowing through the form, pale freshly "
                        "cut facets against darker aged surface, no paint.",
    },
}

# --------------------------------------------------------------------------- #
# Stages — the satisfying arc. Each describes the ACTION for that phase so the
# clip shows change happening, not a static hero shot.
# --------------------------------------------------------------------------- #
STAGES = {
    "outline": (
        "{tool} lightly scores the outline of {subject} onto {surface}, "
        "etching clean guide lines and the major shapes; only shallow scoring "
        "so far, the surface still mostly whole."
    ),
    "peeling": (
        "{tool} peels away {outer_layer} in {debris}, roughing out the silhouette "
        "of {subject} and exposing the {mid_layer} underneath; the form starts "
        "to emerge in relief."
    ),
    "deep_carving": (
        "confident deeper cuts sculpt the three-dimensional form of {subject} — "
        "{features} — carving well into the {mid_layer} and opening the "
        "{inner_layer} where depth is greatest; {debris}, {wetness}."
    ),
    "final_details": (
        "fine detailing passes add texture and sharpen every feature of {subject} "
        "({features}), edges cleaned and refined, ending on the finished, polished "
        "{subject} {material} carving held up to camera — a clean satisfying hero "
        "reveal with a slow subtle turn."
    ),
}

# Shared cinematography + quality clause appended to every segment.
CINEMATOGRAPHY = (
    "Locked-off vertical macro shot, subject centered and filling the frame, "
    "shallow depth of field, soft directional natural light, slow gentle "
    "push-in; hands and {tool} stay steady and consistent; photorealistic, "
    "ultra-detailed, high fidelity, satisfying oddly-satisfying process video."
)

# Negative prompt — the recurring failure modes for carving/hand videos.
NEGATIVE = {
    "default": (
        "blurry, low detail, low quality, distorted anatomy, deformed hands, "
        "extra fingers, extra knives, melting, morphing, warping, flickering, "
        "the subject changing identity, inconsistent subject, cartoonish, flat, "
        "painted-on texture, sticker look, text, watermark, logo, letterbox, "
        "jump cut, static frozen image, camera shake"
    ),
    "watermelon_extra": (
        ", grey fur, realistic grey animal, opaque plastic look, ceramic, dry "
        "cracked rind"
    ),
    "wood_extra": ", plastic, metal, painted colors, glossy lacquer",
}

# Optional per-subject feature hints (fills {features}). Extend freely — or set
# `features` via a segment's prompt_extra. These keep detailing specific.
SUBJECT_FEATURES = {
    "wolf": "layered fur tufts, almond eyes, snarling muzzle, bared fangs, "
            "pointed ears, wet nose",
    "lion": "flowing mane, broad muzzle, intense eyes, open roaring mouth, teeth",
    "eagle": "feather layers, sharp hooked beak, fierce eye, brow ridge",
    "dragon": "overlapping scales, horns, snarling jaw, spikes, slit eyes",
    "rose": "layered curved petals, tight center bud, leaves",
    "skull": "eye sockets, cheekbones, nasal cavity, rows of teeth, cranial sutures",
}


def _features_for(subject):
    s = subject.lower()
    for key, feats in SUBJECT_FEATURES.items():
        if key in s:
            return feats
    return "its defining features in fine detail"


def negative_for(material, override=None):
    if override:
        return override
    base = NEGATIVE["default"]
    return base + NEGATIVE.get(f"{material}_extra", "")


def build_segment_prompt(job, segment):
    """Compose the full positive prompt for one segment from job + segment.
    A `prompt_override` on the segment bypasses everything."""
    if segment.prompt_override:
        return segment.prompt_override.strip()

    mat = MATERIALS.get(job.material)
    if not mat:
        raise SystemExit(f"unknown material '{job.material}' "
                         f"(have: {', '.join(MATERIALS)})")
    stage_tpl = STAGES.get(segment.stage)
    if not stage_tpl:
        raise SystemExit(f"unknown stage '{segment.stage}' "
                         f"(have: {', '.join(STAGES)})")

    fields = dict(
        subject=job.subject,
        material=job.material,
        features=_features_for(job.subject),
        **{k: mat[k] for k in
           ("surface", "outer_layer", "mid_layer", "inner_layer",
            "debris", "wetness", "tool")},
    )

    stage_text = stage_tpl.format(**fields)
    cine = CINEMATOGRAPHY.format(tool=mat["tool"])

    parts = [
        f"Continuous time-lapse process video: a person carves {job.subject} "
        f"from {mat['surface'].replace('the smooth ', 'a ').replace('the ', 'a ')} "
        f"in the style of {job.style}.",
        stage_text,
        mat["palette_rule"],
        cine,
    ]
    if segment.prompt_extra:
        parts.append(segment.prompt_extra.strip())
    return enhance(" ".join(p.strip() for p in parts if p.strip()))


def enhance(prompt):
    """Light refinement pass: collapse whitespace and guarantee the quality
    tail is present. Kept deliberately simple/deterministic (no LLM call) so
    output is reproducible; swap in an LLM call here if you want richer
    rewriting later."""
    text = " ".join(prompt.split())
    tail = "4K, crisp focus, realistic materials and physics"
    if tail.lower() not in text.lower():
        text = f"{text} {tail}."
    return text


# High-quality, copy-paste starter overrides for common subjects. Use as a
# segment `prompt_override`, or as inspiration. Each is a FULL single-segment
# carve (good with duration 10 + a start seed).
TEMPLATES = {
    "wolf_watermelon": dedent("""\
        Continuous time-lapse macro video, vertical 9:16: two hands carve a
        snarling gray wolf head into a whole dark-green watermelon using a small
        sharp knife. It begins by scoring the wolf outline into the rind, then
        peels away curling strips of green rind that drop away, then deeper cuts
        sculpt the muzzle, almond eyes, layered fur and pointed ears in the pale
        white rind layer, and finally the knife opens the snarling mouth to
        reveal vivid red flesh as the tongue and inner mouth with pale carved
        fangs. The wolf is rendered entirely in the melon's own colors — dark
        green rind for outlines and nose, pale carved rind with green striations
        as the fur shading, red flesh only in the open mouth — a carved
        watermelon, not painted, not grey. Wet blade, juice sheen, shavings
        collecting. Locked macro shot, shallow depth of field, soft light, slow
        push-in, photorealistic, ultra-detailed, oddly satisfying. 4K."""),
    "lion_wood": dedent("""\
        Continuous time-lapse macro video, vertical 9:16: hands carve a roaring
        lion head from a solid wood block using a chisel and gouge. First the
        outline is scored into the grain, then long curling wood shavings fly
        off to rough out the mane and muzzle, then deep confident cuts sculpt
        the flowing mane, broad muzzle, intense eyes and open roaring mouth with
        teeth, ending on the finished polished wood lion held to camera. Warm
        wood grain flowing through the form, pale fresh-cut facets, sawdust and
        shavings, fine tool marks, satin sheen, no paint. Locked macro shot,
        shallow depth of field, soft light, slow push-in, photorealistic,
        ultra-detailed, oddly satisfying. 4K."""),
    "rose_watermelon": dedent("""\
        Continuous time-lapse macro video, vertical 9:16: hands carve a blooming
        rose into a whole watermelon with a small knife. Outline scored into the
        green rind, then rind peeled in curls to rough the petals, then deeper
        cuts layer the curved petals in the pale rind with a tight center bud,
        edges refined into a delicate rose, red flesh hinted at the deepest
        center. Rendered in the melon's own green-and-white layers, wet sheen,
        shavings, no paint. Locked macro shot, shallow depth of field, soft
        light, slow push-in, photorealistic, ultra-detailed, satisfying. 4K."""),
}
