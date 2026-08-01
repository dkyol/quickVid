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

**Pick crop coordinates from a grid overlay on the actual image, not by
guessing fractions freehand — especially near a design with multiple
close-together decorative elements.** A round/curved subject distorts where
content actually lands at a given fractional height, and adjacent decorative
elements (e.g. a small carved "fin" or flourish next to the main border
pattern) are easy to straddle by accident. A crop that captures two different
elements at once gives the video model an ambiguous target: measured on the
Starbucks reel, a border crop that included both the intended leaf-vine
pattern AND an adjacent carved decorative fin produced a take that cut at the
seam between them with an implausible color transition, not cleanly on
either element. Fix:
```powershell
ffmpeg.exe -y -i stage_X.png -vf "drawgrid=w=iw/10:h=ih/10:t=1:c=red@0.7" -update 1 -frames:v 1 grid.png
```
Read exact coordinates for the ONE element you want off the grid, then verify
the resulting crop contains nothing else before using it as a seed — don't
just guess a box and eyeball the result; iterate against the grid.

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

**The 250x444 thumbnail is not enough by itself — open every rung at full
resolution too.** Measured on a Starbucks-medallion carve (2026-07-30): the
hstack audit was eyeballed at thumbnail size and passed, but two rungs
(`stage_C_face`, `stage_D_hair`) had actually drifted to ~100% carved —
matching the master almost exactly, including the border, which the prompt
explicitly said to leave flat — despite looking like a plausible partial
state at thumbnail scale. The defect was invisible until each PNG was opened
individually at native size. **For a forward-chain rung, specifically verify
the region the prompt named "stays flat" actually reads as flat outline art,
not just that the region being added looks right** — that's the direction
most prone to silent drift, because a rung that over-delivers still *looks*
like a finished, good carving in isolation; only comparing it against its own
prompt's constraints catches it.

**Peripheral/framing regions (a border ring, a background pattern) are the
LEAST reliably held flat during an additive edit — even less reliable than
the subject's own features.** The wolf ladder's lesson was "the model can't
un-carve the subject." The Starbucks ladder surfaced a sharper version: even
when a region is never touched by name in a prompt and is *outside* the
subject entirely, an edit model asked to add detail elsewhere will often
"finish" that untouched peripheral region anyway — its training prior toward
a complete, plausible-looking carved watermelon outweighs an instruction to
leave one area alone. Treat any rung with a from-the-master peripheral
element (a border, a background texture) as needing its own explicit
full-resolution check every time, not just once.

**If a forward-chain rung has drifted, don't assume the NEXT link in the
chain is safe just because it "only adds one more region."** On the wolf
ladder, drift accumulated gradually over 3-4 links. On the Starbucks ladder,
one rung (`stage_C_face`) drifted to ~100% after a single additive edit from
a correct `stage_B`. Distance from the master in *edit count* is not a
reliable proxy for distance in *carved percentage* — always check the actual
image, every rung, every time, regardless of how few edits deep it is.

**After fixing ONE defect in a rung, re-check EVERY region the prompt named
— not just the one you were worried about.** A single rung can over-deliver
in multiple, unrelated ways across separate rebuild attempts, and fixing one
doesn't mean the others are fine. Measured on the Starbucks `stage_B_crown_star`
rung: it was rebuilt three times, and each rebuild fixed the one thing being
checked while a DIFFERENT region was silently wrong — first the border carved
early (should have stayed flat), then the crescent background color inverted
(fixed, verified), then — after THAT fix passed its own check — the hair also
turned out fully carved despite the prompt saying it should stay flat, caught
only when a downstream crop of it looked wrong. None of these were caught by
re-auditing just the region that had failed before; each needed a fresh look
at the whole rung against its whole prompt.

**A rung that feeds multiple downstream shots/crops multiplies the cost of a
missed defect.** `stage_B_crown_star` fed a macro crop, a wide shot, AND a
second macro crop's source — one bad rung silently poisoned three separate
video generations at once before it was caught. Audit a rung MORE carefully,
not the same amount, before cutting multiple crops or wide shots from it.

