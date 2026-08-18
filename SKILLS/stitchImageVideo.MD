# stitchImageVideo — chain N unrelated stills into one reel via i2v continuation, cut before hallucination, hide the cut in a blur whip

Driver script: **`stitch_video.py`** (root of the repo). It reuses
`veo_carve.py`'s Google client, retry/quota handling and aspect-mismatch
guard unchanged rather than re-deriving them, and adds the trim + blur-whip
transition + concat step as free ffmpeg work on top. Validated end-to-end
on synthetic clips (2026-08-15), **and since run start-to-finish on real
Veo footage the same day** (a 6-image DC riverside run reel) — see "Which
model" and "What's actually verified vs. not" below for what that first
real run settled. **A second full edit pass on that same reel (2026-08-18)**
— re-pacing, per-clip motion-speed normalization, dropping a bad seed, and
a whole alternative cut structure — is what "Alternative: the photo-beat
cut" and the `"speed"` field below come from; see that section and "Open
items" for what it settled.

```
python stitch_video.py jobs/<name>.json generate --dry-run
python stitch_video.py jobs/<name>.json generate
python stitch_video.py jobs/<name>.json generate --image 01_trailhead --takes 3
python stitch_video.py jobs/<name>.json rank --image 01_trailhead
python stitch_video.py jobs/<name>.json promote --image 01_trailhead --take 2
python stitch_video.py jobs/<name>.json sheet --image 01_trailhead --fps 4
python stitch_video.py jobs/<name>.json assemble
```

Full job schema and phase-by-phase behavior are documented in the script's
own module docstring — read that before writing a job file, it's the
source of truth for the CLI, not this prose.

## The idea in one line

