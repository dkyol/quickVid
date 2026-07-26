# carvegen — Kling-powered continuous carving videos

> ## ⚠ LEGACY — do not run `carve.py gen`
>
> **The current carving pipeline is Grok Imagine — see `imageGenSkill.MD`.**
>
> Two things broke this route:
> 1. The direct Kling API account at kling.ai/dev is **unfunded** — every
>    generate call fails with `code 1102: Account balance not enough`. The
>    client in `carvegen/kling_client.py` points there.
> 2. Kling now runs through the Higgsfield MCP instead, where the model that
>    would actually help (`kling3_0`, the only one taking **both**
>    `start_image` + `end_image`) is gated behind a Pro/Ultimate plan. The
>    reachable `kling3_0_turbo` was tested head-to-head against Grok on the
>    same seed and lost badly: it left ~85% of the subject an uncarved
>    drawing.
>
> **Still useful here, and still worth calling:**
> - `python carve.py plan <reference.mp4> --project <proj>` — reference-video
>   stage planner, no API spend.
> - `python carve.py gen jobs/<proj>.json --dry-run` — builds and prints full
>   carving prompts for free (paste into a Grok shot).
> - `carvegen/prompts.py` — templates, `SUBJECT_FEATURES`, negatives.
> - `carvegen/post.py` — ffmpeg conform + crossfade stitch + audio.
> - `carvegen/seeds.py` — Grok seed-image generation (still the seed path).
>
> Everything below describes the Kling contract as it was written.

Generate viral-style, vertical (9:16) **continuous carving process** videos: a
whole watermelon (or wood block) is progressively carved into a detailed
subject — snarling wolf, animal, object, face — through the satisfying arc
**outline → peeling → deep carving → final details**, ending on a clean hero
reveal. Video generation runs on **Kling AI's official API**; ffmpeg stitches
the segments into one Reels/TikTok-ready clip.

This replaces the earlier Grok Imagine pipeline (`generate_shots.py` /
`build_reel.py`, kept as legacy). Seed *image* generation can still optionally
use Grok; all *video* now uses Kling.

---

## 1. Why this architecture

Kling only generates **5s or 10s** clips, so a longer carve is built by
**stitching short segments**, one per carving stage. Two Kling features make
this far better than the old approach:

- **`image` (image-to-video)** — anchor a segment to a known first frame.
- **`image_tail` (end keyframe)** — anchor the *last* frame too. Give a
  segment `start_image` + `end_image` and Kling **interpolates the carve
  between two states you control** (e.g. outline → half-carved). This is the
  single biggest fidelity/consistency win and wasn't possible on Grok.

So the recommended pattern is a chain of segments where each segment's
`end_image` is the next segment's `start_image` — the subject stays locked to
your frames the whole way through.

## 2. Setup

```
pip install -r requirements.txt          # adds PyJWT
```
Get your Kling API key at https://kling.ai/dev and put it in `.env`:
```
KLING_API_KEY=...                                 # single key, sent as Bearer
# KLING_API_BASE=https://api-singapore.klingai.com   # global default; mainland = https://api.klingai.com
```
The single API key (Bearer) is the current scheme and covers the newest
models. A legacy `KLING_ACCESS_KEY` + `KLING_SECRET_KEY` pair (signed into a
JWT) still works if that's all you have, but won't unlock new models — the
client uses the API key when both are present.
Verify:
```
python carve.py check
```

## 3. Recommended Kling settings for carving

| Setting | Value | Why |
|---|---|---|
| `model` | `kling-v2-master` | best temporal consistency + motion realism (subject must stay identical across the carve). `kling-v1-6` = cheaper fallback. |
| `mode` | `pro` | crisper detail — rind texture, shavings, wet flesh are the whole appeal. |
| `duration` | `5` per segment | short clips stay on-model; reach length by stitching. Use `10` for fewer seams. |
| `aspect_ratio` | `9:16` | Reels/TikTok. |
| `cfg_scale` | `0.5` | follows the carving prompt without stiff/warpy motion. Raise toward 0.7 for tighter adherence. |

Confirm current model names/pricing in your Kling console — Kling ships new
model versions often (`kling-v2-6`, etc.); override per job via `"model"`.

## 4. Workflow

1. **(Optional) Plan seeds from a reference video** — decide how many seed
   frames and where:
   ```
   python carve.py plan "C:/path/to/reference.mp4" --project wolf_watermelon --every 4
   ```
   It extracts the reference frame at each moment to
   `wolf_watermelon/reference_frames/` and scaffolds the seed list.
