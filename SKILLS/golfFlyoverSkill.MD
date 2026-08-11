# golfFlyoverSkill — cinematic, geographically-real golf hole flyovers

A **plan**, not yet a script. Goal: a single cinematic 9:16 "hero flyover" of one
golf hole — camera sweeping from the tee, down the fairway, arriving over the
green — built from a text prompt **plus a real map of the hole** (the course's
own website imagery, or satellite imagery keyed to real GPS waypoints), not a
generic stock-photo camera pan.

This is a sibling to the other two golf/carving skills and reuses their proven
machinery rather than inventing new machinery:
- **Map sourcing** (website scrape → GPS → Google Earth Engine satellite crop →
  rotate tee-to-green vertical) is `golfCompliationskill.MD` step 4's fallback
  recipe, verbatim. Don't re-derive it — read that section first.
- **Chained start/end-frame generation, prompting-for-the-finished-state, drift
  QC, and free-assembly-does-most-of-the-work** are `imageGenSkill.MD`'s carving
  pipeline lessons, retargeted from "carving progress" to "camera motion."

If the user wants a full 9/18-hole tour instead of one hero shot, that's
`golfCompliationskill.MD`'s job (photo/video per hole + vertical drop-in
transitions) — this skill is specifically for the single cinematic flyover shot,
and its output can later be dropped into that pipeline as one hole's "video."

---

## Why build this instead of just using ViewMax / Artlist's toolkit

Checked both (2026-08-11) before writing this plan:

- **ViewMax** (deevid.ai) and **ImagineArt's AI Drone Video Generator** are the
  same category of tool: feed in **any single photo** + pick a canned camera
  preset ("smooth flyover," "sweeping arc," "zoom transition"), get a **5-second**
  generic clip. There is no geography involved — the "flight path" is just a
  stock camera move applied on top of whatever photo you gave it. Good for a
  quick real-estate listing teaser, not built for accuracy.
- **Artlist's AI toolkit** is a general image/video generator (upload + prompt),
  no aerial/flyover-specific feature at all.

**What we can do that they can't: ground the flight path in the hole's actual
shape.** We already have the recipe (from the golf compilation work) to pull
real tee/landing/green GPS coordinates and real satellite pixels for a specific
hole. That means our "drone" flies over the *actual* fairway bend, the *actual*
bunker placement, the *actual* green contour — not a generic arc over a flat
photo. The tradeoff is cost/time: multiple chained generations instead of one
5-second preset click. That's the bet this skill is making.

---

## ▶ Let's get started

When the user invokes this skill, run this in order. Ask only for what's
missing.