Given a folder of still images (a trail, a room, a product, whatever — the
images don't need to be related to each other), generate a short
**image-to-video continuation** of each one on Google Veo, but don't try to
make any single clip run long: **find the moment each clip stops being a
faithful continuation of its real seed photo and starts inventing content
that isn't grounded in it, cut a beat before that moment, and disguise the
cut as a deliberate blur-whip + speed-ramp transition into the next image's
clip.** Repeat per image, concat the result. The viewer reads a fast,
stylized, cut-heavy reel; nothing in it runs long enough to show the seams
where the model would have started making things up.

## Why this works — the finding this plan is built on

`golfFlyoverVantage.MD` already measured the exact failure mode this skill
is designed around, the hard way, across two full attempts on real spend:
a Veo continuation from a real photo **only stays grounded for roughly the
first 3-5 seconds** (varies by scene) before it falls back to the model's
own trained priors about "what this kind of scene generally looks like,"
because **the source geometry is never actually passed to the video
model** — only the seed frame(s) and a text prompt reach the API, so
everything after the seed's influence fades is synthesized from scratch
with zero access to the real scene. That file treats this as a limitation
to work around (cap ground-level AI motion to a couple seconds, or don't
generate it at all, and cut to something else instead).

**This skill treats the same limitation as the whole point of the edit.**
Instead of fighting the divergence or hiding from it, use it as the natural
cue for *when to cut*: every clip in this pipeline is, by construction, only
ever shown during its grounded window. The fast-cut, blur-whip aesthetic
this produces isn't a compromise forced by the limitation — genre reels that
already look like this (whip-pan travel edits, product reveal montages) are
*exactly* the case where hiding a hard cut behind motion blur reads as a
deliberate stylistic choice, not an error. Same root cause as the vantage
skill's finding, opposite editorial response: there, divergence was a bug to
avoid; here, divergence timing is the beat sheet.

---

## ▶ Let's get started

0. **Ask which images, in what order, before doing anything else** — per
   standing instruction, never assume `media/` or reuse a prior session's
   images silently. Confirm: how many stills, their rough subject (so
   prompts can be written per-image), desired total reel length, and
   whether this needs a voiceover/music bed or is silent b-roll.
   **Screen every candidate seed for legibility before spending a
   generation on it** — measured on the DC riverside reel (2026-08-18): one
   seed (a phone photo looking straight up through tree canopy) was already
   motion-blurred and out of focus with no ground, path, or landmark in
   frame. No amount of downstream fixing rescued it — not a better cut
   point, not showing the seed itself first (see "Alternative: the
   photo-beat cut" below), nothing — because the confusion was already
   baked into the source photo: a generation *can't* invent legibility a
   blurry seed never had. A seed that fails a "would this one frame make
   sense as a standalone photo" test by eye should be dropped or swapped
   before it burns a paid generation, not after.
1. **Prep every seed to the output aspect (9:16 default) before generating
   anything.** Veo honors the seed's own framing and **letterboxes** if the
   seed's pixel aspect doesn't match the requested output — this is a
   measured, silent failure (`veo_carve.py`'s `check_seed_aspect`): the job
   completes successfully and still hands back 1080x1920 with black bars,
   invisible in a code review because the defect lives in the PNG's pixel
   dimensions, not any line of code. Crop/pad every still to 1080x1920 (or
   the real target) up front, don't rely on the API to do it.
2. **Pick the model** — see "Which model" below. Default to
   `veo-3.1-lite-generate-preview` for cost, since this pipeline's
   generation count scales with the number of images (N stills = at least N
   generations, more with re-rolls) — a materially different cost shape
   than the carving skills' fixed 8-10 shot budget.
3. **Generate one continuation clip per image**, image-to-video from a
   single seed — **no `last_frame`/end-frame here**, unlike the carving
   ladder's rung-to-rung interpolation. There is no "next real frame" to
   land on: each image is an independent scene, so the only job is "extend
   this one real photo forward plausibly for as long as it stays grounded."
   Ask for the model's max/1080p duration (probe first — see below) rather
   than a short clip, since the useful window is found by trimming after
   the fact, not by requesting a short generation up front.
4. **Find the divergence point in every clip — full-clip scrub, not a spot
   check.** This is the step the whole technique depends on getting right,
   and it is exactly the QC failure mode already burned once in
   `imageGenSkill.MD`'s "v8 EXECUTED" section: three clips there looked
   clean at two hand-picked timestamps and had already gone fully off the
   rails by the next second. Do this per clip:
   - Decode to a contact sheet at **4fps minimum** (1fps for anything longer
     than ~6s) — same fix the golf vantage skill and the carve v8 postmortem
     both landed on independently.
   - Compare each frame against the seed image itself, not just against
     neighboring frames — the divergence question is "does this frame still
     show the same real place/object as the photo," not "did the video move
     smoothly," which a frame-to-frame diff alone won't catch (motion can
     stay smooth while content quietly drifts away from the seed).
   - `veo_carve.py`'s `score_clip()` (`drift` = distance from seed at a
     given point) is a **shortlist tool only** — it separated good/bad
     carve takes 2:1 in that project but is not a verdict on its own; the
     same file's own postmortem documents a case where the top-ranked take
     by this metric was the one that blew up. Use it to flag which clips to
     scrub first, not to decide the cut point.
   - Record the divergence timestamp per clip (e.g. `t≈3.8s`).
   - **The thumbnail contact sheet can itself be too low-resolution to catch
     a real divergence.** Measured on the first real run: a 140px-wide tile
     contact sheet made a hallucinated person forming in a tree canopy look
     like ambiguous foliage noise, easy to wave off — pulling full-resolution
     frames at 0.5-1s intervals around the suspect window made it obvious
     (a clear figure) at the same timestamp the thumbnail had obscured. Use
     the contact sheet to find which clips and which rough windows need a
     closer look, then confirm the actual cut point against full-resolution
     frame extracts, not the thumbnail itself, before trusting a "looks
     clean" verdict. The inverse also happened in the same run: a clip that
     looked like it grew an invented tree from thumbnail alone (small tree
     in seed appearing to balloon in size) turned out, on full-res frames,
     to be a real tree from the seed correctly growing larger from normal
     forward-motion perspective — the thumbnail was misleading in both
     directions, not just the risky one.
5. **Trim to a beat before divergence, never to the edge of it.** Same
   "trim EARLY windows, never the tail" rule as `veo-behavior-quirks`
   memory and the vantage skill's frame-snap lesson — leave ~0.3-0.5s of
   margin before the first frame that reads as invented, since the exact
   divergence boundary is fuzzy by eye and erring late reintroduces the
   thing this whole technique exists to avoid.
6. **Build the transition** at each cut (see "The blur-whip transition"
   below) between clip *i*'s trimmed tail and clip *i+1*'s head.
7. **Repeat 3-6 for every image**, then concat all segments in order.
8. **Grade + audio pass**: consistent saturation/contrast across clips (Veo
   generations drift in exposure/warmth independently per-call, same as the
   carve chain's measured drift — normalize with one `eq`/`colorbalance`
   pass over the whole timeline rather than trusting per-clip consistency),
   music bed under the whole thing since native Veo audio across
   independently-generated, unrelated-scene clips won't cohere as a
   soundtrack the way it does within one carving subject.
9. **QC** — see checklist below.
10. Deliver to `final/stitch_<name>_<stamp>.mp4`.

---

## Which model

| | `veo-3.1-lite-generate-preview` | `veo-3.1-fast-generate-preview` | `veo-3.1-generate-preview` |
|---|---|---|---|
| cost | lowest (assumed — verify against live pricing/balance, not stated in this file) | mid | highest |
| fidelity to seed / prompt adherence | **measured strong on the stitch project's first real run (2026-08-15)** — see below | measured worse than standard on the carve project (duplicate knives, raced past its bound) | measured best of the three on the carve project |
| when to use here | default draft AND likely default final, given the per-image generation count | cheap probe / fallback if lite's grounded window is too short to be usable | reserve for a hero image that's carrying the reel, if lite visibly hallucinates too early on it |

**Confirmed on `lite` (2026-08-15, real billed run, 6-image DC riverside reel)**
— `veo_carve.py`'s constraints (last_frame needs 8s, 1080p needs 8s, aspect
letterboxing) were originally measured against the **standard** model on
2026-07-27; lite turns out to differ on exactly one of them:
- **1080p works on lite at the full 8s duration** — no forced shorter clip,
  same as standard. Confirmed output: 1080x1920, 24fps, h264, native AAC
  audio track, no letterbox (with seeds pre-cropped per step 1).
