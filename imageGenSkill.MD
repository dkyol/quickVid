# imageGenSkill — Carving Video Pipeline (Grok Imagine)

Skill for generating viral-style, vertical (9:16) **continuous carving process**
videos: a whole watermelon (or wood block) is progressively carved into a
detailed subject (wolf, animal, object, face) — **outline → peeling → deep
carving → final details** — ending on a clean hero reveal.

Both the seed still and the video run on **Grok Imagine** via the xAI API
(`generate_shots.py`); ffmpeg stitches when a reel needs more than one clip.

> Head-to-head on 2026-07-25 (identical seed, 10s, 9:16): Grok Imagine
> image-to-video carved the **whole** wolf face; Kling (`kling3_0_turbo` on
> Higgsfield) only nicked the muzzle open and left ~85% of the subject a flat
> drawing. **Use Grok.** The old Kling route is documented in CARVEGEN.md as
> legacy.

---

## ▶ Let's get started

When the user says **"let's get started"** (or invokes this skill), run the
pipeline below in order. Ask only for what's missing; use sensible defaults and
keep moving.

1. **Confirm the subject + material.** e.g. subject `"snarling gray wolf head"`,
   material `"watermelon"` (or `"wood"`). Default style: hyperrealistic carving,
   macro process video.
2. **Ask for a reference video and/or seed images (optional but preferred).**
   - Reference video → `python carve.py plan "<reference.mp4>" --project <proj>
     --count 5` extracts stage frames to `<proj>/reference_frames/` so you can
     see the real arc (this planning step still works and costs nothing).
   - Seed images the user supplies → drop in `<proj>/seeds/`.
3. **Get the `seed_start` image** — the **BEFORE** frame: the whole uncarved
   surface with the subject **drawn in outline** on it. See "Seeds" below.
   Generate it with Grok if the user has none. Always eyeball it before
   spending on video.
4. **Write / confirm `<proj>/shots.json`** (schema below). Set
   `"resolution": "1080p"` — omitting it silently gives you 480p.
5. **Verify the key:** `python generate_shots.py --check`.
6. **Generate:** `python generate_shots.py --shots <proj>/shots.json`
   → `<proj>/media/<name>.mp4` (~40s at 480p, ~95s at 1080p).
7. **Review & iterate.** Pull frames with ffmpeg, check the carve/palette,
   tweak the prompt or reseed, re-run one shot with `--shot <name>`. Copy the
   keeper to `<proj>/final/` and deliver.

---

## Environment (this machine)

- Python: `C:\Users\DKYLE\.conda\envs\api\python.exe` (has requests, python-dotenv).
  Run scripts with this interpreter.
- `ffmpeg.exe` / `ffprobe.exe` are in `tools/`.
- Secrets in `.env` (gitignored): `XAI_API_KEY` (seed images **and** video).
- Verify auth any time: `python generate_shots.py --check`.

## Recommended setup (best results)

| Setting | Value | Notes |
|---|---|---|
| `video_model` | `grok-imagine-video-1.5` | required for 1080p; deeper, more sculptural relief than the base model. |
| `resolution` | `1080p` | → 1072x1904. **Default when omitted is 480p (848x480)** — always set it. |
| `aspect_ratio` | `9:16` | Reels/TikTok. Set at generation; never crop landscape → vertical. |
| `duration` | `10` | up to 15s supported. |
| `type` | `image_to_video` | the seed becomes the literal first frame — this is what makes the carve read as real. |