0. **Confirm scope: one hero flyover for one hole.** (Not a multi-hole tour —
   redirect to `golfCompliationskill.MD` if that's what they actually want.)
1. **Which course, which hole, what style?** Course name + hole number (or "pick
   the signature/most photogenic hole" and suggest one from the yardage book —
   usually a par 3 over water or a dogleg with a view). Style descriptors:
   lighting (golden hour default — reads best and is the genre convention),
   any specific look ("PGA broadcast," "moody overcast," "morning mist").
2. **Get the map/geography seed.** Try the course website first (published
   aerial/hole-tour image), but **check its pixel dimensions before trusting
   it** — Renditions' hole08.jpg was a 230×503px stylized marketing graphic,
   not a photo. That's still fine as a *shape* reference, but real satellite
   pixels make a much better image-to-image seed. Preferred path, validated
   end-to-end on hole 8 (2026-08-11), **supersedes `golfCompliationskill.MD`
   step 4's GolfTraxx-scraping fallback** — try this first, not last:
   1. **Geocode the course** via Nominatim (`nominatim.openstreetmap.org/search?q=<course
      name>&format=json`) to get its OSM bounding box/center — no API key.
   2. **Query Overpass API for `golf=hole` ways tagged `ref=<hole number>`**
      inside that bbox:
      `https://overpass-api.de/api/interpreter?data=[out:json];way["golf"](bbox);out
      body geom;` — many well-mapped courses have every hole's tee→green
      centerline in OSM, tagged with `ref` (hole number) and `par`. This is
      **exact GPS ground truth**, no page-scraping fragility. Confirm the
      match by (a) `ref`/`par` agreeing with the course's own scorecard, and
      (b) the way's real-world path length (haversine sum across its nodes)
      landing within a few yards of the scorecard yardage. Neighboring
      `golf=tee/green/bunker/fairway/lateral_water_hazard` ways whose
      bounding-box centers fall near the hole's own bbox belong to that hole
      too — use them to sanity-check bunker count/position against the
      course's own diagram before trusting anything.
   3. Not every course has this OSM detail — if the Overpass query comes back
      empty, fall back to `golfCompliationskill.MD` step 4's GolfTraxx/GPS
      recipe, or to visual identification (fetch a wide Earth Engine crop of
      the whole property and eyeball hole shapes) — but treat visual-only
      identification as low-confidence; a wide 18-hole mosaic has many
      similar-looking doglegs, and misidentifying the hole silently defeats
      this whole skill's reason to exist. Cross-checking against 1-2
      neighboring holes' shapes (routing order = physical adjacency) raises
      confidence if you have to go this route.
   4. **Fetch NAIP imagery from Earth Engine** for a square region centered on
      the tee/green midpoint, sized in *real meters* (compensate degrees by
      `cos(latitude)` for the east-west span) — then **pass `dimensions` to
      `getThumbURL` as an explicit `"WxH"` string**, not a bare integer.
      `dimensions: 1800` sizes pixels by raw lat/lon degree span, not true
      ground distance, which silently produces non-square pixels (different
      meters/px on each axis) whenever the region's raw-degree aspect ratio
      differs from its physical aspect ratio — and that distortion then
      corrupts any bearing/rotation math done on the image afterward.
   5. **Rotate so tee→green points straight up.** Do the geo→pixel mapping
      and rotation in Python with OpenCV (`cv2.getRotationMatrix2D` +
      `cv2.warpAffine`), and apply the *exact same matrix* to the tee/green
      pixel coordinates to verify they land vertically aligned post-rotation
      — don't hand-derive the sign convention for PIL's `Image.rotate()`
      expand-canvas offset by hand; it's an easy mistake to get subtly wrong
      and have it look almost-plausible (it did here, first try) — verifying
      numerically that both points land at the same x after rotation is cheap
      and catches it immediately, instead of by eye.
   6. Crop to portrait, sanity-check tee-to-green pixel distance against the
      scorecard yardage, **then show the map/crop to the user before spending
      on any generation** — everything downstream inherits its geography.
   - Earth Engine needs one-time setup if unused on this machine: register a
     Cloud project for Earth Engine at code.earthengine.google.com (existing
     GCP projects work — pick "select an existing Cloud project" during
     registration, which also grants the needed IAM permission in one step),
     then `earthengine authenticate` (installed at
     `%APPDATA%\Python\Python312\Scripts\earthengine.exe` if not on PATH).
     Store the project id in `.env` as `EARTHENGINE_PROJECT` (see
     `.env.example`) — newer `earthengine-api` requires
     `ee.Initialize(project=...)`, a bare `ee.Initialize()` fails with "no
     project found". If auth was set up previously but `ee.Initialize()`
     throws "Please authorize...", the refresh token has likely gone stale
     (Google expires them fairly readily) — `earthengine authenticate
     --force` redoes the browser login and fixes it; no need to re-register
     the project.
3. **Build three waypoint stills from the one map/seed** (see "Waypoints" below)
   — establishing (tee), mid-flight (fairway/landing), arrival (green). Eyeball
   all three before spending on video — same QC-by-eye discipline as the carving
   ladder.
4. **Generate two chained video segments** (tee→fairway, fairway→green) with a
   start+end-frame model (see "Which model" below). ~8-16s combined.
5. **Trim + hard-cut/quick-crossfade the two segments into one continuous
   flight**, grade pass, optional minimal hole-card burn-in, optional ambient
   audio bed.
6. **QC** (checklist below) — scrub the full clip at 1fps, not two spot-checks.
7. Deliver to `final/flyover_<course>_<hole>_<stamp>.mp4`.

Once this has been run by hand for 2-3 holes and the recipe stabilizes, promote
it into a real script (`make_flyover.py`) the way `make_ladder.py`/
`veo_carve.py` came out of the carving skill's hand-built phase — don't build
that script speculatively before the technique is validated once.

---

## Waypoints — why three stills, not one

A single image-to-video generation asked to "fly the whole hole" has the same
failure mode carving had when asked to "carve the whole subject" in one shot:
it either does nothing convincing or hallucinates wildly by the far end. Three
grounded stills, each a real crop of the map/satellite seed, keep every second
of footage anchored to real geography:

| waypoint | source crop | what it shows |
|---|---|---|
| A — establishing | full hole crop (the map/satellite seed itself, or a light re-render of it) | whole hole visible, tee to green, sets geography for the viewer |
| B — mid-flight | cropped/zoomed to the fairway landing area | matches the tee shot's real landing zone — same "crop a partial rung, don't regenerate" trick as the carving macro shots |
| C — arrival | cropped/zoomed to the green + surrounds | real green shape/contour, real bunkers |

**Render each crop from flat map/satellite into "photoreal aerial drone shot"**
via image-to-image (Nano Banana Pro / `gemini-3-pro-image` / GPT Image 2 —
whichever is on hand; `gemini-3-pro-image` held geography changes best in the
carving work's "change only this region" tests, worth trying first here too).
Prompt to add photoreal lighting/shadow/grass texture while explicitly
constraining it not to invent new hazards, move the green, or reshape the
fairway — same guard-rail principle as carving's "not a living animal" negative
prompt, just aimed at geography instead of anatomy.

---

## Which model for the camera motion

Same decision the carving pipeline already made, retargeted: a flyover needs
**guaranteed start+end-frame interpolation** (the "fly from A to B" motion, not
"animate this still"), same as carving needed to guarantee a *progression*.

| | Seedance 2.0 (Higgsfield) | Veo 3.1 (`veo-3.1-generate-preview`) | Minimax Hailuo (`variant: minimax`) |
|---|---|---|---|
| start+end frame | yes | yes (`last_frame`) | yes (`end_image`, not `minimax-2.3`) |
| native audio (wind/ambient) | no | **yes** — the reason to prefer Veo here | no |
| resolution | up to 1080p | native 9:16 1080p | 1080 but follows seed aspect (3:4 in → crop to 9:16) |
| clip length | ~5-6s | **8s, mandatory** with `last_frame` | 6s |
| billing | Higgsfield plan | Google prepay credits | Higgsfield plan |

**Default to Veo 3.1** if Google credits are available — native audio matters
more here than it did for carving, because a flyover's ambient wind/rustle sells
the "drone footage" illusion the way foley sold "real carving." Fall back to
Seedance 2.0 (mute) + a light wind/nature audio bed if not, same fallback logic
as the carving hybrid path. Same `last_frame`-needs-8s and aspect-must-match-
seed gotchas from `imageGenSkill.MD` apply unchanged — read the "Veo behavior
quirks" section before generating.

### Where to get these models (checked 2026-08-11)

Two subscription options were evaluated against this plan's actual model list:

- **Kling.ai's own membership** (kling.ai/app/membership — Standard ~$7-9/mo,
  Pro ~$26, Premier ~$65, Ultra ~$128) — **skip it.** It only buys Kling's own
  model family, not Nano Banana / Seedance / Veo at all, so it doesn't cover
  this plan's model list. It's also the exact genre this project already
  benchmarked and lost on: `imageGenSkill.MD` found Kling (`kling3_0_turbo`)
  "only nicked the surface, left ~85% flat" against Grok on a task that's
  fundamentally about strictly following a constrained transformation — the
  same core requirement as "don't invent a bunker that isn't really there."
  Kling is already reachable via Higgsfield's `kling3_0_turbo` if ever wanted,
  so a separate direct subscription would be redundant besides.

- **Artlist's AI toolkit** (toolkit.artlist.io) — has the right model family
  (Nano Banana, Seedance, Veo all present) split across tiers by unlimited-vs-
  credit access. **The `artlist` MCP server (`https://mcp.artlist.io/mcp`) is
  now registered and authenticated in this project** (local scope, added and
  OAuth'd 2026-08-11 — same pattern as the `higgsfield` MCP server already used
  throughout this repo), so generation can go straight through MCP tool calls
  once it's confirmed reachable in a fresh session (`ToolSearch("artlist")` —
  tools weren't visible mid-session at registration time, standard for a newly
  added MCP server). This replaces hand-rolling the OAuth2 client-credentials
  flow documented at developer.artlist.io/authentication — that flow is for
  building against the raw Artlist Business API directly and isn't needed now
  that the MCP server handles auth. What the connected account can actually
  generate (which models, unlimited vs. credit-metered) is still governed by
  whichever subscription tier is active on it — the tiers below:
  | tier | ~price/mo | unlimited on | notes |
  |---|---|---|---|
  | AI Creator | ~$42 | Nano Banana 2 **Lite** + Seedance **mini** | Seedance mini caps at 720p — short of this plan's 1080p/no-letterbox QC gate |
  | AI Professional | ~$240 | + Veo 3.1 **lite** | still the "lite" sibling, not standard Veo |

  **Reality check (2026-08-11, first real run):** the tier table above is
  Artlist's published *subscription* structure, but the account actually used
  here was on a **flat credit-pool plan ("AI Suite 40K" — 40,000 credits/mo,
  no unlimited-model bucket at all)**. On that plan, standard **Veo 3.1 with
  audio was directly generatable** (not gated behind a "lite" sibling) at
  **3,400 credits per 8s/1080p/9:16 clip**. Don't assume the tier table below
  describes the connected account — call `get_balance` (shows plan name +
  credits) and check `list_models`' `freeGeneration` flag per model before
  planning a budget. If `freeGeneration` models exist for video (seen: Kling
  1.6 Std/Pro, Seedance 2.0 Mini), they're the true no-cost draft tier — but
  Kling already lost the "follow this constraint exactly" benchmark elsewhere
  in this project, and Seedance Mini is the same weaker-constraint-following
  "mini" sibling problem as Veo lite, so treat free-tier drafts as motion/cut
  sanity checks, not a fidelity substitute.

  **Recommendation: start on AI Creator, don't jump to AI Professional yet.**
  This plan is still in its "run it by hand 2-3 times to validate the recipe"
  phase (see Open Items below) — exactly what a cheap unlimited-lite/mini tier
  is for, same "draft cheap, finish expensive" pattern the carving pipeline
  already validated (test on fast/720p, spend only once the recipe is right).
  Don't expect the *lite* tiers to solve the fidelity problem outright, though:
  this project already measured that a model's "lite/fast" sibling follows
  constraints noticeably worse than its standard version on identical seeds
  (`veo-3.1-fast` produced duplicate knives and raced past its specified stage
  where standard Veo gave single-knife, correctly-bounded takes) — exactly the
  failure mode this plan is most fragile on (geography drift). If Creator-tier
  quality can't hold the fairway/green geometry through QC, the fix is buying
  a handful of full-resolution, pay-per-generation credits (standard Seedance
  2.0 or Veo 3.1) for just the final hero shots — not upgrading to unlimited
  Veo 3.1 lite. Same "regenerate the broken shot, never the reel" cost
  discipline as the rest of this file.