2. **Provide seed images.** Recreate each planned moment in your style (or use
   any stills you have) and drop them in `wolf_watermelon/seeds/` as
   `seed_01.png`, `seed_02.png`, … A job references them by name. If you have
   no seed, a segment with no `start_image` falls back to text-to-video, or you
   can generate a seed still via Grok (see `carvegen/seeds.py`).
3. **Preview prompts for free:**
   ```
   python carve.py gen jobs/wolf_watermelon.json --dry-run
   ```
4. **Generate + stitch:**
   ```
   python carve.py gen jobs/wolf_watermelon.json
   ```
   Output: `wolf_watermelon/final/wolf_watermelon_<stamp>.mp4` plus a manifest
   JSON (every prompt + setting, for reproducibility).
5. **Iterate:** re-run with `--skip-existing` to only regenerate missing
   segments and re-stitch.

## 5. Job file schema (`jobs/*.json`)

```jsonc
{
  "project": "wolf_watermelon",          // -> <project>/media, /seeds, /final
  "subject": "snarling gray wolf head",  // swap this to change the carving
  "material": "watermelon",              // "watermelon" | "wood"
  "style":   "hyperrealistic fruit carving, macro process video",
  "model":   "kling-v2-master",
  "mode":    "pro",
  "aspect_ratio": "9:16",
  "cfg_scale": 0.5,
  "negative_prompt": null,               // null -> strong material default
  "output": { "crossfade": 0.4, "keep_source_audio": true, "music": null },
  "segments": [
    { "name": "01_outline", "stage": "outline",       "duration": 5,
      "start_image": "seed_01", "end_image": "seed_02" },
    { "name": "02_peeling", "stage": "peeling",        "duration": 5,
      "start_image": "seed_02", "end_image": "seed_03" },
    { "name": "03_deep",    "stage": "deep_carving",   "duration": 5,
      "start_image": "seed_03", "end_image": "seed_04" },
    { "name": "04_final",   "stage": "final_details",  "duration": 5,
      "start_image": "seed_04" }
  ]
}
```
- `stage` ∈ `outline | peeling | deep_carving | final_details` — selects the
  process-stage prompt template.
- `start_image`/`end_image` — seed names (in `seeds/` or `media/`), file paths,
  or URLs. Give both to interpolate a stage between two frames (`image_tail`).
- `prompt_extra` — appended to the built prompt; `prompt_override` — replace it.
- Audio: leave `music` null + `keep_source_audio` true to keep Kling's own
  carving foley (no music). Set `music` to a file to use a bed instead.

**Swap subjects/styles** by changing `subject`/`material`/`style` — the prompt
templates adapt (e.g. `"subject": "roaring lion head"`, `"material": "wood"`).

## 6. Code layout (separation of concerns)

```
carve.py                 CLI (check / gen / batch / plan)
carvegen/
  config.py              settings + job schema + recommended defaults
  kling_client.py        JWT auth, t2v, i2v(+image_tail), polling, retries
  prompts.py             carving prompt templates, materials, stages, negatives
  seeds.py               resolve provided seeds; optional Grok seed generation
  post.py                ffmpeg conform + crossfade stitch + audio
  pipeline.py            orchestration + result manifest + batch
  logging_setup.py       clean console/file logging
jobs/*.json              one file per video; example: wolf_watermelon.json
plan_seeds.py            reference-video -> seed plan (wrapped by `carve.py plan`)
```

## 7. Ready-to-use prompt templates

`carvegen/prompts.py` → `TEMPLATES` has full single-segment carves you can drop
into a segment's `prompt_override`:
- `wolf_watermelon` — snarling gray wolf in a watermelon.
- `lion_wood` — roaring lion from a wood block.
- `rose_watermelon` — blooming rose in a watermelon.

Per-subject detail hints live in `SUBJECT_FEATURES` (wolf, lion, eagle, dragon,
rose, skull) and fill the `{features}` slot automatically — add your own there.

## 8. Verify / caveats

- Auth uses the single API key from https://kling.ai/dev as a Bearer token
  (the current scheme; legacy AccessKey/SecretKey JWT still supported as a
  fallback). Base URL defaults to the global `https://api-singapore.klingai.com`.
- The Kling contract here was confirmed against Kling's docs + community
  references (2026-07); the official docs gateway blocks automated fetches, so
  **re-check endpoint/param names in your Kling console** if a call 4xxs
  (`model_name` values especially change between releases).
- Video URLs from Kling expire quickly — `pipeline.py` downloads immediately.
- Each Kling generation is billed; use `--dry-run` to vet prompts first and
  `--skip-existing` to avoid regenerating good segments.
