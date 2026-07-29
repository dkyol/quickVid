# carvingSkill.MD — carve any subject into any material, streamlined

> This is the **fast path**: a short, generic runbook distilled from
> `imageGenSkill.MD` after a project that took many iterations to get right.
> That file is the full lab notebook — every dead end, every measurement,
> every wrong theory and its correction. Read it if something here breaks
> and you need to know *why* a rule exists. This file exists so the next
> carve doesn't have to relearn those lessons the hard way. **The QC gates
> below are not optional advice — skipping them is what caused the rework
> this file exists to prevent.**

## What this produces

A vertical (9:16) short-form video of a material (watermelon, wood, soap...)
being progressively carved into a subject — a described subject in words
**or a subject given as a reference image** (a logo, a photo, a drawing) —
ending on a clean reveal. Built as an edited montage of short clips, not one
continuous generation (see "Why a montage" below if that seems like
overkill).

## ▶ Let's get started — ask for these before doing anything

When this skill is invoked, get the following from the user before running
any command. Ask only for what's missing; default the rest and keep moving.

1. **Subject — text OR a reference image.** If an image (logo, photo,
   drawing) is supplied, use the `--reference` path throughout Step 1; the
   whole ladder then derives from that image instead of a text description.
   If text, get a specific, visual description (not just "a dog" — "a
   snarling husky head, ears back, mouth open").
2. **Material.** Default `watermelon` if not specified. Other materials
   (wood, soap, pumpkin...) work the same way but change the palette rules
   in Step 1 — confirm what "the material's own colors" means for it before
   writing prompts.
3. **Reference reel (optional).** If the user has a real carving video they
   want to match the pacing/rhythm of, get the file path — it feeds Step 7's
   recut for free. Not required to proceed.
4. **Project name.** Default: derive a short slug from the subject
   (`logo_watermelon`, `husky_wood`, etc.).

Do not start generating anything until subject + material are settled — the
master still in Step 1 is the one input every later step depends on, so
getting it right the first time is worth more than moving fast here.

## Step 0 — environment (once per machine, skip if already set up)

- Python: `C:\Users\DKYLE\.conda\envs\api\python.exe`
- `ffmpeg.exe` / `ffprobe.exe` in `tools/`
- `.env`: `XAI_API_KEY` (seed edits via Grok, rarely needed), `GOOGLE_API_KEY`
  (master + ladder + Veo — this is the one that matters)
- **Verify the key with a live call before anything else, and diff the
  actual string, don't pattern-match on it:**
  ```powershell
  curl "https://generativelanguage.googleapis.com/v1beta/models?key=$env:GOOGLE_API_KEY"
  ```
  200 = good. 401 = the value in `.env` is wrong somehow (a stray trailing
  character from a bad paste is the most likely cause, not a "wrong kind of
  key" — compare it byte-for-byte against what you meant to paste before
  theorizing). 429 with `"monthly spending cap"` in the message = raise it
  at https://ai.studio/spend. 429 with `"exceeded your current quota"` and
  no further detail = ambiguous, could be a daily limit or a project
  clamp — do not spam retries, see `veo_carve.py`'s `QuotaExhausted` handler.
  There is also a **2 requests/minute** rate limit independent of both —
  generate sequentially, never in parallel.

## Step 1 — the master still (the biggest quality lever)

One curated, finished, wide hero shot. Everything else derives from it, so
spend real attention here.

**Text subject:**
```powershell
python make_ladder.py --project <proj> --subject "<subject text>" --master-gen 4
```
**Reference-image subject (a logo, a photo):**
```powershell
python make_ladder.py --project <proj> --reference path\to\logo.png --master-gen 4
```
Both produce `<proj>/seeds/master_take{1..4}.png`. **Eyeball all of them and
pick the best by hand** — rename the keeper to `seeds/master.png`. Reject
any take that:
- is not in the material's own colors (a logo carved in watermelon must be
  green/white/red rind layers, never the logo's actual brand colors — the
  prompt says this, but verify, don't assume);
- looks "alive" or like a painted/printed sticker instead of a carving;
- has smooth, untouched rind anywhere in frame (the whole visible surface
  needs a carved decorative texture, or later macro shots have nothing to
  show);
- is not natively 9:16 — a 3:4 or square master makes every later Veo clip
  **letterboxed** (confirmed black bars, no way to fix after the fact).
  `gemini-3-pro-image` takes `--aspect 9:16` directly; use it.

## Step 2 — build the ladder by EDITING the master, never fresh generation

Fresh text-to-image cannot hold a *partial* carve — it renders finished
subjects no matter how the prompt is worded. Every ladder rung must be an
**edit** of the master (or of another rung), which keeps composition,
lighting and palette locked and only changes what you name.

**The one rule that matters most: direction.**
- An edit model **cannot un-carve** a finished design back to half-carved.
  Asking it to regress the *subject itself* produces drift and sometimes
  non-monotonic results (a "half-carved" rung scoring further from the
  master than an earlier one).
- It CAN regress something **spatially separate** from the subject — like
  stripping a decorative border back to a line drawing, or closing an open
  mouth — because that's closer to "remove this region" than "undo this
  transformation."
- So: build the **early/outline** rung and the **late/near-finished** rungs
  as direct regressions FROM the master (each one edit away from it), then
  build the **middle** rungs FORWARD from the outline by *adding* carved
  area one region at a time. Additive edits are what these models are
  actually good at.
- **Keep every rung as close to the master as the technique allows.**
  Rungs built several edits deep in a forward chain (A→B→C→D...) accumulate
  drift — by the 4th link the subject can look visibly different from the
  master (different proportions, different linework style). If a rung is
  drifting, rebuild it as a direct regression from a *later*,
  master-adjacent rung instead of continuing the forward chain.

`make_ladder.py`'s `LADDER` list encodes this as a `source` per rung — read
it before editing; it's the reference implementation of the direction rule
above, not boilerplate.

```powershell
python make_ladder.py --project <proj> --subject "<subject>" --master <proj>/seeds/master.png
```
Rebuild one rung: add `--only stage_NAME`.

## Step 3 — macro crops (free)

Cut close-up seeds as fractional crops of a **partial** rung — never the
master, and never a fully-finished rung. A crop of the master shows a
finished carving being poked at, which reads as "already done." A crop of a
partial rung shows the carved/uncarved boundary, which is the single most
convincing "carving in progress" texture available.

```powershell
python make_ladder.py --master <proj>/seeds/master.png --crops-only \
    --crop <name>:<source_rung>:X,Y,W,H
```
A macro needs at least one recognizable landmark in frame plus the boundary
— too tight a crop reads as an abstract blob, not a carving.

## Step 4 — MANDATORY: audit the whole ladder before spending on video

Side-by-side every rung, free, before any paid generation:
```powershell
cd <proj>/seeds
../../tools/ffmpeg.exe -y -i stage_A.png -i stage_B.png -i stage_C.png \
  -i stage_D.png -i stage_E.png -i master.png -filter_complex \
  "[0]scale=250:444[a];[1]scale=250:444[b];[2]scale=250:444[c];\
   [3]scale=250:444[d];[4]scale=250:444[e];[5]scale=250:444[f];\
   [a][b][c][d][e][f]hstack=6" -update 1 -frames:v 1 audit.png
```
Check: same subject style, same proportions, same border/texture treatment
across every rung. A rung that looks like a different subject, or has a
border/texture state inconsistent with its neighbors, WILL show as a visible
jump-cut defect once shots are cut together — this is cheap to catch here
and expensive to catch after generating video. Monotonic carve coverage is
necessary but **not sufficient** — a ladder can be perfectly monotonic and
still split into two visually different "families." Fix the drifted rung
before spending, not after.

## Step 5 — generate video (Veo 3.1)

**Ask for a small bounded action per shot, not a transformation.** The
single biggest failure mode across every past run: an interpolation shot
(seed → end-frame) asked to cover a *large* change reliably does something
implausible — removes half the subject in one sweep, redesigns it mid-clip,
or renders duplicate tools/hands. A plain image-to-video shot asked for one
small, concrete, bounded action (with visible debris — "a strip curls off
and falls," not "carving happens") has never failed this way. **Reserve
interpolation for exactly one shot: the single moment where showing the
transformation on-camera actually matters** (e.g., a mouth/cut opening to
reveal the interior) — that's the only place it has held up.

```powershell
python veo_carve.py --job jobs/<name>.json --dry-run          # verify prompts/seeds resolve, free
python veo_carve.py --job jobs/<name>.json --shot <name> --takes 3
python veo_carve.py --job jobs/<name>.json --rank --shot <name>
```
Per shot: `resolution: 1080p` + `last_frame` (interpolation) both force
`duration=8`. Seed aspect must match the job's aspect — mismatch =
letterbox. `negative_prompt` for the "two knives / duplicate hand / living
animal" guards.

## Step 6 — MANDATORY: scrub the ENTIRE clip before promoting a take

**This is the gate that was skipped and cost a redo — do not skip it.**

A bounded i2v shot can look perfectly correct at any two hand-picked
timestamps and still spontaneously finish the *entire* carve — including
parts owned by a later shot — somewhere in the back half of its 8 seconds,
with no warning in the prompt or the seed. Checking frames at, say, 3s and
5s is not enough; the runaway can start at 5.5s and be finished by 6.5s.

```powershell
ffmpeg.exe -y -i veo_<name>.mp4 -vf "fps=1,scale=180:320,tile=8x1" -update 1 -frames:v 1 scrub.png
```
One command, one image, all 8 seconds. Do this for **every take before
ranking, and again for whichever take you're about to promote** — even the
top-ranked one.

**The `--rank` drift score is a shortlist tool, not a verdict.** It has
picked the wrong take before — the lowest-drift take was the one that
blew up late, while two higher-drift takes both stayed correctly bounded
the whole clip. Always eyeball the full scrub of the actual top pick before
`--promote`.

Also watch for two more failure modes, both found the same way — full scrub,
not spot-check:

- **A detail vanishing under the tool and not coming back by the end of the
  trim window, while the NEXT shot shows it intact.** Not a within-clip
  glitch — the hand/tool simply covers or removes a feature (a nose, a
  logo element) for the rest of that clip's usable range. Check the exact
  frame the cut lands ON against the exact frame the next shot STARTS on;
  if the feature is missing in one and present in the other, the cut reads
  as it magically reappearing. Fix by moving the trim window later (or
  choosing a different take) until the tool has cleared the feature before
  the cut point.
- **A "bounded" take that never runs away can still carve in the WRONG
  place.** Staying inside the prompt's scope (small action, no full reveal)
  is necessary but not sufficient — the model can also simply miss the
  seed's actual linework and carve an unrelated mark elsewhere on the
  surface, especially if the seed's outline is low-contrast (thin dark
  lines on dark material read poorly even to a human at a glance). Check
  the full scrub against the SEED image side by side: does the cut sit on
  the drawn line, not just somewhere plausible-looking? If the outline is
  too faint to trace reliably across takes, fix the seed (bolder/higher-
  contrast outline) rather than re-rolling takes against the same seed.

## Step 7 — assembly: never stitch on even slots

A naive equal-length stitch reads as synthetic and wastes the technique's
own strengths. Free, no regeneration needed:

- **Vary the shot durations.** A fast burst early, longer shots for the
  money moment, one deliberately tiny (~0.3-0.5s) "flash" cut for an
  unavoidable wide→macro jump — a discontinuity that resolves before the
  eye catches it reads as energy, not error.
- **Punch in on wide shots** (crop to zoom ~1.3-1.45, centered, rescale to
  output size) so consecutive shots share more visual mass across a cut;
  macros are usually already tight enough.
- **Match content across a cut, not just scale** — end a wide shot on a
  frame where some of the next macro's texture is already visible, rather
  than cutting from bare surface straight to a fully-textured close-up.
- **Never trust the tail of a `last_frame` interpolation clip** — Veo
  improvises through the middle and snaps hard to the pinned end frame in
  the last frame or two, which looks like a jump cut if you trim into it.
  Take early-to-mid windows instead; continuity comes from every shot
  *starting* on a QC'd rung, not from chaining tail frames.
- **Measure it.** Scene-detect the stitched output
  (`ffmpeg -filter:v "select='gt(scene,0.15)',showinfo"`) and compare cut
  count and cut-jump magnitude against a reference reel if you have one.
  More cuts detected than shots means an in-shot jump (usually an
  interpolation snap) is severe enough to read as its own edit — fix that
  shot's trim window before shipping.

## Step 8 — final checklist

- [ ] scrubbed every promoted clip full-length, not spot-checked
- [ ] scene-detected cuts == number of shots (no phantom in-shot jumps)
- [ ] the subject is the same subject/style in every shot, no mid-reel drift
- [ ] one tool, one hand, throughout (no duplicates)
- [ ] full frame, no letterboxing
- [ ] not fully finished before the final third; no un-requested wipe/reveal
- [ ] material's own colors only, never the reference image's original colors
- [ ] recut with varied rhythm, not even slots

## Spend discipline

1. Never call a paid API just to check if it's available — infer state from
   the last real error.
2. State the generation count and get a go before spending beyond one clip.
3. Exhaust free fixes first — a bad trim window or even-slot stitch has
   caused more visible defects on this project than an under-powered model
   ever did. Free recut before paid regenerate, always.
4. Regenerate the broken shot, never the whole reel.
5. Generate multiple takes only where takes actually vary in quality
   (i2v shots with real motion); rank, scrub the full clip, then promote.

## Why a montage, not one continuous generation

No current model can improvise, unbroken, a multi-minute subtractive
sculpture a human would plan over hours — asking for one long continuous
carve gets tentative, shallow motion. Real (and most AI-generated) carving
reels are themselves montages: a master image, per-shot generations from
edits/crops of it, brief tool-contact moments, and hard cuts on a fast
rhythm — most of the actual material removal is *implied across a cut*, not
shown continuously. Recreating that edit structure, not fighting it, is
what makes the genre work.

## Where the detail lives

`imageGenSkill.MD` has the full history: every measurement, every wrong
theory (some corrected in-place, dated), the exact API quirks, the specific
`veo_carve.py`/`make_ladder.py`/recut script internals. Read it when this
file's summary isn't enough to debug something, or when doing something
this file doesn't cover (Hailuo/Grok hybrid path, chained-clip generation,
detailed metric definitions).
