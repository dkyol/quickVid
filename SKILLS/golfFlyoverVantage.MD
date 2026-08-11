# golfFlyoverVantage — golfer's-eye broadcast flyover (tee cam → fairway track → green reveal)

A **plan**, not yet a script. Sibling to `golfFlyoverSkill.MD`, same goal (one
cinematic 9:16 hero flyover of a single hole, grounded in real geography) but
a **different camera language**. `golfFlyoverSkill.MD` produces a straight-down
"map cam" flyover — useful, but it's a satellite view, not what a golfer (or a
PGA broadcast) actually sees. This skill produces the broadcast-standard shot:

> Camera starts at **grass-top / eye level, right behind the tee box** —
> essentially ground height, not an aerial drone height — looking almost
> straight down the fairway toward the horizon. It glides forward smoothly at
> that low height, following the fairway's real line. Near the green, it
> **rises sharply** into a high wide reveal of the green complex.

That's three distinct camera beats (tee ground-level glide → fairway
ground-level tracking → green high reveal), not one continuous altitude/angle
the way the top-down version is, and the low beats are **much lower than a
drone establishing shot** — see the reference clip below.

**Reference clip**: `SKILLS/references/golfFlyoverVantage_tee_reference.mov`
(supplied 2026-08-11, ~3.5s). This is the ground truth for the tee/fairway
camera beat — read it before generating anything, don't work from the prose
description alone. What it actually shows, frame-scrubbed at 6fps: camera at
**grass height** (a few feet off the turf, not 20-30ft — an earlier draft of
this file guessed 20-30ft from a verbal description before this clip existed;
the clip overrides that guess), looking almost horizontally down the fairway
**directly into a low golden-hour sun** — strong lens flare/God-rays, warm
orange-gold color grade, pine trees silhouetted black against a bright sky,
sharp white-sand bunker edges with dark green fringe grass, a dark water
hazard visible off to one side, green fairway filling most of the lower
frame. Motion is a smooth, steady, near-constant-velocity forward glide —
no visible banking or altitude change in this clip (that's the tee/fairway
beat only; the clip doesn't cover the green's altitude-rise beat, which is
still per the prose description below until a reference for it exists too).

**Why this is a separate file, not a variant flag on the other skill:** the
camera change isn't cosmetic. `golfFlyoverSkill.MD`'s whole method is
"satellite/map crop → image-to-image, explicitly told to *keep the same
camera angle* and just add photoreal texture." That works because nadir
satellite pixels already *are* the top-down camera. For a low oblique
broadcast angle, there is no equivalent real pixel source — nothing in the
geography pipeline is shot from 20ft above a tee box. The image model has to
**synthesize a 3D perspective from a flat 2D map**, not just re-skin one. That
is a strictly harder, lower-fidelity-guaranteed task, and treating it with the
same "preserve the exact camera angle" prompt language (which is what
happened the first time this was attempted, before this file existed) just
produces another top-down shot with warmer lighting — not what was asked for.
Keep the two skills separate so `golfFlyoverSkill.MD`'s validated
camera-preserving recipe doesn't get quietly broken by this harder case.

---

## What to reuse from `golfFlyoverSkill.MD` unchanged

Everything about **finding the real geography** carries over exactly — read
that file's step 2 first:
- Geocode the course (Nominatim) → OSM Overpass `golf=hole ref=N` lookup for
  exact tee/green GPS + par, cross-checked against the scorecard yardage.
