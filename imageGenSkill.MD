# imageGenSkill — Carving Video Pipeline

> **START HERE if you are picking this up:** jump to **▶▶ V8 RUNBOOK**. It has
> the spend rules, exactly which 10 generations to run, what is already fixed
> and must NOT be regenerated, and the definition of done. The sections above
> it are history: this file grew chronologically (Kling → Grok → Hailuo hybrid
> → Veo), and the early guidance was superseded, sometimes reversed. Where two
> sections disagree, the later one measured something.


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

0. **Pick the pipeline first.**
   - **Single clip** (steps below) — one 10s carve, one generation, ~95s. Good
     for a quick post or a look test.
   - **Independent-shot Montage, v3** (see "The v3 Montage" section) — when the
     user wants to *match a reference reel*. Costs ~1 master + ~4 edits + ~8
     video generations, but it is the only thing that reproduces the cut-heavy
     feel of real carving accounts. If the user supplies a reference and says
     "make it like this", **go straight there**. (The older Chained Montage
     section below is kept for its measurements; its chaining idea is
     superseded.)
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

---

# The Chained Montage pipeline (match a reference reel) — SUPERSEDED

> **Status 2026-07-27:** the *measurements* in this section (cut list, rhythm,
> phase 0/1 planning) still drive everything, but the chain itself — feeding
> each clip's tail frame to the next generation — is superseded by the v3
> montage below. The 2026-07-26 chained run failed: red flesh bled forward
> through every link (measured 1.9x the reference's saturation) and exposure/
> scale drift compounded, because in a chain one bad link poisons everything
> downstream. `chain_carve.py` still runs it if ever needed.

Use this when the goal is **"make it look like that video"** rather than "make a
carving clip." It takes any reference reel + any subject/material and produces a
cut-for-cut equivalent.

## Why this exists

The reference that started this (`@carve__reveal`, eagle in a watermelon) was
analysed frame-by-frame on 2026-07-25. Two findings drive everything below:

1. **It is not one continuous take.** Scene detection found **8 hard cuts in
   11.4s** (at 1.63, 2.47, 2.72, 3.38, 5.22, 7.05, 8.72, 10.07s) — average shot
   ≈1.3s. Frames 0.1s apart across a cut show a different rind pattern, a
   different zoom, and a knife that teleports into frame.
2. **It is likely AI-generated too** (corrected 2026-07-27; the first read
   said "real carve"). The eagle's feather layout, beak geometry and eye
   placement being *identical* across discontinuous shots is exactly what a
   master-still pipeline produces — it proves a shared source image, not a
   physical object. Meanwhile the **rind pattern changes between cuts**, which
   a real melon cannot do but per-shot generations from one master do
   constantly. The creator's probable recipe: one master still + per-shot
   generations from crops/edits of it, a physics-strong video model with
   native foley, **brief blade-contact moments** (most removal is implied
   across a cut, not shown), and hard cherry-picking — each cut keeps ~1.3s
   of a longer take, so shipped physics is a selection effect as much as a
   model property.

So a single generation can never match it — we would be asking a model to
improvise, unbroken, a subtractive sculpture a human planned over hours. The
montage IS the technique. Recreate the *edit*, and let each generation be
responsible for only ~1.3 seconds of change.

## The idea in one line

Chain short clips where **each clip's last frame is the next clip's seed**, so
continuity comes from the frames, not from the model's memory — then hard-cut
them on the reference's rhythm.

## Inputs

| Input | Example | Notes |
|---|---|---|
| reference reel | `ScreenRecording_*.MP4` | any carve/transform video; only its *timing* and *stage ladder* are used |
| subject | `"roaring lion head"` | swap freely |
| material | `"watermelon"` \| `"wood"` \| `"soap"` | drives the palette rules |

## Phase 0 — Read the reference (free, no API)

```powershell
$V="C:/path/to/reference.mp4"
# 1. specs
tools/ffprobe.exe -v error -select_streams v:0 `
  -show_entries stream=width,height,r_frame_rate `
  -show_entries format=duration -of default=noprint_wrappers=1 $V

# 2. THE CUT LIST — this is the deliverable of this phase
tools/ffmpeg.exe -i $V -filter:v "select='gt(scene,0.15)',showinfo" -f null - 2>&1 `
  | Select-String "pts_time"
```
Record each `pts_time` as a cut. Shot *i* runs from cut *i-1* to cut *i*; those
durations become your **edit rhythm** — copy them exactly, they are why the
reference feels fast.

Then grab one frame per shot to define the **stage ladder**:
```powershell
tools/ffmpeg.exe -y -ss <shot_midpoint> -i $V -frames:v 1 <proj>/reference_frames/stage_<i>.png
```
(`python carve.py plan <ref.mp4> --project <proj> --count <N>` does even
spacing instead, if the cuts are regular.)

## Phase 1 — Write the stage ladder

Turn the N reference frames into N one-line descriptions of **what is newly
carved in that shot**, re-targeted to your subject. Each line is a *delta*, not
a full description. Example for a wolf, 8 shots:

| # | dur | stage delta |
|---|---|---|
| 1 | 1.6s | intact melon, design drawn in black outline, knife touches the rind |
| 2 | 0.8s | first shallow score along the outline, one curl of rind lifts |
| 3 | 0.9s | ears and skull outline cut in, pale rind showing at the edges |
| 4 | 1.8s | brow and eye sockets deepened, eyes take shape |
| 5 | 1.8s | muzzle and snout carved into relief, fur tufts etched around cheeks |
| 6 | 1.7s | mouth opened to red flesh, fangs cut from pale rind |
| 7 | 1.3s | fine fur detail passes, shavings piling below |
| 8 | 1.3s | hero reveal — wiped clean, fully carved, slow settle |

Rules that make or break the ladder:
- **One stage per shot.** If a delta is big enough to need two sentences, split it.
- **Monotonic.** Never un-carve; every stage strictly adds material removal.
- **The last stage is the only one allowed completion language.**

## Phase 2 — Seed the before-frame

Generate `seed_start` per the **Seeds** section above (subject drawn in fine
black outline on the intact material, nothing carved). Eyeball it before
spending on video — every downstream clip inherits its framing, lighting and
palette.

## Phase 3 — The chain loop

For `i = 1..N`:

1. **Seed:** `i == 1` → `seed_start`; otherwise the tail frame of clip `i-1`.
2. **Prompt:** base carve prompt + *only* stage `i`'s delta, plus the bound
   `"advance the carving only this far; most of the design is still un-carved"`.
   For `i == N` swap the bound for the completion language.
3. **Generate** 5s (generate longer than you need — you will trim to ~1.3s and
   want a choice of moments):
   ```powershell
   & $PY generate_shots.py --shots <proj>/shots.json --shot 0<i>_stage
   ```
4. **Extract the tail frame** as the next seed:
   ```powershell
   tools/ffmpeg.exe -y -sseof -0.25 -i <proj>/media/0<i>_stage.mp4 `
     -update 1 -q:v 2 <proj>/seeds/seed_0<i+1>.png
   ```

> **Gotcha (measured):** `-sseof -0.04` writes **no file at all** — the demuxer
> cannot seek that close to EOF and exits 0 having produced nothing. Use
> `-sseof -0.25`. It also dodges the motion blur that usually smears the final
> frames, which would otherwise poison the next seed.

> **Gotcha (measured):** a clip prompted with completion language *finishes the
> whole carve*, leaving the chain nowhere to go. Today's wolf clip ended fully
> sculpted at 10s. Bound every link but the last.

## Phase 4 — Trim to the reference rhythm

Each 5s clip contributes only its best ~1.3s. Scrub for the window where the
blade is actually in contact and material is moving:
```powershell
tools/ffmpeg.exe -y -ss <best_start> -t <shot_dur_i> -i <proj>/media/0<i>_stage.mp4 `
  -c:v libx264 -crf 16 -preset slow -c:a aac <proj>/cut/0<i>.mp4
```

## Phase 5 — Stitch

Hard cuts, matching the reference. `build_reel.py` handles conform + audio;
set the crossfade to 0 (or 0.08 to take the edge off without reading as a
dissolve — a real montage cuts, it does not fade):
```powershell
& $PY build_reel.py --shots <proj>/shots.json
```
Keep each clip's native foley (`build_reel.py` crossfades shot audio in sync
automatically); add a music bed only at the end.

## Phase 6 — QC checklist

Run these before calling it done:
- [ ] **Monotonic carve** — step through the cut points; the subject never
      un-carves or regains rind.
- [ ] **Palette held** — still the material's own colors (green/white/red), not
      a grey animal.
- [ ] **Exposure drift** — chained generations creep in brightness/warmth. Check
      shot 1 against shot N; correct with a `colorbalance`/`eq` pass.
- [ ] **Scale drift** — the subject tends to grow or drift off-center. Normalize
      with a per-shot crop/zoom before stitching.
- [ ] **Hand/knife continuity** — hands change between links. Hard cuts hide
      most of it; if a cut is jarring, trim to a window where hands are out.
- [ ] **Rhythm** — total duration and cut count within ~10% of the reference.

## Cost & time

N ≈ 8 shots → 8 Grok generations at 1080p ≈ 95s each ≈ **13 minutes of
generation**, plus trimming. Re-rolling one bad link costs one generation, not
the whole reel — the chain's main practical virtue.

## Honest expectations

This gets the *structure* right: coherent subject, visible progression, the
reference's cutting rhythm. It will still read as AI on close inspection —
blade-in-rind contact and shavings obeying gravity consistently are where these
models give themselves away, and no prompt fixes that. If you need it
indistinguishable, carve a real melon and film it; the edit recipe above applies
unchanged to real footage.

# The v3 Montage — independent shots from an EDITED ladder

This is the current pipeline: `make_ladder.py` (seeds) + `montage_carve.py`
(video + stitch). It exists because both 2026-07-26 runs failed in ways that
were diagnosed frame-by-frame on 2026-07-27:

- **Chained run** (`chain_carve.py`): red flesh bled across the whole subject
  and grew link over link; exposure and scale drifted. A chain lets one bad
  link poison every later one.
- **Montage run** (`montage_carve.py` + the old t2i ladder): the architecture
  worked — the cuts, rhythm and macro texture were right — but the reel showed
  **no carving happening**, which defeats the whole genre. Root cause was the
  ladder itself: every rung was generated with fresh text-to-image, and Grok
  t2i rendered nearly every rung as a *finished* carve no matter how loudly
  the prompt said "nothing carved yet" (the doc already predicted t2i can't do
  progressive stages — the ladder tried anyway). Worse, two macro rungs
  (`ladder_03_macro_eye`, `ladder_06_macro_mouth`) came back as a **photoreal
  living wolf**, and the video model faithfully animated a real animal head
  sticking out of a melon for shot 5.

## What the reference actually shows (re-read 2026-07-27)

Frame-stripping the `@carve__reveal` eagle again, with fresh eyes:

1. **There is no uncarved-melon phase at all.** Even the opening wide shows
   the rind covered edge-to-edge in carved leaf/feather pattern; the eagle
   emerges from that texture. So "show the carving" does NOT require a full
   outline→finished arc.
2. What sells *carving-in-progress* is that **every macro shot shows the blade
   actually removing material** — and the peak moment is the **mouth
   excavation**: the knife physically pulls strands of red pulp out of the
   open beak. One big irreversible reveal mid-reel, debris everywhere.
3. The all-over background pattern is also why the reference reads as carved
   at wide scale. Our wolf master had smooth striped rind around the subject,
   which reads as a **printed decal**, not a carving.

## The method

**Step 1 — one master still, curated hard.** The finished wide hero. Everything
else derives from it, so spend takes here (`--master-gen 4`, pick by eye).
Requirements baked into `make_ladder.py`'s `MASTER_PROMPT`: melon-palette
subject, carved decorative pattern covering ALL visible rind (no smooth rind in
frame), red only inside the mouth, and an explicit **"carved watermelon
SCULPTURE, not a living animal, no real fur"** guard.

**Step 2 — build the ladder by EDITING, and mind the DIRECTION.** Editing
keeps composition, lighting and palette identical and only changes what you
name — the constraint t2i kept breaking. But *which way* you edit decides
whether the ladder works at all:

> **An edit model cannot un-carve.** Asking it to regress a finished carving
> to a half-carved state fails. Measured twice — v4's four regressed rungs
> bunched at the finished end, and v5's first attempt (rebuilt on
> `gemini-3-pro-image`) came back **non-monotonic**: mean abs diff from master
> A 22.23 / B 13.82 / C 13.09 / **D 19.42** / E 5.31, with D scoring further
> from the master than B or C.

So: **regress only the two edits that are easy backwards** — strip everything
to line-art (`stage_A_outline`), and close the mouth (`stage_E_closed_mouth`)
— then build the middle rungs **forward from the outline**, adding one carved
region at a time. Additive edits are what these models are good at, and every
rung still descends from the one master so the subject never drifts.
`make_ladder.py` encodes this as a `source` per rung:

```
master ──regress──► stage_A_outline ──add ears──► stage_B_first_cuts
       ──regress──► stage_E_closed_mouth              │
                                                       ├─add brow+eyes─► stage_C_upper_face
                                                       └─add muzzle───► stage_D_muzzle
```
Carved area then steps roughly evenly: 0 / 15 / 40 / 70 / 90 / 100 %.

> **QC by eye, not by metric.** Mean-abs-diff from the master is a *misleading*
> proxy here: the uncarved decorative border dominates the pixel count, so the
> correct forward-built rungs score 21.9 → 26.3 (apparently moving *away* from
> the master) right up until the border is carved at rung E. The tile-and-look
> pass is authoritative; use the number only to catch gross non-monotonicity.

**Step 3 — macro rungs are CROPS of a PARTIAL rung, never the master**
(`--crop name:x,y,w,h`, fractional). Free, identity-perfect, palette-perfect.
Cropping the *master* was the v4 mistake: every mid-reel close-up then showed
a finished carving being poked at, which is half of why the reel read as
"already done". Crop `stage_B`/`stage_C`/`stage_D` instead — those frames
contain the carved/drawn boundary, which is the single most convincing
"carving in progress" texture available. Upscale via Higgsfield
`upscale_image` if a crop looks soft.

**Step 4 — animate each rung independently** (`montage_carve.py`, unchanged),
with two prompt upgrades:
- every shot's prompt names a **concrete, visible removal act with debris**
  ("the blade lifts a strip of rind which curls and falls, chips scatter") —
  "a tiny sliver curls off" reads as poking, not carving;
- every shot's prompt repeats the **not-a-living-animal guard** ("the carving
  never moves, blinks or breathes; only the knife and hands move").

**Step 5 — every WIDE shot is a first→last-frame interpolation between
adjacent rungs.** Grok's video API has no end-frame parameter; use a
start+end-frame model on Higgsfield. Head-to-head on the D→master mouth
excavation (2026-07-27): **Minimax Hailuo, `variant: "minimax"`, won** —
1080p, hand on the knife, blade working inside the mouth with pulp on it —
over `seedance_2_0_mini` (good but 720p) and bounded Grok i2v (floating
knife, "tofu block" extraction). Measured constraints:
- `seedance_2_0` std and `kling3_0` end-frame are **plan-gated** (403); mini
  isn't but caps at 720p.
- Hailuo `minimax-2.3` **rejects `end_image`** — only the plain `"minimax"`
  variant takes it; `resolution: "1080"`, ~2 concurrent jobs (429 above).
- Hailuo follows the SEED's aspect (3:4 in → 1080x1440 out): center-crop to
  9:16 (`crop=810:1440:135:0`) before stitching.
- If the MCP replies with a `preset_recommendation` notice instead of a job,
  retry with `declined_preset_id`.
Chain the pairs A→B, B→C, C→D, D→master so the whole progression happens on
camera; `trim: "tail"` lands each cut on its end rung — the very image the
next shot is seeded from. Grok i2v remains the pick for the single-seed macro
shots (crops have no end frame) and the hero.

**Step 5b — audio.** Hailuo transition clips are silent; Grok clips carry
real knife-on-melon foley. Don't ship half-silent cuts: concat the Grok
shots' audio into a bed (`volume=0.65`), `amix` it under the stitched reel,
`alimiter` at 0.9. (Higgsfield `generate_audio` is speech-only — no SFX.)

**Step 6 — trim + stitch on the reference rhythm** exactly as before
(hard cuts, `montage_carve.py` handles conform/concat).

**QC gate that would have saved both runs: eyeball EVERY ladder rung before
spending on video.** A rung that looks finished, painted, or alive WILL
produce that exact failure in motion. Then run the Phase 6 checklist above.

# Which path do I use?

Two live paths. **Neither replaces the other** — the Hailuo+Grok hybrid above
is still the one that runs without a Google balance, and its ladder/rhythm
rules are shared by both.

| | Hybrid (Hailuo + Grok) | Veo 3.1 (`veo_carve.py`) |
|---|---|---|
| billing | Higgsfield plan + xAI key | Google prepay (`ai.studio`) |
| progression | Hailuo `end_image` | `last_frame` |
| audio | Grok shots only, bed mixed under | every shot, native |
| aspect | Hailuo 3:4 → crop | native 9:16 1080p |
| clip length | 6s / 5s | 8s (forced with `last_frame`) |
| shots per reel | 8 short | 6–8, longer windows |
| use when | no Google credits, or you want 1.3s cuts | best physics + foley, matches the reference's likely toolchain |

The **ladder is shared**: `make_ladder.py` builds it once and either path
consumes the same rungs and crops.

## Models available (probed 2026-07-27)

- **Google key** — video: `veo-3.1-generate-preview`,
  `veo-3.1-fast-generate-preview`, `veo-3.1-lite-generate-preview`. Images:
  `gemini-3-pro-image`, `gemini-3.1-flash-image` (+ lite / preview),
  `gemini-2.5-flash-image`, `imagen-4.0-generate-001` (+ ultra / fast).
  `gemini-3-pro-image` is now the **default ladder engine** — it holds
  "change only this region" far better than the xAI edit endpoint.
- **Higgsfield** — `minimax_hailuo` (`variant: "minimax"` for `end_image`),
  `seedance_2_0_mini`, `kling3_0_turbo`. `seedance_2_0` std and `kling3_0`
  are plan-gated (403).
- **xAI** — `grok-imagine-video-1.5` (1080p i2v + foley),
  `grok-imagine-image-quality` (edits, `--engine grok`).

# The Veo 3.1 path (`veo_carve.py`) — one model instead of two

Added 2026-07-27 once a Google key was available. Veo 3.1 is the only model
reachable from this machine that does **both** jobs the montage needs, which
is what the Hailuo+Grok split exists to work around:

| Need | Hailuo | Grok | Veo 3.1 |
|---|---|---|---|
| first+last frame (guaranteed progression) | yes | **no** | yes |
| native audio / foley | **no** | yes | yes |
| 9:16 1080p without cropping | **no** (3:4 in→out) | yes | yes |
| clip length | 6s | 5s | **8s** |

It is also the family most likely behind the reference reel (the viral
AI-carving/ASMR genre runs on Veo 3.x; its edge is contact physics plus
synced foley).

Measured constraints (2026-07-27):
- Models: `veo-3.1-generate-preview`, `-fast-`, `-lite-`. All three are
  visible to a valid key via `models.list()`.
- **`last_frame` requires `duration_seconds=8`.** 4s → `INVALID_ARGUMENT`.
  1080p also requires 8s.
- Needs `google-genai` >= 2.x, else `ValueError: last_frame parameter is not
  supported in Gemini API`. Installed 2.14.0 here.
- **Two different 429s — read the message before acting.**
  - `"Your prepayment credits are depleted"` = **out of money**. Top up at
    https://ai.studio/projects.
  - `"You exceeded your current quota... check your plan and billing"` (with a
    rate-limits link) = **per-model daily quota**, nothing to do with money.
    Measured 2026-07-27: `veo-3.1-generate-preview` blocked after ~11
    generations while `veo-3.1-fast-generate-preview` and
    `gemini-3-pro-image` still accepted work — separate buckets. It cleared
    at the date rollover. Diagnose by probing several models: if any paid
    model works, it is not a billing problem.
- **Transient 429/503 are common.** `veo_carve.py` retries with backoff
  (30/60/120/240s) and continues to the next shot on hard failure. Without
  that one blip aborts a whole reel mid-run.
- **`veo-3.1-fast` follows constraints noticeably worse.** On the same seeds
  it rendered duplicate knives (two blades, two hands) in two shots and raced
  past the specified stage into a finished red-mouthed wolf. Standard Veo on
  identical seeds produced single-knife, correctly-staged takes. Use fast for
  probes and quota overflow; re-roll anything that matters on standard.
- Supports `negative_prompt` (unlike the xAI path) — use it for the
  living-animal guard rather than burning prompt length on it.

Run it exactly like the montage job, with `seed_end` added to any shot that
should interpolate:
```powershell
& $PY veo_carve.py --job jobs/wolf_montage_v5.json --dry-run
& $PY veo_carve.py --job jobs/wolf_montage_v5.json --shot 06_mouth
```
Shots without `seed_end` fall back to single-seed image-to-video. Because
clips are 8s (vs Hailuo's 6s / Grok's 5s), a Veo reel wants **fewer, longer
shots** than the 8-slot ladder above — re-plan the rhythm rather than
trimming 8s down to 0.9s.

## v4 post-mortem (2026-07-27) — read before building v5

The v4 reel fixed the palette and the bas-relief profile, but the user's
review found the *pacing* broken, and the numbers back it. Mean abs pixel
difference of each rung from the finished master:

| rung | diff from master | gained vs previous |
|---|---|---|
| A outline | 21.97 | — |
| B first score | 20.61 | **1.36** |
| C half carved | 14.63 | 5.98 |
| D no flesh | 7.78 | 6.85 |
| master | 0 | 7.78 |

1. **Shot 1 spends 1.6s achieving ~nothing** (A→B moves 1.36 of 22) and what
   it *does* carve is the decorative oval border, not the wolf. The opening
   second should be the knife biting into the subject.
2. **Shot 2 (0.9s) carries the entire un-carved → carved transformation**,
   because `trim: "tail"` lands it on rung C — which already reads as a
   finished wolf. Hence "90% carved by the first second." Everything after is
   detail work on a done carving.
3. **Fix:** more rungs with even spacing (B→C is one perceptual leap and needs
   2–3 intermediate rungs), the big transformations given the LONG slots, and
   trim windows taken from the middle of a clip (carving in progress) rather
   than the tail (carving finished). Seconds 1–5 of v4 were rated good — keep
   that macro texture.
4. **The cloth-wipe hero shot was never requested.** It came from the original
   stage ladder in this file and propagated through every job file since. The
   reference does not wipe. Drop it; end on the carve itself.

## v5 — built and ready to generate (`jobs/wolf_montage_v5.json`)

Ladder rebuilt forward on `gemini-3-pro-image` and QC'd; crops taken from the
partial rungs; job written for the Veo path. Eight shots / 12.8s, slots
1.0–2.4s (mean 1.6s vs the reference's 1.3s):

| # | shot | kind | slot |
|---|---|---|---|
| 1 | first cuts on the EARS | A→B interpolate | 1.8s |
| 2 | ear macro (carved/drawn boundary) | crop i2v | 1.0s |
| 3 | brow + eyes open up | B→C interpolate | 1.8s |
| 4 | eye macro | crop i2v | 1.0s |
| 5 | muzzle + cheeks | C→D interpolate | 1.8s |
| 6 | decorative border | D→E interpolate | 1.6s |
| 7 | **mouth excavation** | E→master interpolate | 2.4s |
| 8 | hero hold (no wipe) | master i2v | 1.4s |

Five of eight shots advance the carve; the wolf is not fully carved until
shot 6. Run:
```powershell
& $PY veo_carve.py --job jobs/wolf_montage_v5.json
# QC, then copy media/veo_<name>.mp4 -> media/m_<name>.mp4
& $PY montage_carve.py --job jobs/wolf_montage_v5.json --stitch-only
```
`--stitch-only` is mandatory — without it `montage_carve` regenerates the
shots on Grok. Veo clips are 8s and carry their own foley, so the trim
offsets in the job are first guesses: re-scrub them after the first QC pass,
and no foley bed is needed this time.

# ▶▶ V8 RUNBOOK — execute this when quota lifts

**Hard limits: 2 requests/minute, 10 requests/day.** Sequential generation
runs ~1 per 90-120s, safely under the RPM ceiling — never parallelise.
A 429 now aborts the whole run by design (see `QuotaExhausted`): it cannot
distinguish a daily limit from a project safety clamp, so it stops and tells
you to check the Cloud Console rather than guessing a reset time.

## Spend discipline (these rules exist because ~$200 went on a 12s reel)

1. **Never call a paid API to check whether the paid API is available.** Every
   "quota probe" submitted a real 8s 1080p generation. Infer state from the
   last error, or ask.
2. **Price it before spending it.** State the generation count and get a go
   for anything beyond a single clip.
3. **Exhaust free fixes first.** Both of the montage's worst-looking moments
   ("half the wolf vanishes", "the wolf changes design") were TRIM WINDOW
   errors on clips we already owned. Free. A 22-generation rebuild was
   proposed before that was discovered.
4. **Draft cheap, finish expensive.** Test prompt changes on fast/720p.
5. **Regenerate the broken shot, never the reel.**
6. **We own 72s of Veo footage and use ~12s.** Before generating, ask whether
   an unused window of an existing clip already does the job.

## What is already fixed (do NOT regenerate these)

| shot | type | state |
|---|---|---|
| 02_ear_macro, 04_eye_macro | i2v | good |
| 05_midface | i2v (v8) | good — replaced the one-sweep shot, validated |
| 06_nose_macro | i2v | good — wider crop + cherry-picked take1 |
| 08_mouth | E→master interp | good — the ONE interpolation that works |
| 09_hero | i2v | acceptable |

Seeds, crops and the forward-built ladder are all done and QC'd. Aspect is
native 9:16 throughout, so no letterboxing.

## The 10 generations, in priority order

The goal is to eliminate the **three unintended in-shot cuts** by converting
every remaining interpolation except the mouth into bounded i2v. Job:
`jobs/wolf_montage_v8.json` (already written, 8/9 i2v).

| # | shot | seed | takes | why |
|---|---|---|---|---|
| 1 | `07_ruff` | `stage_D_muzzle` | 3 | the only definitively broken shot — design drift swaps the wolf at a cut |
| 2 | `01_open` | `stage_A_outline` | 3 | opening carries retention; currently the risky interp type |
| 3 | `03_ears` | `stage_B_first_cuts` | 2 | acceptable today but still an interpolation |
| — | reserve | — | 2 | re-roll whatever QC rejects |

```powershell
& $PY veo_carve.py --job jobs/wolf_montage_v8.json --shot 07_ruff --takes 3
& $PY veo_carve.py --job jobs/wolf_montage_v8.json --rank --shot 07_ruff
& $PY veo_carve.py --job jobs/wolf_montage_v8.json --shot 07_ruff --promote 2
```
Rank sorts by **drift** (distance from seed at the end) — validated as the
metric that separates known-good from known-bad 2:1. Compare takes only
within one shot; drift is not comparable across shots.

## Port these from the Grok/hybrid reel (measured 2026-07-29)

The 07-27 hybrid reel (`wolf_watermelon_montage_20260727_110839_post.mp4`)
looks better than the Veo work in seconds 3-8, and it is worth knowing
exactly why. Measured, not guessed:

| property | GROK hybrid | ours (Veo) | portable? |
|---|---|---|---|
| luminance separation | 93 / 135 | 116 / 152 | **ours already better** |
| contrast (std) | 51 / 60 | 58 / 72 | **ours already better** |
| **saturation** | 44 / 40 | 39 / **26** | **YES — grade it** |
| **framing** | carving fills ~90% of frame | ~55%, grey + hands | **YES — punch in** |
| per-tuft fur depth gradient | green base -> cream tip | flatter bands | no — seed property |
| three-quarter camera angle | yes | front-on, symmetric | no — seed property |

**The big one is FRAMING, not colour.** Our wides waste ~40% of the frame on
background and hands. `crop=iw/1.45` centred, rescaled, gives the carving the same
presence as the reference — verified side by side; z=1.60 starts clipping the
ornate border, z=1.15 still looks small. Apply per shot:

```
crop=iw/1.45:ih/1.45:(iw-iw/1.45)/2:(ih-ih/1.45)/2,
eq=saturation=1.45,unsharp=5:5:0.5,scale=1080:1920
```

The two seed-level properties (fur depth gradient, three-quarter angle) are
NOT portable without regenerating the master and the whole ladder, which
would invalidate every existing clip. Do not chase them — the framing and
saturation ports recover most of the visible gap for free.

## Assembly (free — this is where the remaining quality is)

1. **Two windows per clip.** Each 8s clip can supply TWO cuts at different
   punch-in levels, placed apart in the timeline. 9 clips -> 12-14 cuts,
   denser than the reference's 8, for zero generations.
2. **Recut, never even slots** — `scratchpad/recut.py`, which prints our
   cut-jump and in-shot figures beside the reference's.
   - punch in on wides (z 1.05-1.30) so consecutive shots share visual mass
   - match CONTENT across a cut, not just scale
   - one 0.35-0.45s flash to absorb the unavoidable wide->macro jump
   - vary rhythm; metronomic alternation reads synthetic
3. **Verify with `scratchpad/metrics_clean.py`** — same method both videos.
   Target: cut mean at/below the reference's 16.5, and **cuts detected == 9**
   (12 today means 3 unintended in-shot jumps remain).
4. Loudness pass to -14 LUFS. Veo clips carry their own foley; no bed needed.

## Definition of done

- [ ] scene detection finds the same number of cuts as shots (no phantom edits)
- [ ] no shot removes a large area in one motion
- [ ] the wolf is the same wolf in every frame of the reel
- [ ] one knife, one hand, everywhere
- [ ] full 1080x1920 frame, no letterbox
- [ ] not fully carved before the final third; no cloth wipe
- [ ] cut discontinuity <= reference; rhythm varied with one flash cut

# v8 (2026-07-28) — DON'T ASK VEO TO TRANSFORM

Every bad moment in v6/v7 was an **interpolation shot covering a large
change**, and no plain image-to-video shot ever failed:

| bad moment | shot | type | what Veo did |
|---|---|---|---|
| second 4 | 05_muzzle | C→D interp | removed half the face in ONE sweep |
| second 8 | 07→08 cut | D→E interp | redesigned the wolf mid-clip, so the cut swapped carvings |
| duplicate knives | 03_upper_face | B→C interp | two blades, raced past its stage |
| second 6 | 06_nose_macro | i2v | bad crop + one unlucky take (not the shot type) |

**So stop asking for transformation.** The ladder rungs already encode the
whole carve; make each shot a *small bounded action at rung X* and let the
progression happen across the CUTS — which is what the reference does
("most removal is implied across a cut"). Keep interpolation only where the
change is small and local: the mouth excavation, the one interp shot that
worked reliably every time.

**Validated 2026-07-28 for one generation** before committing the rest:
`05_midface` — the exact shot that produced the one-sweep removal — was
re-run as i2v from `stage_C_upper_face` with a bounded prompt. Both takes
held the boundary for the full 8s: upper face carved, lower half still drawn,
knife working only the cut edge, shavings accumulating. **No sweep.** The
thesis holds; `jobs/wolf_montage_v8.json` is 8/9 i2v.

## METRICS: what they can and cannot tell you (read before quoting a number)

The pixel-difference metrics in this file are useful for **editing**
decisions and useless for **quality** ones. That distinction cost a public
overclaim, so it is written out here.

**What happened:** I measured in-shot motion at 4.89 for both the reference
and our reel, and concluded "per-shot the model already performs at
reference level, so a better model would not help." Both halves were wrong.

**Why the number was wrong.** That measurement assumed the N largest
inter-frame differences *were* the cuts and excluded them. In our reel some
in-shot spikes (the Veo end-frame snap) are larger than some real cuts, so
it discarded our worst moments and flattered the result. Measuring both
videos the same way — scene-detect cuts in each, exclude a frame either
side — gives:

| | reference | ours (v7) |
|---|---|---|
| in-shot motion | 5.04 | 5.41 |
| in-shot p95 | 11.90 | 14.88 |
| cut discontinuity mean | 16.5 | 29.5 |
| cut discontinuity max | 44.2 | 91.1 |
| **cuts DETECTED** | **8** | **12** |

**Why the inference was wrong.** In-shot motion measures how *much* the
picture changed, not whether the change was *plausible*, and it is computed
on a 96x170 greyscale downscale — which destroys exactly where carving
physics lives (blade contact, shaving edges, undercut shadows). Proof from
our own clips:

| clip | verdict | motion |
|---|---|---|
| v6 `05_muzzle` | BROKEN, half the face in one sweep | 5.34 |
| v8 `05_midface` | good, bounded | 4.38 |
| nose take1 | good, clean curl | 4.42 |
| nose take3 | BAD, smeared mush | 4.96 |

A gap of 0.54 separates a clean carve from visible smearing; 0.96 separates
good from a material-conservation violation. The reference-vs-ours gap was
**0.37** — smaller than both. The metric's resolution is coarser than the
differences that matter, so similarity on it proves nothing.

**Better models DO help — we ran the experiment and then argued against it.**
Identical seeds, identical prompts, `veo-3.1-fast` vs
`veo-3.1-generate-preview`: fast gave duplicate knives and raced past its
stage; standard gave single-knife, correctly-staged takes. Same for stills,
where moving off Grok to `gemini-3-pro-image` was the largest single quality
jump in the project.

**The defensible claims:**
- Cut discontinuity IS measured reliably by these metrics, and ours was ~2x
  the reference's until the recut took it below. That holds.
- **Scene detection finds 12 cuts in our 9-shot reel.** Three "shots"
  contain jumps severe enough that an algorithm reads them as edits — the
  interpolation snap, showing up objectively. That is a real, actionable
  defect and it is what v8 removes.
- What does NOT hold: "the model isn't the bottleneck." The honest version
  is *"I paid for better generations for two days while ignoring a problem
  ffmpeg fixes for free."* Both mattered; only one had a cost.

## Ranking takes: what actually discriminates

Scored against four clips whose quality was already known:

| clip | step | spike | **drift** |
|---|---|---|---|
| 05_muzzle (bad: sweep) | 4.8 | 19.3 | **27.8** |
| 07_border (bad: drift) | 6.1 | 35.2 | **28.0** |
| 08_mouth (good) | 4.2 | 8.8 | **14.0** |
| 04_eye (good i2v) | 5.7 | 18.8 | **10.7** |

- **`drift`** (distance from the seed at the end) separates good from bad 2:1.
  Rank on it.
- **`step`** — predicted to catch the one-sweep removal — **does not
  discriminate at all**; a good clip scored higher than a bad one. Kept in
  the output for information only. (Worth remembering as a case where the
  obvious metric was simply wrong and only checking against known-good and
  known-bad clips revealed it.)
- **Drift is comparable only BETWEEN TAKES OF ONE SHOT.** Absolute values
  depend on the seed's uncarved area and on hands entering frame — a
  perfectly bounded v8 take scored 41.6, higher than a genuinely broken v6
  clip at 27.8. Never threshold across shots.

Workflow: per-shot `"takes": N` in the job (spend where takes actually vary)
→ `--rank` → eyeball the top two → `--promote K`. On its first two uses the
ranking matched visual judgement both times.

# v6 results (2026-07-28) — THE EDIT IS THE BOTTLENECK, NOT THE MODEL

The single most useful measurement of this whole project. Comparing the v6
reel against the reference with identical methodology (15fps luma, mean
absolute inter-frame difference, cut frames excluded from the in-shot figure):

| metric | reference | v6 as-cut | v6 RE-cut |
|---|---|---|---|
| **in-shot motion (mean)** | **5.04** | **7.63** | 8.04 |
| in-shot p95 | 11.85 | ~24 | 21.6 |
| cut jump (mean) | 29.2 | ~78 | **13.2** |
| cut jump (max) | 44.2 | 89 | 61.5 |

**Per-shot, Veo already performs at reference level** — the in-shot means were
identical (4.89 vs 4.89) on the first measurement pass. Spending more on a
bigger model was never going to close the gap. What separated the two reels
was entirely editorial:

1. **Cut discontinuity.** Alternating full-melon wides with extreme macros
   throws away the whole frame at every cut (78 vs the reference's 29).
   Fixing this is free — see the recut recipe below — and took our cuts to
   13.2, *gentler* than the reference's own.
2. **In-shot agitation.** Ours stays ~1.6x busier. Punch-in was suspected but
   tested innocent: dialling zoom back from 1.45 to 1.28 moved the figure only
   8.75 → 8.04. The rest is Veo's character plus the `last_frame` snap.

> **Correction to an earlier claim in this file.** The v3 section says the
> reference's energy comes from "cutting between scales (wide → macro →
> wide)". The measurement says the opposite: the reference's scale changes are
> GENTLER than ours. Don't design a shot plan around that old sentence.

## The recut recipe (free, no generation)

- **Punch in on the wides** (crop `iw/z:ih/z` centred, rescale to 1080x1920,
  z≈1.1–1.3) so consecutive shots share visual mass. Keep z modest: it
  magnifies motion as well as scale.
- **Match content, not just scale, across a cut.** The opening wide→macro jump
  fell from 71 to 62 purely by starting shot 1 later, so pale carved rind is
  already on screen before cutting to an all-pale macro.
- **Hide an unavoidable jump inside a FLASH.** The reference's shot list is
  1.63 / 0.83 / **0.25** / 0.67 / 1.84 / 1.83 / 1.67 / 1.35s — it absorbs its
  own hard cut in a quarter-second. A discontinuity that ends before the eye
  resolves it reads as energy, not error.
- **Vary the rhythm.** A metronomic 1.6/0.9 alternation feels synthetic. Use a
  fast burst early, then longer shots, with the money shot given the most room.

`scratchpad/recut.py` is the parametric builder: edit `PLAN`
(name, start, duration, zoom), run it, and it prints the cut-jump and in-shot
figures next to the reference's so a change is verified, not assumed.

## Macro framing: there is such a thing as too tight

v6 shot 06 (`nose_macro`) is the reel's weakest second. Cropped so tight that
the nose reads as an abstract dark blob with no wolf context, and the blade
appears to smear a pale lump rather than cut it. **A macro still needs one
recognisable landmark plus the carved/drawn boundary** — the eye macro works
because both are in frame. Crop boxes around 0.30–0.38 of the master's width
are the useful range; below that it stops reading as carving.

## v5 results (2026-07-27) — what Veo actually does

All 8 shots generated, no failures. Two findings that change how you plan a
Veo reel:

**1. `last_frame` is a SOFT target, and "landing" is a hard snap.** The
request is correct — payload capture confirms `instances[0]` carries
`prompt`, `image` AND `lastFrame` — but Veo improvises forward through the
clip and then **jump-cuts to the pinned end frame in the final frame or
two**. Shot 03 sat on a red-mouthed finished wolf from 6.5s and snapped back
to the correct half-carved rung only at 7.99s. Four of five transitions
landed (03, 05, 06, 07); shot 01 never landed at all, ending on an invented
red-fanged mouth instead of `stage_B`.

Consequences for the edit:
- **Never trim from the tail of a Veo clip** — the last frames contain a
  visible jump cut. (The opposite of the Hailuo advice above, where tail
  trims were what made junctions continuous.)
- **Take EARLY windows, ~0.8–3.5s.** The start frame is always honoured
  exactly, so the further in you go the more the model has improvised.
- The frame-anchored junction premise does not hold on this path. Continuity
  comes from every shot *starting* on a QC'd rung instead.

**2. Seed aspect ratio must match the requested output.** Veo honours the
seed's framing, so a 3:4 seed with `aspect_ratio: "9:16"` gets
**letterboxed**: every v5 clip came back 1080x1920 containing only
1080x1440 of picture with 240px black bars — a quarter of a Reels frame
wasted. Grok's image model emits 864x1152 (3:4), so any ladder built from a
Grok master has this problem. `veo_carve.py` now warns per shot before
spending (`check_seed_aspect`). Build the master at 9:16 (e.g.
`gemini-3-pro-image`, which takes an aspect ratio) — note the melon's
background is only uniform at the TOP, so padding the rungs programmatically
is not an option; the bottom holds hands and shavings.

> Worth noting how this one was found: it is invisible to code review. The
> source is correct, the API call is correct, and the defect exists only in
> the relationship between a PNG's pixel dimensions and a JSON config field.
> Only frame-strip QC of the output catches this class of bug — which is why
> the QC pass is not optional, and why the check now lives in code.

## Code-review fixes (2026-07-27, pre-v5)

A `/code-review` pass on the branch before the v5 spend confirmed 10 findings;
all are fixed. The ones that change how you drive the pipeline:

- **`--shot NAME` now re-rolls.** In both `montage_carve.py` and
  `veo_carve.py` it used to be a silent no-op when the clip existed (it would
  print `[skip]` and re-stitch the same bad clip). Skip-if-exists now applies
  only to sweep runs, and an unknown shot name is a hard error listing the
  valid names (it used to exit 0 having done nothing).
- **Stitch the Veo reel with `--from-prefix veo_`** instead of hand-copying:
  `montage_carve.py --job ... --stitch-only --from-prefix veo_` copies every
  `veo_<name>.mp4` over `m_<name>.mp4` and hard-errors on any missing source.
  Hand-copying was the default failure mode — `media/` accumulates same-named
  `m_*` clips across versions (v4's `m_08_hero.mp4` was one forgotten copy
  away from silently ending the v5 reel with the deleted cloth wipe).
- **`--stitch-only` no longer requires seed images to exist** — stitching
  never uses them.
- **Veo safety-filter guard:** a completed operation with no video (the RAI
  filter withholding output — likely for gory-sounding flesh/knife prompts)
  used to crash with a raw traceback and abort the remaining shots. Now it
  reports, continues, and lists failed shots at exit.
- **Hard-cut audio loss:** `acrossfade=d=0` is treated by ffmpeg as *unset*
  and eats ~1s of audio per join (an 8-shot reel lost ~7s; foley drifted
  ahead of picture). `build_reel.py` and `carvegen/post.py` now concat when
  crossfade <= 0. (`chain_carve.concat` always had the guard.)
- **`make_ladder.py`:** `--crop NAME:SOURCE:X,Y,W,H` can now crop from a
  partial rung (before, `--crop` always cut the master — the documented v5
  method was unimplementable from the CLI); `--crops-only` skips the paid
  ladder edits; master takes number by max index (curating away a bad take
  no longer makes the next `--master-gen` overwrite a keeper); edge-clamped
  crops re-center instead of squashing the geometry.
- Bare-float `trim` offsets clamp with a warning instead of seeking past EOF;
  `veo_carve.py` honors job/shot `duration` and prints a `[warn]` when
  `last_frame`/1080p forces 8s; `plan_seeds.py` scaffolds now pin
  `grok-imagine-video-1.5` + `"resolution": "1080p"` (the scaffold used to
  ship the 480p trap this doc warns about); `google-genai>=2.0` is in
  requirements.txt and `GOOGLE_API_KEY` in `.env.example`.

Known-but-deferred (displaced by the finding cap): the orphaned Kling stack
(`carvegen/kling_client.py`, `carve.py`, ~900 dead lines still advertised by
CARVEGEN.md) and the fully serialized generation loops (shots submit one at a
time against 600–900s timeouts).

## Still to build

- `montage_carve.py` could grow a `"provider"` field so Hailuo/Grok/Veo shots
  live in one job file instead of being placed by hand.

## Key lessons (carry forward)

- Grok Imagine i2v > Kling for carves; prompt the *completed* transformation —
  **except** inside a montage, where every shot but the last must be bounded
  to one stage.
- Viral carving reels are **montages**, not single takes. Measure the reference's
  cut list before trying to match it.
- **The edit is the bottleneck, not the model.** Measured 2026-07-28: our
  in-shot motion matched the reference exactly while our cut jumps were ~2.7x
  worse. Fix the cut before buying a bigger model.
- **Generate several takes per shot and cherry-pick** (`veo_carve.py --takes
  N`, then `--rank` to sort them by smoothness). This is the cheapest quality
  lever in the whole pipeline and the one most often skipped. Physics quality
  in short-cut montages is substantially a selection effect.
- **Measure, don't assert.** Every claim in this file that turned out wrong
  (the reference being a real carve; its energy coming from big scale jumps;
  "Veo ignored the end frame") was fixed by measurement — payload capture,
  pixel diffs, cropdetect. Frame-strip QC of real output catches what code
  review structurally cannot.
- **Build stage ladders by EDITING one master still, never by fresh t2i** —
  t2i renders finished subjects and will hand you a living animal at macro
  scale. Crops of the master are the best macro seeds. Eyeball every rung
  before generating video.
- **Guard against the subject coming alive** in every image AND video prompt:
  "carved sculpture, not a living animal; the carving never moves or blinks."
- For guaranteed on-camera progression, interpolate between adjacent rungs
  with a start+end-frame model (Seedance 2.0 via Higgsfield); Grok has no
  end-frame parameter.
- Prompt each shot with a concrete removal act + debris; the reference's peak
  is the mouth excavation (knife pulling red pulp strands out).
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