## Step 5 — generate video (Veo 3.1)

**Correction (2026-08-01), reversing part of this Step's lead rule below:**
"deepen an already-carved region" shots are safe from Veo's perspective
(nothing for the model to get wrong) but often fail the actual viewer test —
measured on a v2 Starbucks build, three such shots each cut a technically
real dark-rind-to-pale-rind sliver, but every cut landed in a small gap
between elements that were ALREADY fully carved on both sides, so the
region read as 100% finished before and after the shot. The user's verdict:
"the knife work does nothing." A cut is only visually convincing if it
converts a LARGE, OBVIOUSLY-STILL-DARK area to pale — not just
technically-correct pixels in a small gap. **Reserve pure deepening shots
for texture/B-roll, not as headline beats** — for anything meant to read as
"real carving happening," use a genuine small-to-moderate transition (an
outline or partially-carved region becoming visibly more carved), pinned
with a hand-built end-frame per the interpolation guidance below. On the
same build, wide shots interpolating between adjacent ladder rungs (each a
~15-25 percentage-point jump, e.g. stage_A→stage_B) worked reliably at full
melon scale, not just as macros — "small bounded change" scopes by visible
dark-area-converted, not by camera framing.

**The single most reliable shot type: deepen an ALREADY-CARVED region, don't
carve a flat one for the first time.** Compare a wolf carving reel's most
delicate-looking moments (pulled the actual frames and job prompts to check)
against the Starbucks reel's flat-to-carved shots: the wolf reel's best shots
are all seeded from an already-carved area and ask for a FEW SMALL
REFINEMENT strokes, e.g. `03_ears`: "the hand works the knife along the
already-carved ear edges, deepening them with THREE short strokes," or
`04_eye_macro`: "traces the eye's edge once to deepen the socket." Nothing
changes STATE in these shots — they start and end carved, and the knife just
makes brief contact, a chip or curl flicks off. That's a fundamentally
easier, safer ask than any flat-to-carved transition, because there's no
state for the model to get wrong. **Build MOST of a reel's shots this way**:
pick a rung that's already carved in the region you want to feature and ask
for small deepening/detailing strokes, not a transformation. Reserve actual
flat-to-carved transitions (see the interpolation guidance below) for the 1-2
shots where showing the change on-camera is the actual point — most of a
reel's motion and "watch it get carved" feeling should come from refinement
shots on rungs that are already mid-progress, with the PROGRESSION itself
carried by which rung each successive shot is seeded from (a later, more-
carved rung), not by any single shot visibly transforming.

**Ask for a small bounded action per shot, not a transformation — and for
that small action, PREFER first+last-frame interpolation with a hand-built
end-frame over open-ended image-to-video.** An earlier version of this file
said to reserve interpolation for one single shot per reel; the Starbucks
carve overturned that. Two separate lessons had been conflated into one:
- **Large transformations fail regardless of technique.** An interpolation
  shot asked to cover a *large* change (a full reveal, most of a face)
  reliably does something implausible — removes half the subject in one
  sweep, redesigns it mid-clip, or renders duplicate tools/hands. This part
  still holds.