- Earth Engine NAIP fetch, rotated tee→green vertical, with the
  `dimensions:"WxH"` square-pixel fix and the OpenCV-matrix rotation approach
  (both documented there after being hand-debugged once — don't re-derive).
- Earth Engine one-time setup / stale-token / project-permission gotchas.

**The only thing that changes is what this map crop is used *for*.** In
`golfFlyoverSkill.MD` it's the direct camera-preserving I2I input. Here, it's
a **layout reference** — hand it to the image model as "here is the hole's
real shape, hazard positions, and proportions" while the prompt asks for a
completely different, invented camera position. If hole 8 (or any hole)
already has a validated `golfFlyoverSkill.MD` run done, **reuse its rotated
satellite crop directly** — no need to re-derive geography from scratch for
the same hole.

---

## ▶ Let's get started

0. **Confirm scope**: one hero flyover, one hole, golfer's-eye broadcast
   camera (tee low-angle → fairway track → green high reveal) — confirm this
   is actually the wanted look vs. the top-down version; ask if unsure, the
   two read very differently.
1. **Course + hole + style** — same as `golfFlyoverSkill.MD` step 1
   (course/hole number, lighting default golden hour).
2. **Get the map/geography seed** — `golfFlyoverSkill.MD` step 2, verbatim
   (or reuse an existing rotated crop for this hole if one exists).
3. **Build three waypoint stills with the NEW camera treatment** (see
   "Waypoints" below) — each one asks the model to invent an oblique/elevated
   3D camera view *consistent with* the flat map's real layout, not to
   preserve the map's own camera angle. Eyeball all three specifically for
   **perspective plausibility** (see QC below) before spending on video — this
   step is riskier than the top-down version's, so don't skip the eyeball.
4. **Generate two chained video segments** (tee→fairway, fairway→green) with
   a start+end-frame model. Same model guidance as `golfFlyoverSkill.MD`
   ("Which model" section) — Veo 3.1 for native audio, Artlist draft tier to
   validate cheaply before the hero pass.
5. **Trim + cut/crossfade, grade pass**, same as `golfFlyoverSkill.MD` step 5.
6. **QC** — same checklist as `golfFlyoverSkill.MD` **plus** the
   perspective-specific checks below.
7. Deliver to `final/flyover_<course>_<hole>_vantage_<stamp>.mp4` — the
   `_vantage` suffix keeps it distinguishable from a top-down run of the same
   hole.

---

## Waypoints — three camera beats, not one camera height

| waypoint | camera | what it shows |
|---|---|---|
| A — tee | **grass-top / eye level**, right behind the tee box, looking almost horizontally down the fairway toward the horizon (see reference clip — not an aerial drone height) | golfer's own sightline off the tee, into the sun, golden hour |
| B — fairway | continuing at the same ground-hugging height, further down the hole, following the fairway's real curve/dogleg | mid-flight ground-level tracking, still low, not yet risen |
| C — green | camera **rises sharply** in altitude | high wide reveal of the green complex, bunkers, contours — this beat is visually close to a top-down/high-angle shot again |

**Prompt each waypoint against the rotated map crop as a layout reference,
explicitly describing the invented camera position** — don't reuse
`golfFlyoverSkill.MD`'s "keep the exact same camera angle (straight down /
top-down aerial)" line, that's the wrong instruction here. Instead (matching
the reference clip — grass height, not a drone-height establishing shot):

> "Cinematic shot from grass-top height, right behind the tee box, looking
> almost horizontally down the length of the fairway toward the green in the
> distance, camera pointed toward a low golden-hour sun near the horizon with
> strong lens flare. Pine trees silhouetted against the bright sky, sharp
> white-sand bunker edges with dark green fringe grass, warm orange-gold
> color grade. Not a drone establishing shot, not a satellite or map view —
> ground-level, the golfer's own sightline off the tee. Reinterpret this hole
> from that low, near-horizontal perspective. The fairway's real curve/dogleg
> direction, the pond's position relative to the fairway (left/right as seen
> from the tee), and the tree line placement must match the reference map's
> layout — do not mirror-flip left/right, do not add, move, or resize any
> hazard."

The **explicit "do not mirror-flip left/right" line matters specifically
here** and has no equivalent in the top-down skill: a flat top-down map has no
canonical "left/right from the tee" until you commit to a viewing direction,
and an image model asked to invent a 3D perspective from 2D data has a
roughly 50/50 chance of picking the wrong-handed interpretation unless told
not to. Catch this in QC (below), it's easy to miss at a glance because the
*shapes* still look right, just mirrored.