- **The direct Google Veo API path (`veo_carve.py`, prepaid Google credits) is
  still available too, and is actually a good fit specifically for hero
  shots.** `imageGenSkill.MD`'s V8 runbook documents its hard limits — **2
  requests/minute, 10 requests/day** — which sounds restrictive for a whole
  carving reel's worth of generations, but this plan only needs **2 video
  generations per hero flyover** (tee→fairway, fairway→green), so a single
  hole comfortably fits in one day's quota with room to re-roll a bad segment.
  This gets you **standard** Veo 3.1 (not the lite sibling), which is the
  fidelity tier the geography guard-rail actually wants — use it for the final
  hero-quality pass once the recipe is validated on Artlist's cheaper tier,
  rather than as the validation loop itself (2/day is too slow for iterating
  on prompts).

## Prompting the flight

Port directly from the carving skill's most important lesson: **prompt the
finished, continuous motion, not the activity.** A prompt that describes
"the drone flies over the course" tentatively gets ten seconds of hover. Demand
the specific arc explicitly —

> "Continuous smooth aerial drone shot, banking gently right as it tracks low
> over the fairway from the tee, rising altitude near the green to reveal the
> putting surface and bunkers. Golden hour lighting, long shadows, grass
> texture visible, no cuts, no hovering, camera never stops moving. The
> fairway shape, bunkers, and green contour exactly match the reference image —
> do not add, move, or resize any hazard or green."

