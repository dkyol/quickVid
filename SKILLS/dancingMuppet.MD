# dancingMuppet — a character seed image + a song → that character dancing to it

A **plan, not yet a validated runbook.** Nothing in this file has been run
end-to-end yet; the model IDs and constraints below were probed live against
the connected Artlist account (2026-08-13) and are real, but every "this
should work" claim is a prediction until the first build. Mark what breaks
in-place, dated, the way `imageGenSkill.MD` does — that file's value is its
corrections, not its first drafts.

## PLATFORM MIGRATION, 2026-08-13: Artlist → Atlas Cloud direct (OpenRouter
## tried first, rejected same day — audio input isn't reachable there)

The user is dropping the Artlist MCP integration and calling Seedance 2.5
directly through **Atlas Cloud's reference-to-video API**. This changes the
*mechanics* of Path A below but not (as far as tested) the *model behavior*
findings — the face-fix prompt, the amplitude-fix prompt, the "dancing"
body-plan conflict, and the beat-lock result were all properties of Seedance
2.5 itself, not of Artlist's wrapper, so they should still apply. Everything
in this file that calls `mcp__artlist__*` tools is superseded; use this
section's mechanics instead.

**Why Atlas Cloud and not OpenRouter — resolved, not a live question
anymore.** OpenRouter was tried first (same day). Its unified video schema
(`model`, `prompt`, `duration`, `resolution`, `aspect_ratio`, `generate_audio`,
`frame_images`, `input_references`, `seed`, `provider.options.<slug>.parameters`)
has no field for passing audio as a reference or timing driver — confirmed
**definitively**, not just from docs but from `GET /api/v1/videos/models`'s
live response for `bytedance/seedance-2.5`: `allowed_passthrough_parameters`
is `["watermark","req_key","output_format"]` (no audio param, at all), and
`pricing_skus` has `video_tokens_with_video_input` but no
`video_tokens_with_audio_input` — if audio were billable as an input there'd
be a SKU for it. Atlas Cloud's **reference-to-video** endpoint (specifically
that endpoint — its plain `image-to-video` endpoint does NOT support audio
references either, same limitation as OpenRouter) exposes `reference_audios`
as a first-class field, confirmed from its own docs
(`atlascloud.ai/models/bytedance/seedance-2.5/reference-to-video`). Use the
reference-to-video model slug below, not the image-to-video one — the two
are genuinely different endpoints with different capabilities on this
platform, easy to mix up.

**RESOLVED, 2026-08-14 — `reference_audios` genuinely drives beat-locked
motion on Atlas Cloud, confirmed not just claimed.** Two 5s probes at
720p were inconclusive (too few motion cycles — 5s ≈ 3 cycles at song
tempo — for `motion_period.py`'s autocorrelation to be trustworthy either
way). A full 30s generation resolved it: measured dominant motion period
**0.5417s** vs the song's beat period **0.5457s** — a **0.7% match**,
essentially identical to Artlist's original Experiment 0 result (also
0.7%). With 30s of data (~14 cycles) this measurement is robust. Treat this
as settled for Seedance 2.5 R2V+Audio specifically — the model itself
listens to the audio; that was never platform-specific, only the *plumbing*
to reach it differed between Artlist/OpenRouter/Atlas Cloud.

**Other things confirmed on this same 30s run, worth carrying forward:**
- **Body plan held far better than on Artlist** — one paw, small foot nubs,
  no legs/knees for the large majority of the clip (vs. Artlist's
  consistent full-clip two-arm/two-leg growth on "dancing" prompts). One
  caveat: a second arm-like appendage briefly appeared around the ~18-29s
  "paw raised high" dramatic-moment stage — not perfect, but a real
  improvement. Unclear whether this is genuinely a better-behaved
  provider/routing path or partly luck across a handful of runs; treat as
  encouraging, not proven.
- **Face-fix and amplitude-fix prompts transfer directly** — same wording
  that worked on Artlist worked here, across all three Atlas Cloud runs.
- **`@Image1` / `@Audio1` / `@Video1` citation syntax is authoritative for
  this platform**, confirmed straight from the live JSON schema
  (`static.atlascloud.ai/model/schema/bytedance-seedance-2.5-reference-to-video.json`),
  not inferred from blog posts.
- **Audio format matters**: Atlas Cloud only accepts `mp3`/`wav` for
  `reference_audios` — an `.m4a` (AAC in an MP4/MOV-family container) gets
  rejected with `InvalidParameter.FormatUnsupported: Unsupported audio
  format: mov`. Convert with ffmpeg (`-c:a libmp3lame`) before inlining.
- **Response is nested under a `data` key**, and the poll endpoint returns
  the same shape — `body["data"]["id"]`, `body["data"]["urls"]["get"]` for
  the poll URL, `body["data"]["outputs"]` (array of URLs) once
  `status: "completed"`. Easy to miss if assuming a flat response.
- Working reference scripts from this session:
  `work/dancingMuppet/atlascloud_probe.py` (short probe) and
  `work/dancingMuppet/atlascloud_full30.py` (full-length run) — both do the
  base64-inline + submit + poll + download dance end to end.

**Mechanics, confirmed from Atlas Cloud's docs:**
- **Auth**: `Authorization: Bearer $ATLASCLOUD_API_KEY` header (env var now
  in `.env`), not an MCP tool call.
- **Model slug**: `bytedance/seedance-2.5/reference-to-video` — NOT
  `bytedance/seedance-2.5/image-to-video`, which lacks audio references.