- **`negative_prompt` is REJECTED outright on lite** — passing it 400s with
  `INVALID_ARGUMENT: 'negativePrompt' isn't supported by this model`. This
  is a hard difference from standard (which does honor it, per
  `veo_carve.py`). **Omit `negative_prompt` entirely from lite job files**
  (both the job-level and per-image field) — the 400 happens before any
  billing, so this is a free, instant failure to design around, not a cost
  risk, but it does mean the fix in "Prompting each continuation" below
  (fold the constraints into the positive prompt as explicit "do not"
  clauses) is mandatory for lite, not optional style.
- **Grounded-window length is scene-dependent, and can massively exceed the
  "3-5s" standard-model figure**: of 6 lite generations in the first real
  run, 4 stayed fully grounded for the entire 8s with zero visible
  divergence at any point (confirmed via full-resolution frame checks, not
  just the thumbnail sheet — see the QC finding below), 1 was fine to at
  least 7.5s, and 1 hallucinated a person into a tree canopy starting
  somewhere between t=5.0s and t=6.5s. Texture-heavy/repetitive scenes
  (dense foliage, a long uniform architectural corridor) seem to hold up
  far longer than open/geometrically-specific scenes — plausible since
  "more of the same leaves" is a low-risk continuation for the model even
  with zero real depth information, but this is an observation from one
  run, not a rule to design a whole job's `cut_at` values around blind.