For waypoint C (green, high reveal), the target framing converges back toward
something close to `golfFlyoverSkill.MD`'s top-down green crop — if that
skill has already been run for this hole, **its validated arrival still
(waypoint C from that run) is a legitimate candidate to reuse or lightly
re-angle here**, rather than re-synthesizing a high aerial from scratch.

---

## Which model

Same guidance and same hard-won lessons as `golfFlyoverSkill.MD`'s "Which
model for the camera motion" section — read that section, it isn't repeated
here. In particular, carry forward unchanged:
- Default to Veo 3.1 (native audio) via whichever access is live —
  **check `get_balance` / `list_models`'s `freeGeneration` flag for the
  actual connected account** rather than assuming a tier table; the account
  used for the first `golfFlyoverSkill.MD` run was a flat credit pool
  (Artlist "AI Suite 40K"), not the unlimited-lite tiers originally assumed.
- Draft cheap (Artlist draft-tier stills, and optionally a cheap/free video
  model for a first motion sanity check) before spending on the Veo hero pass
  — **more important here than in the top-down skill**, because the camera
  synthesis itself is the new, unvalidated part, not just the motion.
- **Explicitly set `negative_prompt`** against hovering/static shots — a
  positive-prompt-only "never stops moving" instruction was proven
  insufficient on the top-down run's first attempt (one segment read as
  near-hovering for its full 8s despite that exact instruction).

## Prompting the flight

Same "prompt the finished, continuous motion" principle as
`golfFlyoverSkill.MD`, but the motion itself has three beats here, not one
continuous altitude change — say so explicitly rather than leaving the model
to guess where the rise happens:

> "Continuous smooth cinematic shot. Starts at grass-top height right behind
> the tee, gliding forward at a steady near-ground level toward a low
> golden-hour sun with lens flare, following the fairway's real curve, pine
> trees silhouetted against the sky. As it nears the green, the camera rises
> sharply and smoothly in altitude, opening up into a high wide view of the
> green complex and its surrounding bunkers. Long shadows, grass texture
> visible, warm orange-gold color grade. No cuts, no hovering, camera never
> stops moving. The fairway shape, hazard positions (do not mirror-flip
> left/right), and green contour must match the reference layout — do not
> add, move, or resize any hazard or green."

If the rise-at-the-end beat and the tee/fairway low-tracking beat don't chain
convincingly in one video generation, split it the same way
`golfFlyoverSkill.MD` splits tee→fairway and fairway→green: generate the
low-altitude tee→fairway track as one segment, and a **separate**
fairway→green segment whose whole job is the altitude rise, rather than
asking one 8s clip to convincingly do both a long low track and a sharp
climb.

## Assembly

Same as `golfFlyoverSkill.MD`'s assembly section (trim to best window, short
crossfade timed to matching angle/altitude at the cut, saturation/contrast
grade pass) — no changes needed here, the join logic doesn't care which
camera style produced the clips.

## QC checklist — everything from `golfFlyoverSkill.MD`, plus:

- [ ] **Scrub at 4fps and tile into a contact sheet**, not 1fps — same lesson
      as the top-down skill, confirmed the hard way there.
- [ ] **Perspective plausibility** — does the horizon/vanishing-point logic
      hold as the camera moves (consistent apparent scale change, no sudden
      "flattening" back toward a top-down look mid-shot)? An image model
      synthesizing an invented 3D view from a flat map can partially collapse
      back toward the nadir angle it was conditioned on — watch for this
      specifically at the tee and fairway beats.
- [ ] **Left/right handedness matches the real hole** — compare the
      generated tee shot's hazard placement (which side the pond/creek/trouble
      sits on, as seen from the tee) against the real map. This is the
      mirror-flip failure mode called out above; it will NOT show up as a
      "wrong shape" — the shapes look fine, just reflected.