That last sentence is the geography guard-rail — carried over from the "not a
living animal" negative-prompt lesson, aimed at the failure mode specific to
this genre (a model happily invents a nicer-looking green than the real one).

**A positive prompt saying "never stops moving" is not sufficient on its own
— confirmed on hole 8's first real pass.** Both segments were generated with
that exact instruction; one still read as near-hovering across the *entire*
8s (only visible at 4fps scrubbing — the 1fps QC pass made it look
acceptable), the other front-loaded all its motion into the first ~5s and
locked static for the rest (the known "`last_frame` is a soft target that
snaps early" quirk, now confirmed to reproduce on Artlist's wrapped Veo 3.1
too, not just the direct Google API). Two concrete fixes:
- **Use the model's `negative_prompt` field explicitly** (present in Artlist's
  Veo 3.1 config, easy to forget since the carving pipeline's direct-API Veo
  work never needed one) — e.g. `"static shot, hovering, frozen camera, no
  movement, stationary camera, tripod shot, slow crawl"`.
- **A weak-motion clip can't be salvaged by trimming** (there's no strong-
  motion window inside it to cut down to) — that's a re-roll, not an edit.
  Only the early-snap-then-hold failure is trim-fixable (discard the static
  tail, keep the early motion — the mirror image of the existing "trim EARLY
  windows, never the tail" `last_frame` lesson).

## Assembly (free, and most of the remaining quality lives here — same finding
as the carving v6/v8 work)