- **Never call the paid API just to probe availability** (`imageGenSkill.MD`
  spend rule #1 — a "quota probe" is a real billed generation). Probe with
  one cheap real generation you'd want anyway (the first image in the
  sequence), read the response/error for the answers above, and adjust the
  job for the rest of the run rather than guessing up front. This is exactly
  how the `negative_prompt` rejection above was found — the probe call
  failed for free before any clip was actually billed, and the job was
  fixed before the batch of 5 remaining paid generations ran.

Reuse `veo_carve.py`'s `client()`, `generate()` (drop the `seed_end`/
`last_frame` argument entirely — this pipeline never uses it),
`check_seed_aspect()`, and the `QuotaExhausted`/503-retry handling
unchanged rather than re-deriving Google API plumbing that's already been
hand-debugged once.

## Prompting each continuation

Two things the prompt needs to do that the carving skills' prompts don't:

1. **Ask for continuation of THIS specific scene, not generic motion in the
   genre.** Where the carve prompts describe an invented finished state
   ("prompt the finished state, not the activity"), this pipeline wants the
   opposite: describe only camera movement, and explicitly forbid
   introducing new subjects, people, objects, or scene elements not already
   visible in the frame. Something like:
   > "Continue this exact scene naturally, camera moving forward along the
   > trail at a steady walking pace. Do not introduce any new people,
   > animals, structures, or objects that are not already visible in the
   > frame. Do not change the weather, lighting, or season. If the path
   > curves or the view is blocked, follow it naturally rather than cutting
   > through or revealing what's beyond it."
2. **Set `negative_prompt` against the specific hallucination this scene
   invites** — but only if the model actually honors it. **`veo-3.1-lite`
   does not: it 400s outright if `negative_prompt` is present at all**
   (confirmed 2026-08-15; see "Which model" above). On lite, fold the same
   intent into the positive prompt instead, as explicit "do not" clauses
   tailored per image — e.g. instead of a separate
   `negative_prompt: "new people appearing, new buildings, sudden scene
   change, extra pets, text overlays"`, end the positive prompt with "Do
   not introduce any new people, animals, boats, or structures that are not
   already visible in the frame. ... No text, captions, or watermarks."
   This reads as slightly more verbose prompt but is otherwise equally
   effective and is the only option lite accepts. Standard and fast *do*
   honor a real `negative_prompt` field (confirmed in `veo_carve.py`) — use
   the dedicated field there instead of folding it in.

## The blur-whip transition