- [ ] **The altitude rise at the green reads as a real climb**, not a hard
      cut to a different clip — same continuity logic as the top-down skill's
      cut-matching, applied to an in-shot altitude change instead of a
      between-shot cut.
- [ ] Everything else from `golfFlyoverSkill.MD`'s checklist (geography
      holds, full 1080×1920 no letterbox, no invented hazards) unchanged.

## Cost discipline

Same rule, same count (2 video generations + up to 3 image renders), same
"state it and get a go-ahead before spending" — but budget for **a higher
chance of needing a re-roll on the stills**, not just the video, since the
camera-angle synthesis is the new unvalidated step. Don't assume the top-down
skill's per-shot cost as a baseline for this one until it's been run once.

---

## The first attempt looked fine and wasn't — read this before trusting any QC pass on this skill

Hole 8's first real run (2026-08-11) produced a clip that passed every QC
check in this file — no mirror-flip, no hover, geography-shaped hazards in
the right left/right position, clean assembly — **and it was still wrong in
a way that mattered:** a bunker appeared to sit right off the tee, the whole
hole read as maybe 150 yards long instead of 455-485, and the real fronting
creek in front of the green got fused into a repositioned pond that looked
like it ran beside the fairway instead of crossing in front of the green.
The user, who's actually played the hole, caught it immediately from the
video; nothing in this file's QC checklist would have.