1. **Two segments, one cut.** Trim each clip's best continuous-motion window
   (scrub, don't guess) and join with either a hard cut or a **very short**
   crossfade (0.2-0.3s) timed to a moment where both segments' camera angle and
   altitude roughly agree — a big angle mismatch at the cut reads as a jump,
   not a continuous flight.
2. **This is not the compilation skill's vertical drop-in.** That transition is
   for *discrete holes* on a tour. A flyover is one continuous camera move, so
   the cut should read as invisible, not as a stylistic transition.
3. **Grade pass** — the carving work's saturation/contrast/punch-in recipe
   (`eq=saturation=1.2-1.3`, mild `unsharp`) generalizes here; aerial satellite-
   derived renders tend to come out flatter/greyer than a real drone shot.
4. **Optional minimal hole-card** — reuse `make_cards.py`'s style (hole #, par,
   yards) burned in for the first 1-2s only, small corner placement, if this
   flyover is meant to carry standalone golf context rather than being dropped
   into a bigger course-tour edit. Skip it if the shot is going to be recut into
   the compilation skill's per-hole slot (that pipeline burns its own card).
5. **Audio** — Veo's native ambient track if used; otherwise a light wind/
   nature bed (no dialogue/foley needed the way carving needed knife foley).
   Music, as with the other skills, is left for the platform (Instagram) unless
   asked for explicitly.

## QC checklist before calling it done

- [ ] **Scrub the full clip at 4fps, not 1fps** — the carving work found
      bounded shots that looked clean at 3s/5s and blew out by 6s (same
      "looks fine at a glance, breaks later" risk applies to a model quietly
      warping the green shape mid-flight), but on hole 8's first run **even
      1fps sampling was too coarse to catch weak/near-static motion** — a
      clip that reads as "continuous enough" at 1 sample/sec turned out to be
      almost hovering for its full 8s at 4 samples/sec. Tile the frames into
      one contact-sheet image rather than eyeballing a scrubber, so the whole
      clip is visible at once.
- [ ] **Geography holds** — freeze-frame waypoint A vs the arrival frame near C;
      same fairway bend, same bunker count/placement, same green shape. This is
      the flyover-specific equivalent of carving's "same wolf in every frame."
- [ ] **Camera motion reads continuous** across the one cut — no altitude/speed
      jump, no angle flip.
- [ ] **Full 1080x1920, no letterbox** (aspect must match the seed going in —
      same Veo gotcha as carving).
- [ ] **No invented hazards** — a bunker or water feature that isn't on the
      real hole is an immediate re-roll, not a "close enough."

## Cost discipline

Same rule as the carving runbook: **price it before spending it.** One hero
flyover = 2 video generations (tee→fairway, fairway→green) + up to 3 image
renders for the waypoints. State that count and get a go-ahead before
generating, especially on Veo (prepaid Google credits) rather than assuming
budget. Re-roll the specific bad segment, never both.

---

## Open items (resolve when this is actually run for the first time)

- No script exists yet (`make_flyover.py` TBD) — everything above is a by-hand
  recipe, same maturity level `golfCompliationskill.MD` started at.
- Untested: whether Earth Engine NAIP resolution is sharp enough at typical
  fairway-crop zoom to survive the "render into photoreal" step without looking
  muddy — the compilation skill flagged this fallback as validated on exactly
  one course so far, not a general guarantee.
- Untested: whether two chained 8s Veo segments is the right length, or whether
  a third (green-side low pass / hero hold) segment is worth the extra
  generation — decide after seeing the first real result, don't over-plan it
  now.