Verified API enums (probed 2026-07-25, `POST /v1/videos/generations`):
- `resolution`: `480p` | `720p` | `1080p`
- `size`: `848x480` | `1696x960` | `1280x720` | `1920x1080`
- `1080p` is **rejected on `grok-imagine-video`** ("not available for this
  model") — it needs `grok-imagine-video-1.5`.

## shots.json schema

```jsonc
{
  "project": "wolf_watermelon",
  "video_model": "grok-imagine-video-1.5",
  "aspect_ratio": "9:16",
  "resolution": "1080p",          // top-level default; per-shot overrides
  "shots": [
    { "name": "01_carve_grok",
      "type": "image_to_video",   // image | video | image_to_video
      "seed": "seed_start_grok",  // name in seeds/ or media/, path, or URL
      "duration": 10,
      "prompt": "..." }
  ]
}
```
Run one shot only with `--shot 01_carve_grok`. Image shots accept `--n` for
multiple takes (rename the keeper to drop the `_takeN` suffix); video shots
always produce one take.

## Seeds

The single biggest quality lever. Rules that were learned the hard way:

- **Render the subject in the MATERIAL's own colors, not the subject's.** A
  watermelon wolf is green-and-white-and-red, NOT grey: dark green rind for
  outlines and the **nose (dark green, not black)**, pale carved rind as the
  fur with the melon's green striations as shading, red flesh only in the open
  mouth/inner ears. Wood = grain + pale fresh-cut facets + shavings, no paint.
- **`seed_start` must be the BEFORE state** — the subject only *drawn in fine
  black outline* on the smooth uncarved surface, nothing carved yet. This is
  what forces the video to show material coming off.
- Prefer ONE outline seed + let the video model carve. Text-to-image can't
  reliably produce a *progressive* multi-stage set (it renders finished
  subjects), so don't try to hand it 5 in-between stages.

### Generating seeds with Grok

Use `carvegen/seeds.py:generate_seed()` or a short script with `XAI_API_KEY`
(model `grok-imagine-image`). Outline prompt that reliably yields a true
before-frame:

> "Extreme close-up vertical phone photo, warm natural light, dark wooden
> background. Two hands hold a whole vivid green watermelon. A `<subject>` is
> DRAWN on the green rind in fine black marker outline — flat line-art on the
> smooth uncarved green skin, nothing carved yet, no pale layer, no red flesh.
> A small knife touches the rind. A green watermelon with a drawing on it, not
> a realistic grey animal, not painted."

## Prompting the carve

**Prompt for the finished state, not the activity.** This is what separated the
good take from the bad one: a prompt that merely *describes carving* gets ten
seconds of tentative poking. Demand completion explicitly —

> "The carving spreads fast across the whole face — ears, brow, cheeks, muzzle —
> until the **ENTIRE** wolf head is fully carved in deep 3D relief, **no drawing
> left flat**. … Ends on the finished carved wolf watermelon, fully sculpted."

Then the material specifics: curling strips of green rind peeling away and
falling, pale white carved rind beneath as layered fur, dark rind kept as nose
and markings, muzzle opened to red flesh with pale carved fangs, shavings piling
up, juice glistening. Close with framing: vertical macro, hands steady,
photorealistic.

`carvegen/prompts.py` still holds reusable templates (`wolf_watermelon`,
`lion_wood`, `rose_watermelon`) and per-subject detail hints in
`SUBJECT_FEATURES` — good raw material, just paste into a shot's `prompt`.
`python carve.py gen jobs/<proj>.json --dry-run` prints a fully-built prompt for
free if you want the long-form version.

## Key lessons (carry forward)

- Grok Imagine i2v > Kling for carves; prompt the *completed* transformation.
- Seed the before-state; material palette over subject palette; nose = rind color.
- Set `resolution` explicitly — the 480p default is easy to ship by accident.
- `1080p` requires `grok-imagine-video-1.5`; the base model 400s on it.
- Set `aspect_ratio` at generation, never crop landscape → vertical.
- 1080p takes ~95s vs ~40s at 480p; the poll can sit at 94% for a while — not a hang.

## Legacy

`CARVEGEN.md` documents the Kling pipeline (`carve.py`, `carvegen/`). It is kept
for the prompt templates, the reference-video planner (`carve.py plan`), and the
ffmpeg stitcher (`carvegen/post.py`), but its **video client points at the
direct kling.ai/dev API, which is no longer funded** — don't call `carve.py gen`.
`build_reel.py` stitches multi-shot reels from a shots.json.