**Why the checklist missed it:** synthesizing a low oblique view from a flat
top-down map is not a perspective *projection* — the image model has no
camera model, no depth, no terrain mesh. It composites "plausible golf photo
elements" using the reference for loose shape/color cues, not as scaled
geometry. So it can nail left/right placement (a coarse, roughly-binary
property) while being **completely wrong on distance and relative scale**
(a continuous property the model has no mechanism to get right from a nadir
map, no matter how the prompt is worded — stating exact yardages in text
didn't fix it either). This is a capability gap, not a prompting gap, and no
amount of QC-after-the-fact catches it reliably if you don't know the real
hole — the output looks *internally* plausible.

**The actual fix, confirmed on the re-run: use a real photo whenever one
exists**, even one taken in the wrong weather/lighting. A single real
ground-level photo of the tee (supplied by the user, `IMG_4447.JPG` — see
`SKILLS/references/` if kept) as the video's *start frame* fixed everything
the synthesis got wrong, because Veo's job at that point is "extrapolate
plausible continued motion from real pixels," which these models are
genuinely good at — a much smaller ask than "invent an entire scene's
geometry from a flat map." The corrected run:
- Used the real tee photo directly (cropped to 9:16, real overcast lighting
  kept as-is rather than relit — relighting a real photo was offered as a
  safer alternative to full synthesis but wasn't needed here) as the true
  video start frame instead of a synthesized still.
- For the one waypoint still that still had to be synthesized (mid-fairway,
  past the dogleg — no second real photo existed), the fix was **explicitly
  forbidding the model from showing the green or its bunkers at all**, since
  the real dogleg means they genuinely aren't visible yet from that point.
  Removing the target that was getting hallucinated-close is more reliable
  than asking the model to place it far away correctly.
- Matched the real photo's actual overcast lighting instead of forcing
  golden hour — fighting the model back toward invented "golden hour"
  lighting via `negative_prompt` (`"golden hour, sun flare, lens flare,
  sunny"`) was necessary; the positive prompt alone kept drifting back to it.
- Reused `golfFlyoverSkill.MD`'s validated top-down green still for the
  final reveal, unchanged from the first attempt — that part was never the
  problem, both attempts got that piece right.
- Same "arrives early, holds static for the tail" Veo pattern hit the
  fairway→green segment again (arrives ~t=4.5-5s of 8s) — same free trim
  fix as before, now confirmed on three separate runs across both skill
  files.

**Correction to the above (same day, same hole): a real photo does NOT fix
the whole shot — it only grounds the first ~3-4 seconds.** The "corrected"
run described above was itself still wrong, just later in the timeline: past
roughly t=4-5s (however far the video model can extrapolate before it runs
out of real pixels to lean on), it fell back to the exact same hallucination
—an invented bunker beside the pond that doesn't exist there — that the
first, fully-synthesized attempt showed from t=0. The user caught this too,
from watching the video, not from any QC step in this file. Root cause,
confirmed by inspecting what data actually reaches the video generation
call: **the satellite/map geometry is never passed to the video model at
all** — only the two still-frame endpoints and a text prompt are. Everything
in between is generated from the model's own trained priors about "golf
course footage" with zero access to this hole's real layout. This is a
structural limitation of current video diffusion models (no persistent 3D
scene/depth representation across a multi-second unconstrained span), not a
prompting problem, not an Artlist-vs-direct-API problem, and not something
a better reference image fixes — confirmed by testing the direct fix
(real photo as start frame) and watching it fail past the point where the
real photo stops being close-enough context for the model to lean on.

## Resolution actually used for hole 8: hybrid, not sustained ground-level video

**Do not attempt a full ground-level traverse of a long hole via video
generation — cap any AI-generated ground-level motion at a few seconds past
a real anchor, or don't generate ground-level video at all.** What actually
shipped for hole 8:
1. The real tee photo, held as a **static/Ken-Burns zoom via ffmpeg** (no AI
   video generation at all — deterministic pixel-level zoom on real pixels,
   zero hallucination risk by construction), ~3.5s, hole-card burned in
   (hole #, par, yardage, course name) for the first ~2s.
2. **A hard cut directly into `golfFlyoverSkill.MD`'s already-validated
   top-down flyover** for the rest of the hole, instead of continuing to
   attempt a ground-level fairway traversal.
3. This intentionally abandons the "one continuous golfer's-eye camera move"
   premise this file originally set out to build. That premise turned out to
   require accurate long-range video synthesis that doesn't exist yet as a
   reliable capability — worth being honest about rather than re-attempting
   with new prompt wording, which was tried twice already and failed both
   times for the same structural reason.

**Default recommendation for the next hole**: don't promise a sustained
golfer's-eye flyover for anything longer than a real photo/video can directly
support. If a real ground-level photo exists for the tee, use it (static or
lightly zoomed, ffmpeg-only) for an honest opening beat, then cut to the
top-down skill's output for the rest. If no real photo exists, skip the
ground-level beat entirely and just run `golfFlyoverSkill.MD`. Only attempt
AI-generated ground-level *motion* (not just a static/zoomed photo) for a
window of a couple seconds immediately adjacent to a real anchor image, never
for a full fairway traverse, and treat even that as an experiment to QC
carefully rather than a reliable default.

## Open items (still unresolved)

- Whether a couple-second (not 8s) AI-generated ground-level motion clip,
  immediately following a real photo, stays grounded reliably — untested;
  the two full-length (8s) attempts both drifted into hallucination, but a
  much shorter ask was never isolated and tested on its own.
- Untested: whether reusing a top-down skill's green still for waypoint C
  works as well when no prior top-down run exists for that hole.
- Total cost across all attempts on hole 8: ~150 credits stills + 13,600
  credits video (4 Veo generations, all 4 ultimately unused in the final
  delivered hybrid clip) = ~13,750 credits spent on video generation that
  didn't ship. The final delivered result used **zero** additional Veo
  spend beyond what golfFlyoverSkill.MD had already validated — the entire
  ground-level-video budget on this run was spent learning that the premise
  doesn't work, not on usable output. Budget the *next* hole's vantage
  attempt assuming this finding holds (cap ground-level AI video at a couple
  seconds or skip it) rather than re-discovering it at full hero-pass cost
  again.