Goal: hide a hard content cut (real trail photo A's grounded footage → real
trail photo B's grounded footage, two different places) the same way a whip
pan disguises a cut in live-action editing — motion blur and speed peak
exactly at the cut, so the eye can't resolve either frame at that instant.

Outgoing clip (last `whip_seconds` before the trim point) and incoming clip
(first `whip_seconds`) both get compressed in time by `speed` and blurred,
then joined with a short `xfade`. `stitch_video.py`'s `assemble` phase
builds this as three small ffmpeg calls per cut (trim+speed+blur each side,
then xfade the two results) rather than one combined filtergraph — easier
to debug, and each intermediate lands in `<project>/cut/` so a bad
transition can be re-inspected without re-running the whole reel.

**Implemented simplification, worth knowing before tuning a job's
`transition` block**: the blur is a **constant `gblur` sigma** across the
whole whip window, not a per-frame ramp from sharp to fully blurred.
`gblur`'s `sigma` option is a plain number, not a per-frame expression, on
the ffmpeg build bundled in `tools/` — a true ramp would need either a
build-specific expression feature that isn't guaranteed to exist, or
compositing several separately-blurred copies with a time mask, which is a
lot of machinery for a window that's only ~4-6 frames long at the default
0.4s/2.5x settings. A constant blur combined with the speed compression and
the crossfade reads as a whip in practice at that length; tune `blur_sigma`
in the job's `transition` block first before reaching for anything fancier.

Two knobs actually drive how hidden the cut is, both in the job's
`transition` object:
- `speed` — how hard the whip window is compressed. Higher hides more
  content mismatch but reads more like a stylized whip; lower reads more
  like a plain cut with a blur filter slapped on it.
- `xfade_seconds` — how much of the (already compressed) whip window is
  spent crossfading the two blurred segments into each other. Capped in
  code to the compressed window's own length, so it can't exceed what
  actually exists to fade.

If a constant gaussian blur doesn't sell the whip on real footage, the
noted upgrade path is a directional/zoom blur instead (radial blur toward
frame center, or a fast `zoompan` push) — a real whip pan blurs
*directionally*, not uniformly, and gaussian alone can read as "out of
focus" rather than "moving fast." Not implemented; flagged in Open Items.
- Keep the transition **short** (under ~0.3s total). A long blurred
  crossfade reads as a dissolve, not a whip, and dissolves don't hide
  content mismatch the way a fast whip does — this is the same "a real
  montage cuts, it does not fade" principle `imageGenSkill.MD`'s Chained
  Montage section already established for the carve reels' own hard cuts.

## Alternative: the photo-beat cut (show the seed, don't hide it)

Everything above is built to **hide** the cut between unrelated scenes —
that's correct when the reel's whole point is one continuous flowing
motion and the viewer never needs to clock that it's N unrelated photos.
It's the wrong call when the format is closer to a recap/explainer (a run
route, a build log, a before/after) where the viewer benefits from
actually *recognizing* "this is a real photo of a real place" before the
motion starts. Measured directly on the DC riverside reel (2026-08-18):
even after fixing pacing and per-clip motion speed, a continuous i2v cut
straight into an ambiguous seed (see step 0's tree-canopy example) read as
"I don't understand what's happening," because the viewer was never shown
a clean, static reference frame to anchor the motion to.

**The structure**: `[seed photo, held] → [i2v generation, hard cut in] →
[next seed photo, held] → [next generation] → ...` — plain `concat` cuts,
no blur-whip transitions at all (which also simplifies the ffmpeg side:
no whip/xfade passes, just a still-image hold clip per seed and a trimmed
body clip per generation, concatenated in order).

**The hold has to be a flash, not a freeze — measured the hard way.** A
~0.7s hold (chosen as "long enough to clearly read as a photo") produced a
brand-new complaint: "at each transition the runner looks briefly
stopped." The cause had nothing to do with which frame the *generation*
ends on — it's that a fully static hold sitting right at the cut boundary
is, by construction, a zero-motion segment for most of a second, and
motion perception reads any nonzero-to-zero transition as a hard stop
regardless of how much motion preceded it. Cutting the hold to ~0.15-0.2s
(4-5 frames at 24fps — long enough to register as "that's a real photo,"
short enough to read as a flash-cut, not a freeze) removed the complaint
with no other change. **Default to the low end of that range** — an
over-long hold silently reintroduces the "stopped" problem this structure
exists to avoid, and it's an easy failure to miss on a casual watch (it
reads as normal pacing until someone watches specifically for motion
continuity across the cut).

**When to use which**: blur-whip (main technique above) for pure
b-roll/mood reels where disguising scene changes is the whole point;
photo-beat cut for anything where letting the viewer clock "yes, that's a
real photo" is worth more than hiding the cut.

## Matching apparent motion speed across clips

Each seed is an unrelated scene, so Veo has no shared reference for how
fast "forward at running/walking pace" should look — one clip's
continuation can visibly move faster or slower than the next even though
both were asked for the same pace in the prompt. Fixed on the DC riverside
reel (2026-08-18) with a `"speed"` field per image in the job (a playback
multiplier applied via `setpts` to that image's body segment only, in
`stitch_video.py` — separate from the whip's own `speed`, which compresses
time for the transition itself and is unaffected by this).