- **No upload/confirm dance.** Reference fields (`reference_images`,
  `reference_videos`, `reference_audios`) take URLs, base64, or asset
  references directly in the request body — no separate upload-then-confirm
  round trip like Artlist required.
- **Reference limits**: up to 30 `reference_images`, 10 `reference_videos`,
  10 `reference_audios` — combined audio+video reference duration ≤30s per
  request, each audio clip ≤30s and ≤15MB.
- **Submit**: `POST https://api.atlascloud.ai/api/v1/model/generateVideo` →
  returns a prediction id.
- **Poll**: `GET https://api.atlascloud.ai/api/v1/model/prediction/{id}`
  until `status` is `completed`, `failed`, or `timeout`; `outputs` array
  holds the result URL(s) once completed.
- **No `confirmation_required` cost gate**, same situation as OpenRouter —
  submitting spends money immediately. The cost-discipline rules later in
  this file (state the price, get a go-ahead before every spend) are the
  only safety net; compute cost from the flat per-second rate below and
  confirm with the user before every `POST`.
- **Pricing is NOT flat across resolutions — measured, corrects an earlier
  wrong assumption.** The model catalog (`GET /api/v1/models`) lists a single
  `base_price: 0.134` ($/second) with no visible per-resolution breakdown,
  which reads as if it's flat regardless of resolution. **It is not.** A
  measured 30s generation at `1080p-esr` actually cost **$16.25** (the
  completed prediction's `price` field) — an effective **$0.542/second /
  $32.50 per minute**, about **4x** the $0.134/s ($8.04/min) base rate
  implied by the catalog. There is no documented or discovered endpoint that
  exposes the real per-resolution rate up front (tried `/account/balance`,
  `/billing`, `/usage`, all 404); the `price` field in the COMPLETED
  prediction response is the only confirmed source of truth. Quote the
  catalog's `base_price` as a 720p/480p estimate only, and warn explicitly
  that ESR resolutions (`720p-esr`, `1080p-esr`, `1440p-esr`, `4k-esr`,
  `1080p-esr & 60fps`) are unconfirmed
  and were measured roughly 4x higher at the one tested tier.
- **The ESR resolutions are upscales, not native higher-resolution
  renders.** Confirmed from the live schema: "480p and 720p are native
  Seedance outputs... 720p-esr enhances a 480p source to 720p, while
  1080p-esr, 1440p-esr, 4k-esr, and 1080p-esr & 60fps enhance a 720p
  source." Requesting `1080p-esr` does not generate more real detail than
  `720p` — it generates at 720p natively, then runs Atlas Video Enhance on
  top, at roughly 4x the cost. Prefer generating at native 720p and
  upscaling only the final locked cut afterward, UNLESS the in-generation
  upscale is specifically wanted (e.g. it may denoise/sharpen in ways a
  generic upscaler doesn't — untested, no comparison run yet).
- **No built-in monthly limit**, same as OpenRouter — pay-as-you-go, no
  stated cap. If a monthly budget matters, it's self-imposed; check the
  user's Atlas Cloud console for any limit they've set rather than assuming
  one exists, and track cumulative spend manually across a session.

## What this produces

A vertical (9:16) short of **one character** — a muppet/puppet, but the
pipeline is character-agnostic — dancing to **a specific song**, on beat, for
however long the song section runs. Inputs:

| input | required | notes |
|---|---|---|
| **seed image** of the character | yes | the identity anchor; everything else derives from it |
| **song** (audio file) | yes | drives tempo, and — on the audio-reference path — the model's actual timing |
| **choreography direction** | no (defaults) | a named dance, a written move list, or a reference dance video — see "Directing the choreography" |

## What carries over from `golfFlyoverVantage.MD` (and why)

That file's hard-won lesson is not about golf. It's this:

> A video model gets **only the still frame(s) and the text prompt**. Nothing
> else about your intent reaches the generation. Past roughly 4-5 seconds of
> unconstrained span it stops extrapolating from the real pixels you gave it
> and starts generating from its own priors — and it has no persistent 3D
> scene representation to keep the subject consistent across that gap.

For a flyover that showed up as invented bunkers. **Here it shows up as
identity drift**: the muppet's fur color shifts, the felt turns plush, an eye
migrates, a hand grows human fingers, the puppet gains a knee it doesn't
have. Same root cause, different symptom. So the same three structural rules
apply, restated for this job:

1. **The seed image is the only thing holding identity.** Every shot starts
   from it or from a hand-verified derivative of it — never from the tail
   frame of a previous generation (chain drift, `imageGenSkill.MD`'s
   superseded chained-montage section measured this: one bad link poisons
   everything downstream).
2. **Don't ask one generation to cover a long unconstrained span — EXCEPT on
   Seedance 2.5 R2V, which is a documented exception.** `carvingSkill.MD`'s
   "why a montage" argument was written against Veo and other models without
   a persistent scene representation. ByteDance's own Seedance 2.5 docs claim
   the opposite for THIS model specifically: single-pass 30s generation with
   locked identity is the intended use, not a workaround. See "Single-pass
   30s" under Step 4/Path A below — confirmed by research 2026-08-13, not yet
   confirmed by a generation. Rule 2 still applies at face value to every
   other model in this file (Path B, Path C, Veo).
3. **Draft cheap, then spend — but "cheap" means duration, not resolution,
   on this character.** 480p is a real setting on every model below, but the
   user has explicitly ruled it out: "480 does not work ever, it looks bad
   don't suggest it" (2026-08-13). **Never propose or default to 480p for
   this project.** Draft with a short `duration` at 720p+ instead of dropping
   resolution — validate the character survives motion at 720p on a few
   seconds before paying for a full-length take.

What does **not** carry over: the vantage file's geography/layout-reference
machinery (Earth Engine, Overpass, rotated map crops) is irrelevant here —
there is no real-world ground truth to preserve, only the character's own
identity.

---

## ▶ Let's get started

0. **Ask for the media explicitly — do not reuse whatever is sitting in
   `media/` from a previous session.** Get the seed image path AND the song
   file path from the user by name, every time. (Standing rule across every
   reel skill in this repo.)
1. **Confirm the four inputs**: character seed image, song file, which
   **section** of the song (see Step 2 — a 3-minute track is not the
   deliverable; a 10-20s hook is), and the choreography direction (named
   dance / written moves / reference video / "you pick").
2. **Read the song, free** (Step 2 below) — BPM, the section boundaries, the
   downbeat grid. This is a no-API step and it determines the shot list.
3. **Prep the seed** (Step 3) — 9:16, full body in frame, room to move.
4. **Pick the path** (Step 4) — audio-driven, motion-transfer, or
   prompt-only. This is the real decision in this skill.
5. **Run Experiment 0** (below) — one cheap 480p generation that settles which
   architecture the rest of the build uses. Scrub it full length, confirm the
   character survives (Step 6's QC). State the generation count and get a
   go-ahead before anything beyond that.
6. **Generate the remaining shots**, each anchored on the seed.
7. **Cut to the beat grid** from Step 2 and lay the real song under it
   (Step 7) — the music is added in the edit, not trusted to the model.
8. Deliver to `final/dance_<character>_<song>_<stamp>.mp4`.

---

## Step 2 — read the song first (free, no API, do this before anything else)

The beat grid is the skeleton of the whole edit. Get it before generating,
because it decides how many shots you need and how long each one is.

```powershell
# section boundaries / where the hook is — look at the waveform loudness
tools/ffmpeg.exe -i song.mp3 -af "ebur128=peaklevel=true" -f null - 2>&1 | Select-String "M:"

# cut the section you actually want, and work only with this from here on
tools/ffmpeg.exe -y -ss 48.0 -t 15.0 -i song.mp3 -c:a aac work/hook.m4a
```

For BPM/downbeats, `librosa` in the `api` conda env
(`C:\Users\DKYLE\.conda\envs\api\python.exe`) gives an exact grid:
`librosa.beat.beat_track` → tempo + beat frame times. Write the beat times to
a file; Step 7's cut points come straight from them.

**Rules that come out of this step:**
- **Cut on downbeats, not on even slots.** Same lesson as every other reel in
  this repo (`carvingSkill.MD` Step 7) — evenly-spaced cuts read synthetic.
  Here you get the correct rhythm for free from the music.
- **Shot lengths should be whole bars** (4 beats at 120bpm = 2.0s). Pick shot
  durations from the grid, then round the model's `duration` setting UP to
  the nearest available value and trim down in the edit.
- **A 15s hook at 120bpm is ~7.5 bars.** That's 4-6 shots, not one 15s
  generation — even though Seedance will happily accept `duration: 15`.

## Beat sync is three separate problems — read this before picking a path

Any of these models will produce a puppet in motion. What separates "dancing
to *this song*" from "moving while music happens to play" is beat lock, and
it decomposes into three problems that are **not** equally hard:

| | what it is | how hard | who solves it |
|---|---|---|---|
| **cut sync** | edits land on downbeats | free, deterministic | ffmpeg + Step 2's grid |
| **accent sync** | one big move (arm throw, spin, drop) lands on a named beat | medium | end-frame pinning, or a retime |
| **continuous sync** | the whole body pulses at tempo throughout | hard | an audio-driven model, or a retime |

**Most real dance edits run almost entirely on cut sync, plus two or three
accents.** That reframes the whole job: we may not need the model to be
musically aware at all — which is fortunate, because whether it is remains
unmeasured (Experiment 0 below).

**The retime is the cheap universal fix, and it's the strongest single idea in
this file.** If a generated clip contains *periodic* motion of period P, and
a bar is B seconds, then `setpts=(B/P)*PTS` makes the motion exactly
bar-locked. Under roughly 15% correction this is visually invisible. It turns
"the model can't count" from a model problem into arithmetic. It costs
nothing, and it works on clips that are already generated and paid for.

> The retime destroys any generated audio's pitch/timing — irrelevant here,
> because the model's audio is a scratch track for sync-checking only and the
> real song goes on in the edit (Step 7).

## The bar-loop architecture — SUPERSEDED for Path A on Seedance 2.5, see below

**Correction, 2026-08-13, before any loop generation was run:** the premise
below — that Seedance 2.5 needs to be chopped into short clips because it
can't hold identity past ~4-5s — was inherited by analogy from
`golfFlyoverVantage.MD`, which measured that ceiling on a **different model**
(Veo). It does not hold for Seedance 2.5 R2V. ByteDance's own docs and fal.ai's
model docs state Seedance 2.5 is purpose-built for **single-pass, 30-second,
identity-locked generation** — "no stitching, no scene-cut splicing, no
visible seams" — and that reference audio is generated jointly with video in
the same latent space specifically so it can act as a real timing signal, not
just decoration. The 30s ceiling exists for narrative continuation, not as a
constraint to route around. See "Single-pass 30s — the corrected default
shape" below. The loop architecture may still be worth using for OTHER
reasons (see its remaining advantages at the bottom of this section) but it
is no longer justified as an identity-drift workaround on this model — do not
default to it for that reason.

Don't generate 15-30s of unique dancing. Generate **one seamless 1-2 bar loop
per look**, and build the reel out of loops.

1. Seedance 2.5 (group 515) exposes `image_url` + `end_frame`. Set the end
   frame equal to the start frame → the clip loops cleanly.
2. Measure the clip's actual motion period (`motion_period.py`, below), then
   `setpts`-stretch it so the period is exactly one bar. At 120bpm a bar is
   2.0s; a clip whose cycle runs 2.3s stretches by 0.87 and locks.
3. Repeat each loop 2-4x, with a **different punch-in/crop per repeat** so it
   doesn't read as a literal loop.

Reasons this shape can still be worth choosing (none of them "identity drift"
anymore):

- **It's how dance actually works** — 8-counts, repeats, variation. The
  repetition is the genre, not a compromise or a cost-saving hack.
- Cutting between several generations gives editorial control (varied crops,
  punch-ins, pacing) that a single continuous 30s take doesn't offer for
  free.
- If the single-pass 30s approach is tried and DOES show drift on this
  model/character (unmeasured either way as of this writing), this is the
  fallback, and the credit cost is comparable either way — see the open item
  below.

Consequence for Step 3, if this shape is used: **the seed image should be a
"count 1" pose** — the pose the loop both starts and ends on.

## Single-pass 30s — the corrected default shape

Generate the **entire 30s hook in one `generate_video` call**: the single
seed image + the full 30s audio track as the two references, `duration: 30`,
`generate_audio: true`. Use fal's documented technique for long single-pass
videos — divide the take into **stages**, each with one primary state change,
described with approximate (non-frame-exact) time ranges in the prompt:

> "Bars 1-2 (0-4.5s): weight shifts side to side... Bars 3-4 (4.5-8.9s):
> leans and rocks the other way... " etc., one stage per bar-pair from the
> Step 2 beat grid.

Cost scales with output duration (token formula is roughly linear in
seconds), so a single 30s 480p call should land in the same total-credit
neighborhood as several shorter shots covering the same span — confirm
against the actual `price` the tool returns before assuming. The payoff over
chopping into shots: no stitching, no cut-point framing mismatches between
generations (a real, separately-documented failure mode in this repo), and
the model's own claimed strength — continuous identity — actually gets used
instead of engineered around.

## Step 3 — prep the seed image

The single biggest quality lever, exactly as in every other skill here.
Check, before spending anything:

- [ ] **Native 9:16.** A 1:1 or 4:3 seed produces a letterboxed output on
      most of these models (confirmed repeatedly on the Veo path in
      `carvingSkill.MD`; assume it holds here). **ASK THE USER for a native
      9:16 version of the seed before spending anything on an outpaint —
      don't default to extending the canvas yourself.** Measured 2026-08-13:
      extending a 5:6 seed to 9:16 via Artlist's `generate_image` (Nano
      Banana Pro Edit, group 117) produced a clean-looking still, but the
      downstream Path A video generation from it was **not usable** — wasted
      cost, confirmed by the user. Only fall back to the image-edit outpaint
      (pass the seed as input, prompt it to extend the
      background/floor without altering the character, `aspect_ratio: "9:16"`)
      when the user genuinely has no better-cropped source to give you.
      Artlist has no dedicated outpaint tool — this is a general image-edit
      call, which may be part of why it under-delivers here.
- [ ] **Whole body visible, with headroom and floor.** A head-and-shoulders
      crop cannot dance — the model will either invent a body (identity
      drift, immediately) or just bob the head. If only a portrait exists,
      generate a full-body version FIRST as an image edit and treat that as
      the seed.
- [ ] **Space around the character to move into.** A tightly-framed subject
      forces the model to either clip limbs at the frame edge or push the
      camera; both look wrong.
- [ ] **Neutral, planted starting pose.** Standing, arms down, facing camera.
      A seed already mid-gesture biases every take toward repeating that one
      gesture.
- [ ] **The material reads correctly at full resolution** — felt is felt,
      seams visible, fibers not plastic. Open it at native size, not a
      thumbnail (`carvingSkill.MD` Step 4's measured lesson: thumbnail QC
      passed images that were visibly wrong at full res).

**Optionally build an end frame too.** Seedance 2.5 (group 515) exposes
`frameInput` with `hasEndFrame: true` — start `image_url` + `end_frame`. Two
uses here, both worth it:
- **A seamless loop**: end frame = the start frame, so the clip loops
  cleanly for social.
- **Pinning a specific pose on a specific beat** — the same
  hand-built-end-frame technique that fixed carving shots in
  `carvingSkill.MD` Step 5. If a move must land on the downbeat, pin its
  final pose as the end frame instead of describing it and hoping.

---

## Step 4 — which path (this is the actual decision)

Three real paths, probed live on the connected Artlist account 2026-08-13.
Pick by what the user gave you for choreography.

### Path A — audio-driven: Seedance 2.5 R2V + Audio ← **default**

`[ByteDance] - Seedance 2.5 - R2V - Audio` — modelId **3002** (720p) /
**3013** (480p), modelGroupId **515**.

This is the path the user's instinct pointed at, and it's the right default:
it's the only one that takes the character image **and the actual song audio**
in the same call, so timing comes from the music itself rather than from a
text description of the music.

Mechanics (from `get_model_config` on group 515 — this is the authority, not
this file):
- It's `multi-to-video`: pass `input` as an **array** —
  `[{assetId: <image>}, {assetId: <audio>}]`. Images via `upload_image`,
  audio via `upload_audio`. Pass the audio file directly; do **not**
  transcode or extract anything first.
- `settings`: `aspect_ratio: "9:16"`, `duration` 4-30s (default 10),
  `resolution` **480p or 720p only** (no 1080p on this group — see upscaling
  below), `generate_audio` (default on).
- `generate_audio: true` is what makes it treat the audio as a driver rather
  than decoration. Set it explicitly.
- Start/end frame interpolation is available on the same group
  (`image_url` + `end_frame`) — see Step 3.
- **No `negative_prompt` key exists on this group.** The vantage/carving
  skills lean on negative prompts for their guards; that tool is not
  available here. Constraints have to live in the positive prompt, which is
  weaker — budget for more re-rolls than those skills needed.

**Cheap draft tier for this path**: `Seedance 2.0 Mini` (group **416**,
`freeGeneration: true`, R2V/I2V/T2V at 480p/720p). Free generations on the
account read **0 remaining** as of the probe, so "free" may mean "cheapest",
not "no cost" — check `get_balance` before assuming.

### Path B — motion transfer: Kling 3.0 Motion Control

`Kling 3.0 Motion Control` — Pro modelId **2292**, Standard **2293**,
modelGroupId **368**. `video-to-video`: requires BOTH a driving `video_url`
and the character `image_url`.

**Use this when the user names a specific real dance** (a TikTok routine, the
Charleston, a music-video sequence) **and a reference clip of it exists.**
Transferring motion off a real video is a fundamentally smaller ask than
synthesizing a named dance from its name — the same "real pixels beat
synthesis" finding that resolved the golf vantage skill.

**Retime the driving video to the song's BPM BEFORE transferring it.** Then
sync is exact by construction rather than by hope — this is the one path that
guarantees beat lock instead of approximating it, and it's the fallback if
both the audio path and the retime disappoint. Same `setpts` arithmetic as
above, applied to the input instead of the output.

Caveats to expect: a puppet's proportions are not a human's, and motion
transfer onto a non-human body plan is where this will most likely break
(limbs bending where the puppet has no joint, a rod-arm doing something a rod
arm can't). QC specifically for that. `generate_audio` toggle exists here
too; `resolution` is `pro`/`standard`, not a pixel count.

If the Kling result fights the puppet body plan, the fallback is Path A or a
hand-timed cut in Step 7 — stay inside Artlist's catalog rather than crossing
to a different platform/billing pool.

### Path C — audio-driven performance: Omnihuman 1.5

`Omnihuman-v1.5` — modelId **2377**, modelGroupId **389**. Requires
`image_url` + `audio_url` (both mandatory), 720p or 1080p, and it's flagged
`freeGeneration: true`.

Built for audio-driven **performance** (singing, speaking, body motion in
time with audio) rather than free-form dance. **Use it when the muppet should
be singing the song, mouth moving to the lyrics**, not just dancing to it.
It's the only path here that reaches 1080p natively, and it's the cheapest —
so it's also a legitimate first probe to see whether the character survives
any motion at all before committing to Path A.

### Not the right tool here

- **Veo 3.1** (groups 114/115/376) — the workhorse everywhere else in this
  repo, but its audio is *generated*, not *driven*. It cannot dance to a
  supplied song; it'll invent its own soundtrack and its own tempo. Use it
  only for a non-dancing beat (an intro hold, a reaction shot).
- Anything text-to-video. The seed image is the identity anchor; a T2V shot
  in the middle of the reel is a different character by definition.

---

---

## Experiment 0 — the decisive probe (run this before designing the reel)

**One 480p, ~5s Seedance 2.5 R2V+Audio generation** — seed image + a few bars
of the hook, `generate_audio: true` — settles the only question that changes
the architecture:

> Does the audio reference actually drive **dance timing**, or does it mainly
> serve lipsync/ambience?

The config proves the model *receives* the audio. It does not prove the body
moves on the beat. Those are different claims and only a generation
distinguishes them.

**How to read the result** — don't eyeball it, measure it. Run
`motion_period.py` on the clip and compare the dominant motion period against
the bar length from `beat_grid.py`:

- **Period ≈ the bar (or a clean half/quarter of it)** → the model is
  musically aware. Pass the song on every shot, let it carry continuous sync,
  and use the retime only to clean up residual error.
- **Period unrelated to the bar** → **the model never hears the music.** Build
  on bar-loops + retime + cut sync, and the song exists only in the edit.
  Honestly this path is *more* controllable, and it is the one to expect —
  treat it as the default assumption until the probe says otherwise.

Either way the probe also answers, for free: does the character survive
motion at all, where does identity drift start (note the timestamp), and does
the puppet body plan hold. Do not design the shot list before running it.

## Directing the choreography

The user can specify the dance three ways. **These are not equally
reliable** — say so when they choose, rather than accepting a named dance and
quietly delivering something generic.

**1. Named dance** ("the moonwalk", "the floss", "a Charleston").
Works for dances with heavy training-data representation, degrades to generic
bouncing for anything niche, regional, or recent. There is no way to know
which case you're in except by generating one draft and looking. **Always
draft this at 480p first.** If the name doesn't land, fall back to (2) or (3)
rather than re-rolling the same name with more adjectives — that's the
failure loop `golfFlyoverVantage.MD` documented twice.

**2. Written move list, mapped to the beat grid.** The most controllable
prompt-only option, and the one to default to when no reference video exists.
Write it as timed beats, not as a vibe:

> "Bar 1: steps side to side, weight shifting, arms swinging loose at the
> sides. Bar 2: both arms raise overhead on the downbeat and wave. Bar 3:
> spins once to the left and returns facing camera. Bar 4: leans back,
> shoulders shimmying, holds."

One move per bar. Anything needing two sentences is two shots.

**3. Reference dance video** → Path B. The most reliable by a wide margin
when a clip exists. If the user wants an exact routine, ask for the clip
rather than trying to describe it.

**4. "You pick"** — default to a simple, high-amplitude, repetitive groove:
weight-shift side step, arm swings, one spin, one hold. Repetitive motion is
also what survives being cut to a beat grid; intricate footwork does not
read at 9:16 on a phone anyway.

### Prompt scaffolding for a muppet specifically

Puppets have their own failure modes, distinct from the carving skills'
"don't render a living animal" guard. State the ones that matter as positive
descriptions (no `negative_prompt` on Path A):

- **Material identity**: "felt and fleece puppet, visible stitched seams,
  fuzzy fiber texture, plastic googly eyes" — models drift felt → plush →
  CGI-fur over the length of a clip.
- **Body plan**: "arms are soft and rod-controlled, they swing and bend
  smoothly along their whole length without a human elbow joint; the puppet
  has no visible knees." This is the single most muppet-specific instruction
  in the file — the default prior is a human skeleton. **Measured weak
  against the word "dancing" specifically, 2026-08-13** — see the "Dancing
  pulls this character toward a human body plan" open item below. On a
  limbless/one-paw character this instruction was overridden twice in a row
  (with and without a video reference, at both 480p and 720p) once the
  character was asked to dance. It may hold better on a puppet with
  rod-arms (this section's original target) than on a truly limbless blob —
  untested which body plan this instruction actually works for.
- **The mouth**: for a dancing (not singing) shot, "the mouth stays closed";
  for a singing shot use Path C rather than describing lip movement.
- **Camera**: "locked-off camera, the puppet stays centered in frame, camera
  does not pan or zoom." Every shot is an independent generation with no
  shared camera lock, so framing drifts between shots and reads as the
  subject jumping across cuts — measured on the carving reel, and it's worse
  here because the subject is *supposed* to be moving.
- **Identity**: "the puppet's colors, proportions, and face never change."

---

## Step 6 — QC: scrub every clip full length before promoting it

Non-negotiable, and for the same measured reason as `carvingSkill.MD`
Step 6: a clip can be perfect at two hand-picked timestamps and fall apart in
between.

```powershell
tools/ffmpeg.exe -y -i shot_01.mp4 -vf "fps=4,scale=180:320,tile=8x5" `
  -update 1 -frames:v 1 scrub.png
```

**4fps, not 1fps** — a dance move happens inside a beat, and a 1fps sample
walks straight past it.

Checklist:
- [ ] **Identity holds to the last frame** — same colors, same face, same
      proportions at t=end as at t=0. Compare the last frame against the seed
      image side by side, not against the clip's own first frame.
- [ ] **Where does it break?** Note the timestamp of first drift on every
      clip. If it's consistently ~4-5s, that's the extrapolation limit
      showing up again — shorten every shot below it and cut more often.
      This measurement is the most valuable thing the first build produces;
      write the number into this file.
- [ ] **Body plan intact** — no human knees/elbows, no extra fingers, no limb
      passing through the torso, arms still attached.
- [ ] **The motion is actually on beat.** Play the clip against the hook
      audio. On Path A the model should land accents on the downbeats; if it
      doesn't, the audio reference isn't doing its job and the honest fallback
      is Path B or a hand-timed cut in Step 7.
- [ ] **Amplitude** — is it dancing, or swaying? Low-amplitude "polite"
      motion is the most common i2v failure across every skill in this repo
      (carving got "tentative poking" from the same underlying tendency).
      Prompt the finished, committed motion, not the activity.
- [ ] **Framing consistency across shots** — hstack one frame from each shot
      at the same scale and check the puppet is the same size and vertical
      position. Fix with a per-shot crop offset in the edit, not by
      regenerating (`carvingSkill.MD` Step 7 — free fix, and the naive
      center-crop makes it worse, not better).
- [ ] Full 1080×1920, no letterbox.

## Step 7 — assembly

- **Lay the real song under the finished cut.** Whatever audio the model
  returns is a scratch track for sync-checking only — never the deliverable.
  Mute the generated audio (or duck it far under, if it has useful foley) and
  use the original file.
- **Cut on the Step 2 downbeats.** The cut list is already written; use it.
- **Vary the shot lengths within the grid** — 2 bars, 2 bars, 1 bar, 1 bar,
  4 bars reads as an edit; eight identical 1-bar cuts reads as a metronome.
- **Small timing corrections are free**: `setpts` can nudge a clip a few
  percent to lock a move onto a beat. Do that before regenerating anything.
- **Upscale last, if at all.** Path A caps at 720p; `Topaz Video Upscale`
  (modelId **1044**) or `Topaz Upscale - Starlight 2X` (**2610**) take it up.
  Only run this on the final locked cut, never on individual takes.
- Loudness pass to -14 LUFS for social.

## Tooling — what already exists, what has to be written

Probed on this machine 2026-08-13. All the missing pieces are small, free,
and involve no API calls.

**Already solved — reuse, don't rebuild:**
- **`build_reel.py` is the entire assembly layer.** It takes per-shot slot
  durations, muxes a `source_audio` track under the whole reel, crossfades
  (set `crossfade: 0` for hard cuts), blur-fills to 1080x1920, and
  Ken-Burns's any stills. Fill `seconds` per shot from the bar grid, point
  `source_audio` at the hook, done. No new assembly tooling is needed.
- `ffmpeg.exe` / `ffprobe.exe` in `tools/`.
- `numpy` and `scipy` are installed in the `api` env
  (`C:\Users\DKYLE\.conda\envs\api\python.exe`).

**Needs writing — three small scripts:**

| script | job | notes |
|---|---|---|
| `beat_grid.py` | song → BPM, beat times, bar times as JSON | **`librosa` is NOT installed** (nor `soundfile`). Not required: ffmpeg decodes to raw PCM, spectral flux via `scipy.signal.stft`, autocorrelation for tempo, phase alignment for the grid. ~80 lines. Installing librosa is the alternative if preferred. |
| `motion_period.py` | clip → dominant motion period, for the retime | Pipe rawvideo grayscale frames from ffmpeg into numpy, mean-abs frame diff → autocorrelate. **`cv2` is NOT installed and is NOT needed** for this. ~50 lines. |
| `beat_lock.py` | apply the `setpts` stretch, emit N repeats with per-repeat crop variation | ~60 lines. |

**A constraint that shapes the workflow: there is no Artlist API key in
`.env`** (only `ELEVEN_API_KEY`, `XAI_API_KEY`, `KLING_*`,
`EARTHENGINE_PROJECT`, `GOOGLE_API_KEY`). So **Artlist generation is MCP-only
— it happens in conversation, call by call.** There is no batch
`dance_reel.py --job <file>` equivalent to `veo_carve.py` unless an API key
turns up. That's fine at 4-6 generations, which the bar-loop architecture is
designed to stay within; it would hurt badly at 30. If this pipeline gets
used repeatedly, getting an Artlist API key is the first thing to fix.

## Cost discipline

Same rules as every skill in this repo, and they exist because ~$200 went on
a 12-second reel once:

1. **Never call a paid API to check whether the paid API works.** Infer from
   the last real error, or `get_balance`.
2. **`generate_video` may return `confirmation_required` instead of a job.**
   That means no credits were spent — stop, show the user the quoted cost,
   and wait for explicit approval. Never set `confirmCost: true` on a first
   attempt or on your own initiative.
3. **One short 720p+ draft shot before anything else — never 480p, see rule 3
   at the top of this file.** State the total generation count for the full
   reel and get a go-ahead before proceeding past it. Also: provider-side
   generation failures (`PROVIDER_GENERATION_FAILED`) DO get refunded —
   confirmed 2026-08-13, a failed 10s/720p generation returned its 5,000
   credits automatically. Re-check `get_balance` after any failure before
   assuming the spend is gone.
4. **Exhaust free fixes first** — trim window, cut point, crop offset,
   `setpts` nudge. On every prior project in this repo the edit fixed more
   visible defects than a bigger model did.
5. **Regenerate the broken shot, never the reel.**
6. Free generations on this account read **0 remaining** as of 2026-08-13 —
   `freeGeneration: true` on a model does not mean this account gets it free
   right now. Check first.

## Open items (status as of the first real build, 2026-08-13)

Several items below are now resolved by measurement (marked **FIX
CONFIRMED** or **MEASURED**). One major question remains open: the
body-plan-vs-"dancing" conflict — see that item below before starting a new
session on this character.

- **Does Seedance 2.5's audio reference actually drive dance timing?**
  **MEASURED 2026-08-13, YES.** Experiment 0 run: DC_Muppet.JPG seed (outpainted
  to 9:16), 2 bars (4.365s) of "Thursday Soft Launch" cut from the beat grid
  (beat period 0.5457s, bar period 2.183s), modelId 3013 (Seedance 2.5 R2V
  Audio, 480p), `generate_audio: true`. `motion_period.py` measured the
  clip's dominant motion period at **0.5417s** — a 0.7% match to the song's
  quarter-note beat period. The model is genuinely listening to the audio and
  locking body motion to the beat, not just decorating with it. Architecture
  conclusion: pass the song on every shot and let it carry continuous sync
  (the "period ≈ a clean quarter of the bar" branch), retime only for
  residual drift. This also means the bar-loop architecture is a choice for
  shot economy, not a workaround for a musically-deaf model.
- **Where identity drift starts** on a felt puppet, in seconds. **MEASURED,
  and it's a different failure mode than assumed.** Body shape, color, and
  proportions held rock-solid for the full 5s (no ~4-5s extrapolation cliff
  like the golf vantage findings). But **facial detail drifted starting at
  frame 1**: the seed's brown/white cartoon eyes and open smiling mouth were
  replaced with flat black dot eyes and a closed straight mouth from the
  first generated frame onward, held consistently wrong for the whole clip.
  This reads as a first-frame *reinterpretation*, not a long-span drift —
  the model redrew the face once at generation start rather than losing it
  gradually. Likely fix: name the exact eye/mouth construction in the prompt
  ("wide round eyes with visible white sclera and brown iris, open smiling
  mouth with a small pink tongue") rather than relying on the seed image
  alone to carry that detail. **FIX CONFIRMED, 2026-08-13 (two later runs,
  10s and 17s, both 720p).** Naming the exact eye/mouth construction in the
  prompt held the face correctly for the *entire* clip both times, not just
  the opening frames — this is a reliable fix, not a partial one. Keep this
  face-construction paragraph in every prompt going forward; do not rely on
  the seed image alone.
- **Amplitude, measured low.** `mean_abs_frame_diff` was only 4.18 (0-255
  grayscale scale) — the QC contact sheet confirms this reads as a gentle
  sway, not committed dancing, and the prompted bar 1 / bar 2 distinction
  isn't visible. Matches this repo's standing "polite motion" failure
  pattern. Next attempt should prompt more forcefully for full-amplitude,
  committed motion and/or lean on the edit (punch-in, crop) to sell it.
  **FIX CONFIRMED, 2026-08-13.** Explicit "committed, full-amplitude... big
  confident movement, not a gentle sway" language plus a per-stage move list
  produced clearly dynamic motion (arm throws, varied poses, real dancing) on
  both the video-reference run and the text+audio-only run. This fix is
  independent of the video-reference / body-plan issue below — it worked in
  both cases.
- **Does a seamless loop actually close?** Setting `end_frame` = start frame
  should give a clean loop, but nothing has verified that Seedance lands the
  pinned end frame cleanly rather than snapping to it — Veo's measured
  behavior was a hard snap in the final frame or two, which would show as a
  hitch at every loop point. If it snaps, trim the last few frames before
  looping and check again. Still unmeasured — Experiment 0 didn't use
  `end_frame`.
- **How much `setpts` correction is visually acceptable** before the motion
  reads as slow-motion or fast-forward. Assumed ~15%; unmeasured. If a clip
  needs more than that, re-roll rather than stretch.
- **Whether motion transfer (Path B) survives a non-human body plan.**
  Predicted to be the weak point of that path; untested.
- **"Dancing" pulls this character toward a human body plan no matter what —
  MEASURED, and it's NOT what it first looked like.** A 30s run that combined
  `@Image1` + `@Audio1` + `@Video1` (a human dancer reference) produced a
  character with two full arms and two legs, contradicting an explicit "no
  separate arms or legs, only one paw... never grows limbs it doesn't have"
  instruction. The first hypothesis was that `@Video1`'s human structure
  caused it. **That hypothesis was wrong.** A follow-up 17s run at 720p with
  the SAME body-plan instruction but NO video reference (image + audio only)
  produced the exact same result — two arms, two legs, every frame, for the
  full 17s. Neither the video reference nor the resolution was the cause.
  The real cause appears to be that "dancing" is such a strongly
  human-associated action in this model's training that it overrides an
  explicit body-plan constraint in the prompt, at least at the strength this
  was worded. Unresolved: whether even stronger/differently-worded language
  (e.g. leading with the body-plan constraint instead of ending with it,
  repeating it at each stage, or naming the limb count explicitly — "exactly
  one limb, zero legs") can override this, or whether it's a hard prior this
  model can't be prompted around for a dancing action specifically. Untested
  as of 2026-08-13; next session should try re-ordering/repeating the
  constraint before concluding it's unfixable. In the meantime this is a
  real tradeoff to present to the user: accept the character dancing with
  limbs it doesn't have in the still (identity holds on face/color/logo,
  breaks on body plan), or fall back to a non-"dancing" framing of the
  motion (sway/bounce/wobble language that avoids the word entirely) which
  may dodge the humanoid prior.
- **Resolution's real effect, measured — it's about material fidelity, not
  identity.** 720p (modelId 3002) vs 480p (modelId 3013) was compared
  head-to-head with the same character. Fur/material fidelity was visibly
  better at 720p — individual fiber texture, richer color, sharper
  rendering, closer to the seed's actual rendering style. But 720p did NOT
  fix the body-plan drift above, and 480p did NOT cause it either (480p's
  Experiment 0 run, without a face-detail prompt, actually had the CORRECT
  body plan — one paw, no arms/legs — while later 720p runs, with a
  face-detail prompt, had the WRONG body plan). Resolution and body-plan
  fidelity are independent axes; don't expect a resolution bump to fix an
  identity/anatomy problem, only a texture/material one. **User directive,
  2026-08-13: never propose or default to 480p regardless of this finding —
  480p is unacceptable to this user on quality grounds alone, independent of
  the body-plan question.**
- **Whether a 30s single generation is ever the right call** on Path A, given
  `duration` goes to 30. Assume no (montage/loops, per rule 2 up top) until
  something measures otherwise.
- **Cost per shot, measured for Path A.** A 5s, 480p, R2V+Audio generation
  (modelId 3013, group 515) cost **1000 credits**, charged without a
  `confirmation_required` gate — the tool queued it directly on that
  occasion. **720p IS more expensive per second — measured, not assumed:**
  a 10s/720p call (modelId 3002) quoted **5,000 credits** (500/s) via the
  `confirmation_required` gate; a 17s/720p call quoted **8,500 credits**
  (500/s, consistent). A 30s/480p three-reference call cost 6,000 credits
  (200/s). So 720p runs roughly **2.5x the per-second cost of 480p** on this
  model. Budget a full 30s reel at 720p around **15,000 credits** —
  substantial against a 40K/month plan if multiple shots or re-rolls are
  needed. Note also: a `PROVIDER_GENERATION_FAILED` result DOES get
  refunded automatically — confirmed when a 10s/720p attempt failed and the
  5,000 credits reappeared in `get_balance` immediately after.