- **For a genuinely SMALL bounded change, open-ended image-to-video is the
  LESS reliable technique, not the safer default.** Measured on the
  Starbucks siren carve: three separate plain-i2v attempts at "carve one
  small facial feature" each failed differently — an over-carved seed, a
  wrong-place slash through the face, and seed-disregard plus a hallucinated
  stand appearing under the melon — because nothing anchors where the shot
  is allowed to end; Veo is free to improvise the entire 8 seconds. Switching
  the SAME beat to `last_frame` interpolation, seeding BOTH the start frame
  and a hand-edited end frame (one more Gemini edit: "same image, only this
  one small feature is now carved, everything else pixel-identical"), worked
  on the first attempt — and again on a second beat (one border leaf) after
  the same treatment.

So: **build a matching end-frame for any shot showing a small state change,
and interpolate between them.** Reserve plain i2v for shots that aren't
changing carve state at all (a hero turn-in-hand, a pure hold) — those have
nothing to pin and don't need it.

**This applies to refinement/deepening shots too, not just visible carve-state
transitions — even when nothing about the carved AREA changes.** Measured on
a v2 Starbucks build (2026-08-01): a plain i2v "deepen one already-carved
hair wave" shot — the exact safe pattern this Step's lead rule recommends —
came back with the cut showing dark green rind still visible UNDER the
lifted curl, instead of the required pale inner rind. The carve-state was
never in question (small, bounded, already-carved region, nothing
transforming) — the physics of a single cut was still wrong, invisible at
thumbnail-scrub scale, only caught by a full-resolution frame pull and a
user's own eye. Switching to the same hand-built-end-frame + `last_frame`
technique (end frame = an edit of the seed showing that one stroke ALREADY
made, with the correct pale-under-cut color) fixed it on the first retake.
So: for ANY shot where a specific visual detail must come out correct — not
just "does the carve-state end up right" — pin it with an end-frame rather
than trusting Veo's own judgement of cut physics, material color, or
anything else load-bearing to realism. The "nothing to pin" carve-out above
is narrower than it first reads: it's for shots with no state to get wrong
at all (a pure hold, a turn), not merely for shots where the carve
percentage happens not to change.

**DEFAULT for transition/reveal beats: a stills+crossfade sequence, not Veo
at all — reserve Veo entirely for shots where real tool motion is the
point.** Every Veo failure mode above for transition shots (over-carved
seed, wrong-place carving, seed-disregard, hallucinated props, mid-clip
scene splice) is a *temporal* failure — it comes from Veo having 8 seconds
of freedom with nothing anchoring the middle. A still image has none of that
freedom: it's exactly what you built it to be, deterministically. Since
carving progress can be told through *cuts between stages* (see "Why a
montage" below) rather than continuous motion, a transition beat doesn't
need video at all — only a shot where the knife is visibly moving does (a
refinement shot, per this Step's lead rule; the hero hold).

Technique:
1. Build 3-5 intermediate stages between the transition's start and end
   state, each a small additive edit of the previous one — same tooling and
   same verification rigor as Step 2/4 (full resolution, check every named
   region, don't just trust the one you're focused on; a still stage can
   over-deliver exactly like a ladder rung can).
2. Assemble as a fast crossfade sequence with a slight Ken-Burns pan per
   stage — `build_reel.py` already does this natively (image shots get
   pan/zoom via `zoompan`, blend via the `crossfade` config key), no new
   tooling needed. Put the staged stills in `<proj>/media/` (build_reel.py
   looks there, not `seeds/`) and list them in a `shots.json` with a short
   `seconds` value per stage (~0.3-0.5s each reads as a fast reveal, not a
   slideshow).
3. This runs on the Gemini image-edit endpoint, not Veo — rate-limited by
   Step 0's **2 requests/minute** Google API limit, not the Veo 1/min /
   10-per-day cap, and doesn't compete with that budget at all.

This is a reasoned recommendation from this project's failure evidence, not
yet independently validated end-to-end on a delivered reel — build one
transition beat this way and full-scrub it (Step 6's rigor applies to a
stills sequence too: does the crossfade read as a carve, or as an obvious
slideshow?) before trusting it wholesale. If a stills sequence doesn't read
convincingly, fall back to the hand-built-end-frame interpolation technique
above for that specific beat — it's still the right tool when real motion is
worth spending Veo budget on.

**A bounded, correctly-scoped prompt still carves in the WRONG PLACE when the
subject has a face, even on a bold, high-contrast outline.** Measured on the
Starbucks siren carve: two separate shots, each explicitly scoped to a small
peripheral region (the star, the crown), instead cut an unrequested gash
straight down through the siren's face — on outlines that passed the
low-contrast check from Step 2's own guidance. A face-forward subject (a
face, a mascot, a recognizable character) appears to carry a strong model
prior toward carving the face first regardless of which region the prompt
names. Mitigation that worked: state the CURRENT carved/uncarved condition of
every named region explicitly ("X is already carved — finished"; "Y remains
completely smooth, untouched, unmarked intact rind"), not just the desired
action, and add an explicit negative clause naming the face directly ("the
knife never touches the face; it remains completely smooth and unmarked").
This raised the pass rate but did not make it reliable — budget for at least
one retake on any shot whose seed includes an uncarved face, even a
well-scoped one.

**Don't ask a single 8-second shot to hold a "mostly finished, one region
still flat" state across most of the frame — Veo will often just render the
whole frame as finished, or worse, splice in an unrelated close-up mid-clip.**
Measured on the Starbucks border shot: seeded from a rung where the interior
was fully carved and only a thin border ring was still flat line-art, TWO
separate takes both opened already showing the border fully carved (ignoring
the seed's actual state entirely), and the second take additionally hard-cut
mid-clip to a completely different, disconnected close-up composition that
had nothing to do with the wide framing requested. A large "finished" area
dominating the frame seems to pull the model toward treating the whole shot
as already complete. If a shot needs to show one small area mid-carve while
everything else is done, prefer framing it as a macro tightly cropped on
JUST that area (small finished-vs-flat boundary filling most of the frame) —
the macro pattern from Step 3 — rather than a wide shot where the unfinished
region is a small fraction of an otherwise-finished frame. If a shot fails
this way on its first take, rewriting the prompt with stronger language is
not a reliable fix by itself — it failed the same way twice on the Starbucks
run — treat a second failure on the same seed as a signal to redesign the
shot's framing, not just its wording.

**A cut must reveal the material's correct INNER layer color, or it reads as
physically impossible — state this explicitly, don't assume it's obvious.**
Measured on the Starbucks border shot: a take showed the knife lifting a curl
of dark green rind, but the surface exposed underneath was ALSO dark green
instead of the expected pale inner rind, as if the rind had two stacked
layers of skin. Nothing in the prompt had asserted what should be UNDER the
cut, only what the cut should look like from outside. Add a material-specific
rule to the job's `style_suffix`: "a cut through the [outer color] rind
always reveals the [inner color] beneath it, never another layer of [outer
color]" — and once you've seen the failure happen once, add its own words to
`negative_prompt` too ("green rind visible under a cut", "double green
layer").

**Every shot needs an explicit static-camera, centered-subject guard, or the
subject will visibly drift across cuts.** Each shot in a montage is an
INDEPENDENT generation with no shared camera lock, so Veo is free to frame,
zoom, and position the hand-held subject slightly differently on every call
— even from seeds with visually identical composition. Measured on the
Starbucks reel: the melon's apparent size and vertical position differed
noticeably between wide shots that were meant to look like the same
continuous shot, which reads as the subject jumping/drifting once cut
together — this is what a viewer flags as "keep it centered," and it cannot
be fixed in the recut alone (see Step 7). `veo_carve.py` now appends a
`DEFAULT_STYLE_GUARD` ("static locked-off camera; the subject stays
centered... camera does not pan, drift, zoom") to every shot's prompt
unconditionally, so this no longer depends on a job's `style_suffix`
remembering to say it — but it does not fully solve it (i2v models still
vary framing shot to shot even when asked not to) — treat framing
consistency as something to verify at Step 6/7, not something the prompt
alone guarantees.

```powershell
python veo_carve.py --job jobs/<name>.json --dry-run          # verify prompts/seeds resolve, free
python veo_carve.py --job jobs/<name>.json --shot <name> --takes 3
python veo_carve.py --job jobs/<name>.json --rank --shot <name>
```
Per shot: `resolution: 1080p` + `last_frame` (interpolation) both force
`duration=8`. Seed aspect must match the job's aspect — mismatch =
letterbox. `negative_prompt` for the "two knives / duplicate hand / living
animal" guards.

**`--force` gotcha: a shot's output path is keyed only by NAME
(`media/veo_<name>.mp4`), not by which job file produced it.** Re-running the
same shot name under a different or corrected job file (a redo job, a fixed
prompt) silently SKIPS generation and leaves the OLD — possibly broken —
clip in place unless you pass `--force`. The console prints `[skip] <name>
exists`, which is easy to miss when scanning output for errors, and moving on
without checking wastes a turn believing a fix was applied when it wasn't —
this happened three times in one session before the pattern was caught.
**Always check the output file's timestamp after every regeneration
(`ls -la media/veo_<name>.mp4`) — don't trust the console output alone.**

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

**An independent review pass (even from a stronger/different model) is a
good supplement but not a replacement for actually watching the assembled
reel yourself at full resolution.** On the Starbucks reel, an independent
cold review caught two real, serious defects (a narrative regression, an
inverted color) that the original pass missed — but it also described a
genuinely broken shot (a crop that had captured the wrong design element
entirely) as merely "hair rays / fin" without flagging anything wrong. The
user's own eye, not either automated pass, caught it. Use independent review
to catch what you're too close to see, but a clean review report is not
proof the reel is actually clean — do your own final full-resolution
watch-through too.

## Step 7 — assembly: never stitch on even slots

A naive equal-length stitch reads as synthetic and wastes the technique's
own strengths. Free, no regeneration needed:

- **MANDATORY before picking crop/zoom values: check the subject's size and
  position across every wide shot you're about to cut together.** Because
  each shot is an independent Veo generation (see Step 5's camera-lock
  note), the melon can land at meaningfully different scale and vertical
  position in different "wide" shots even when they're seeded from the same
  composition. Pull a frame from each candidate wide shot at the same scale
  and eyeball them side by side (a small hstack, same trick as Step 4's
  ladder audit) before choosing trim windows or zoom values — don't assume
  "wide" means "same framing." Measured on the Starbucks reel: this check
  was skipped, a single fixed zoom was applied to every wide shot alike, and
  the melon visibly changed size/position across cuts in the delivered
  reel — the exact defect a viewer calls "keep it centered."
- **Vary the shot durations.** A fast burst early, longer shots for the
  money moment, one deliberately tiny (~0.3-0.5s) "flash" cut for an
  unavoidable wide→macro jump — a discontinuity that resolves before the
  eye catches it reads as energy, not error.
- **Punch in on wide shots CENTERED ON THE SUBJECT, not on the frame.** A
  naive `crop=iw/z:ih/z:(iw-iw/z)/2:(ih-ih/z)/2` crops around the frame's
  geometric center — if the subject isn't dead-center in that particular
  clip (see the check above), this crop does nothing to correct it and can
  make the apparent jump worse. Measure roughly where the subject actually
  sits in each clip (eyeball the hstack check) and offset the crop origin
  per-shot so the subject lands in the same place in the output frame every
  time, rather than using one zoom/offset pair for every wide shot. Macros
  are usually already tight enough to skip this.
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
  shot's trim window before shipping. **Caveat, measured on a slow hero
  turn-in-light shot:** this filter can also fire repeatedly on a single
  shot with no cut at all, if a rotating/reflective surface shifts specular
  highlights enough frame to frame — six phantom hits appeared inside one
  smooth, defect-free hero clip on the Starbucks reel. Before treating extra
  detections as a real defect, eyeball a dense scrub of exactly that shot's
  window first (see Step 6) — don't trust the count in isolation.

## Step 8 — final checklist

- [ ] scrubbed every promoted clip full-length, not spot-checked
- [ ] scene-detected cuts == number of shots (no phantom in-shot jumps —
      but verify any extra hits against a scrub before treating them as real)
- [ ] the subject is the same subject/style in every shot, no mid-reel drift
- [ ] **the subject is the same SIZE and POSITION in every shot that's meant
      to read as continuous** — check this explicitly with a side-by-side
      (Step 7), don't rely on the crop math alone
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
6. **For a face-forward subject (a face, a mascot, a recognizable logo with
   a face in it) you haven't carved before, spend one generation on the
   riskiest shot — one where the seed has an uncarved face nearby — as a
   canary before committing the rest of the shot list.** The Starbucks reel
   discovered its face-bias wrong-place-carving failure mode (Step 5) only
   after committing most of a day's rate-limited budget to the full shot
   list; a single canary shot would have surfaced it for the cost of one
   generation instead of three.

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