**Measure it, don't eyeball it** — the fix that worked was a small
block-matching optical-flow estimate (numpy + scipy only, no `cv2`
needed): sample a handful of patches in the lower two-thirds of the frame
(the ground/path plane — avoid sky, which has no fixed texture to track),
search a small window in the next frame for the best SSD match per patch,
and take the median displacement across patches and across a ~2s window
of frame pairs as that clip's px/sec motion rate. Do this for every clip
*before* picking `cut_at`, then set each clip's `speed` to
`target_px_per_sec / measured_px_per_sec` (target = the median across all
clips, so some clips speed up and others slow down rather than pushing
every clip toward one extreme). Clamp to a sane range (roughly 0.7x-1.4x
held up on this run) — a multiplier outside that starts to look sped-up or
slow-mo rather than "normalized."

**A cruder proxy — plain mean frame-to-frame pixel difference — does not
work.** It was tried first and rejected: a texture-heavy scene (dense leaf
canopy) scored roughly 5x "faster" than a plain paved trail by that
metric, not because the camera was moving faster but because leaf texture
generates more raw pixel change per unit of actual displacement. Any
motion proxy that doesn't track a specific patch's displacement will
confound scene busyness with actual motion speed.

## QC checklist

- [ ] **Every clip scrubbed at full length, 4fps minimum**, not spot-checked
      — the v8 postmortem's exact failure mode (clean at two timestamps,
      fully diverged by the next second) is the single most likely way this
      pipeline ships something wrong.
- [ ] **Each cut lands before divergence, with margin** — re-check the
      trimmed-out frame against the seed photo one more time after trimming,
      not just at the scrub-and-mark step.
- [ ] **No two consecutive clips share the same hallucination direction** —
      if image A and image B both drift toward, say, "adds a person walking
      into frame," back-to-back clips both showing that reads as a pattern
      the viewer notices, even if each individually was trimmed before its
      own worst moment. Re-order or re-roll if so.
- [ ] **The whip transition actually hides the seam** — play the cut at
      normal speed, not frame-by-frame; if the eye can still parse "that's a
      different place" across the cut, tighten the blur/speed ramp rather
      than shipping it.
- [ ] Full 1080x1920 (or target res), no letterbox on any clip (step 1's
      aspect prep, verified after generation not just before).
- [ ] Exposure/color consistent across the whole timeline, not just within
      each clip.
- [ ] **Apparent motion speed matches across clips** — play the assembled
      reel at normal speed, not clip-by-clip; a per-clip pace mismatch that
      looks fine scrubbing one clip in isolation reads as an obvious
      speed-up/slow-down once it's next to its neighbors in context. See
      "Matching apparent motion speed across clips" above.
- [ ] **If using the photo-beat structure**: watch each transition
      specifically for a "stopped" feeling, not just for correctness of
      content — an over-long still hold is easy to miss on a casual watch
      because it doesn't look *wrong*, it just quietly reads as normal
      pacing. See "Alternative: the photo-beat cut" above.

## Cost discipline

Same posture as the carve project's spend rules — state the generation
count (≥ N images, budget for at least one re-roll per clip since the
grounded-window length is a per-image gamble, not a fixed quantity) and get
a go-ahead before spending, price a cheap lite probe before assuming its
behavior matches the standard model's documented constraints, and never
re-generate a whole image's clip to fix a bad *transition* — the transition
step is free ffmpeg work downstream of clips you already own.

## Optional: a stats/route overlay on top

Not part of the core i2v pipeline, but built alongside it on the DC
riverside reel (2026-08-18) and worth keeping: burning a run-tracking
app's stat card and GPS route line on top of the assembled reel, keyed out
of a screenshot of the source app rather than redrawn from scratch (see
`overlay_work/build_overlays_v2.py`). Two findings worth keeping if this
comes up again:

- **A route/track line broken by labels sitting on top of it (mile-marker
  pills, a location badge, a legend) needs its gaps bridged before it
  reads as one continuous path** — color-keying the line out of the
  screenshot (saturated-hue threshold, everything else made transparent)
  leaves it in disconnected pieces wherever a label occluded it in the
  source image. **Bridge strand *endpoints* to each other, never nearest
  pixel to nearest pixel.** The first attempt connected each broken piece
  to whichever other piece's *any* pixel was closest, which sometimes
  attached a bridge to the middle of a long strand instead of its tip —
  invisible as a bug until compared side-by-side against the real map,
  where it showed up as an impossible X-crossing that didn't match the
  source path at all (two genuinely separate, nearby-but-parallel strands
  — an out-and-back route's outbound and return legs — got cross-wired).
  The fix: compute each disconnected piece's two true endpoints (farthest
  pair of points within that piece, via a convex hull), then greedily pair
  up the globally-nearest *endpoints* across different pieces, retiring
  each endpoint once it's used (so no piece can be bridged from its
  middle, and no endpoint feeds more than one bridge). Verify the result
  by compositing it back over the real, un-keyed source screenshot and
  eyeballing it against the actual path — the broken and the wrongly-fixed
  versions both "look plausible" in isolation; only a side-by-side catches
  either.
- **Verify a reconstructed overlay against the source document, not just
  against itself.** The wrong-topology version above passed its own
  internal QC (fully connected, no gaps, rendered cleanly) and only read
  as broken once judged against what it was supposed to represent — the
  same "verify with a different method than the one that produced the
  artifact" principle `ReadME.MD`'s webinar-repurposing section already
  established for extracted video clips applies just as much to a
  reconstructed graphic.

## Open items

Resolved by the first real run (2026-08-15):
- ~~Actual grounded-window length per image on `lite`~~ — scene-dependent,
  often the full 8s; see "Which model" above.
- ~~Whether lite even accepts plain i2v with no `last_frame` at these
  durations/resolutions~~ — yes, 1080p/8s works cleanly.
- ~~Whether lite honors `negative_prompt`~~ — no, it 400s. Fold constraints
  into the positive prompt instead (see "Prompting each continuation").
- Whether the constant gaussian-blur whip sells the transition on real
  footage — **yes on this run's footage**, at the default 0.4s/2.5x/sigma=14
  settings, reviewed via a full-video 2fps contact sheet plus playback; the
  directional/zoom-blur fallback below was not needed here, but this is one
  run's worth of one aesthetic (natural daylight trail scenes) — revisit if
  a future reel's footage doesn't sell it.

Resolved by the second real-run pass on the same reel (2026-08-18):
- ~~Whether per-clip apparent motion speed needs active normalization~~ —
  yes, measurably; see "Matching apparent motion speed across clips."
  Block-matching displacement, not frame-diff, is the metric that worked.
- ~~Whether showing the seed photo itself (instead of hiding the cut) is a
  viable alternative structure~~ — yes, but only with a short (~0.15-0.2s)
  hold; see "Alternative: the photo-beat cut." A long hold trades the
  original "confusing cut" problem for a new "looks stopped" one.
- ~~Whether a bad/ambiguous seed photo can be salvaged by better editing~~
  — no. A motion-blurred, low-information seed produced confusing footage
  under every structure tried (continuous i2v, photo-beat with the seed
  shown first); the fix was dropping that image, not a better edit. Screen
  seeds for legibility before generating (see step 0).

Still open:
- Whether lite's fidelity holds up on scene types other than the
  texture-heavy/architectural ones tried so far (dense foliage, a brick
  corridor, a fenced trail) — the "grounded window is scene-dependent"
  finding above is based on one reel's worth of scenes, not a general model
  characterization. Open geometry (water, sky, wide plazas) is untested and
  the standard-model "3-5s" figure may still be the safer prior there.
- Whether the directional/zoom-blur upgrade is ever actually needed, now
  that the constant-blur whip has a confirmed real-footage pass.
- **Google Drive folder downloads via `gdown --folder` silently drop
  duplicate filenames.** If a shared folder contains two different files
  that happen to share an exported filename (seen on the first real run: two
  Drive items both named `photo-2236_singular_display_fullPicture.JPG`),
  gdown downloads both but the second silently overwrites the first on disk
  — no warning, no error, just one file quietly missing. Diff the folder's
  file *count* against what `gdown --folder` reports processing, not just
  what ends up on disk, if a job depends on every source image surviving.
- **Some iOS "Spatial Scene" photos are actually a ~48-frame HEIC image
  sequence, not a single still**, and both the file extension (often
  `.JPG` on a Drive export) and `ffprobe`'s default stream selection hide
  this — `ffprobe`/`ffmpeg -i` by default surfaces a low-res (512x512)
  "dependent" thumbnail stream, not the real content. Symptom: an image
  that looks like meaningless motion-blur at low res is actually a short
  burst of real, distinct frames (confirmed by extracting with `-map 0:v
  -vsync 0` and diffing frame hashes — genuinely different content per
  frame, not duplicates). Two options once detected: decode it as real
  footage directly (free, no hallucination risk, but native resolution is
  often far below the seed images around it, e.g. 512x512 needing a heavy
  crop+upscale to hit 1080x1920) or treat frame 1 as an ordinary single-image
  seed for Veo i2v like any other shot (consistent look with the rest of
  the reel, costs a normal generation, but seeds from what may be a
  motion-blurred frame). Ask which the user wants — it changes both cost and
  visual consistency, not just a technical detail.

## What's actually verified vs. not

**2026-08-15, synthetic clips**: `stitch_video.py`'s `generate`/`sheet`/
`assemble` subcommands, the `cut_at` gate, and the trim → speed-ramp → blur
→ xfade → concat pipeline were all exercised end-to-end against synthetic
`ffmpeg testsrc` clips — this validated the mechanics (correct segment
durations, valid playable 1080x1920 h264 output, the gate correctly
refusing to assemble until every image has a `cut_at`) but said nothing
about real footage or real API behavior. One bug was caught and fixed this
way: `-t` was originally placed after `-i` in the trim command, which
ffmpeg parses as an *output* duration cap rather than an input trim —
invisible until the whip segments were actually probed and came back at
their pre-speedup length instead of compressed. Worth remembering as a
reason to probe durations after any future change to the ffmpeg command
construction, not just trust that the command "looks right."

**2026-08-15, real run**: full pipeline run start-to-finish on real
`veo-3.1-lite` output — a 6-image DC riverside run reel, downloaded from a
shared Google Drive folder via `gdown`, generated, scrubbed, assembled, and
delivered at 1080x1920/28.4s/silent. This is the run that produced every
finding in "Which model," the QC finding under step 4, and the two Open
Items about `gdown` and iOS Spatial Scene photos above. Not yet exercised
in this real-run pass: the directional/zoom-blur transition fallback (not
needed — constant blur sold it), a job requiring `veo-3.1-fast` or
`-standard` mid-reel for a hero shot, and any scene type outside
foliage/architectural corridors (see "Still open" above).

**2026-08-18, same reel, second edit pass**: iterative re-cutting of the
already-generated DC riverside footage (no new generations — same raw
clips, re-trimmed/re-paced/re-composited across several rounds against
user feedback), delivered at 1080x1920/8.9s/silent. This pass is where the
`"speed"` field, the block-matching motion-measurement recipe, the
photo-beat alternative structure (and its hold-duration finding), the
"drop a bad seed rather than try to edit around it" finding, and the
route-overlay endpoint-bridging technique all came from. Each fix was
driven by a specific, concrete complaint against the previous render
(motion pace mismatched, a still-blurry seed read as confusing even
seed-first, transitions looked like the subject stopped moving, a
reconstructed map overlay didn't match the source) rather than a
general-purpose pass — worth noting because every one of those problems
was invisible until judged against the *specific* symptom, not caught by
the standing QC checklist alone. The checklist above has been updated with
the two items that generalize (motion-speed matching, photo-beat hold
length); the seed-legibility and overlay-bridging findings are process
notes (step 0 and "Optional: a stats/route overlay") rather than
checklist items since they're pre-generation and one-off-asset concerns
respectively, not properties of the assembled reel itself.
