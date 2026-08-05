# golfCompilationSkill — Golf course photos/videos → an 18-hole Instagram Reel

A standalone recipe for a specific kind of Reel: a **hole-by-hole tour of a golf
course**, built from photos and/or clips of each hole (from a shared Google Drive
folder) plus the course's own website (for the yardage/par book). Each hole's
media gets its **hole number, par, and distance from the whites** burned onto it,
the whole thing is narrated with a script describing the course, and holes
**transition into each other with a vertical drop-in** (the next hole slides down
into frame) instead of a hard cut or a horizontal stitch.

If you want the general photos-and-clips reel builder, use **ReadME.MD** instead;
for the one-video "process reel" format, use **potterySkill.MD**. This file is a
narrower, purpose-built format for golf course content.

**What makes this format different from the base README:**
- **Two inputs, not one.** A Google Drive folder (photos/videos, one hole per
  file, in play order) **and** the course's website (where the par/yardage for
  each hole lives).
- **Per-hole data card burned onto the media itself** — hole #, par, yards from
  the whites — not a generic title.
- **Per-hole layout thumbnail, when the website has one.** Many course sites
  publish a small top-down hole diagram (fairway/green/hazard shape) on the
  same scorecard/course-tour page as the yardage — pulled in and inset onto
  the card like a broadcast graphic, not just the number stats.
- **Missing-hole handling.** If a hole has no photo or video, a blank black frame
  is inserted in its place rather than skipping the hole (keeps the count and
  pacing honest — 9 or 18 beats, always).
- **Vertical drop-in transitions between holes**, not a straight concat. Each
  hole's media slides down into frame from the previous one, so the compilation
  reads as a tour, not a slideshow.

---

## Prerequisites (four things)

1. **Claude in VS Code, with this repo open.** The scripts are already in this
   folder.
2. **ffmpeg + ffprobe in `tools/`.** Not shipped in the repo (too large). Put
   `ffmpeg.exe` and `ffprobe.exe` in the **`tools/`** folder before building —
   download from https://www.gyan.dev/ffmpeg/builds/ (grab the "essentials"
   build, unzip, copy the two `.exe`s from its `bin/` into `tools/`), or
   `winget install Gyan.FFmpeg`. Claude checks for these and will walk you
   through it if they're missing.
3. **A shareable Google Drive folder link** with the course's hole photos/videos,
   and **the golf course's website URL** (for the scorecard / par & yardage
   info). `gdown` (with `beautifulsoup4`) pulls the whole Drive folder in one
   shot — `pip install gdown beautifulsoup4` if not already installed.
4. **A voiceover option.** Either an ElevenLabs voice clone already set up (see
   "One-time setup" below), **or** nothing at all — this format also supports a
   free/no-API-key narrator (`edge-tts`) for when a cloned voice isn't needed or
   the cost isn't worth it for a one-off course tour. Claude asks which you want.

---

## Get started (this is the whole thing)

Drag **this file (`golfCompliationskill.MD`) into the Claude console** and type:

> **let's get started**

Claude reads this file and walks you through it — asking for the Google Drive
media folder and the course website, the play order and front/back/both, then
extracting each hole's par and distance, writing a course-description script,
picking a narrator (cloned voice or free), and building the reel with vertical
drop-in transitions between holes — then saves it to `final/` with a
date-and-time stamp.

That's the intended path. You can also run the steps by hand (see the bottom).

---

## What you get

- A **9:16 vertical** video (1080×1920), the format Instagram Reels expects.
- An **opening title card** with the course's **name and location**, pulled
  from the course website, as the first thing the video shows.
- Each hole's photo/video with its **hole number, par, yardage from the
  whites, and handicap** burned on in a consistent card style — plus a
  **layout thumbnail** inset for any hole whose course site publishes one.
- **Vertical drop-in transitions** between holes — the next hole slides down
  into frame, rather than a hard cut or a horizontal stitch.
- **Blank black placeholders** for any hole missing media, so the hole count
  stays complete (9 or 18) even with gaps in what was shot.
- A narrated **course-description script**, read either in **your cloned
  ElevenLabs voice** or a **free TTS narrator** (your call).
- Optional **burned-in captions** from the same script.
- An optional **countdown timer** showing how long the compilation took to make.
- **Music is left to Instagram** — add it in one tap on the upload screen.
- Output to `final/reel_<date>_<time>.mp4`. Nothing is ever overwritten.

---

## The folders

```
quickVid/
├─ voice_sample/ ← ONE-TIME: drop a sample of your voice here to clone it (ElevenLabs path only)
├─ media/        ← hole photos/videos, pulled from the Google Drive folder
├─ prompts/      ← script.txt (course narration) + holes.json (par/yardage per hole)
├─ final/        ← finished reels appear here, date-time stamped
├─ tools/        ← PUT ffmpeg.exe + ffprobe.exe HERE (not shipped — see Prerequisites)
├─ make_reel.py          ← reused for captions/timer/title plumbing where applicable
├─ make_cards.py         ← PIL toolkit reference for the hole-card overlay style (header/stat_row/footer)
├─ script_fit.py         ← how many script words fit a given reel length
├─ elevenlabs_voice.py   ← voice-clone setup + turns a script into your voiceover (ElevenLabs path)
├─ requirements.txt
└─ .env.example          ← copy to .env; put your ELEVEN_API_KEY + voice id here (ElevenLabs path only)
```

There's no single dedicated script for this format yet — the hole-card overlay
and the vertical drop-in transitions are **hand-built per project** with PIL and
`tools/ffmpeg.exe` directly (same spirit as the "Repurposing a raw recording"
section of `ReadME.MD`). The steps below make the next course tour much faster
to build. Once this format has been built a few times, promote the repeated
parts into a real script.

---

## One-time setup — your voice clone (only if you want the ElevenLabs path)

1. **Drop a voice sample** in **`voice_sample/`** — 1-5 min of you talking, clean
   audio.
2. **Create the clone** at **https://elevenlabs.io/app/voice-lab** → Add Voice →
   Instant Voice Clone → upload that sample → save.
3. **Add your API key** — copy `.env.example` to **`.env`** and set
   `ELEVEN_API_KEY=...` (from https://elevenlabs.io/app/settings/api-keys).
4. **Verify + get your voice id:** `python elevenlabs_voice.py --check`. Save the
   `voice_id` in `.env` as `ELEVEN_VOICE_ID=...`, then re-run `--check` until it
   says **SETUP COMPLETE**.

(Prefer the free narrator, or already have your own audio? Skip this section —
see step 6 below.)

---

## FOR CLAUDE — run this when the user drags in `golfCompliationskill.MD` and says "let's get started"

**Have a short conversation, one topic at a time. Ask before generating; don't
assume. Use sensible defaults and keep it moving.**

### 0. Preflight — make sure ffmpeg is installed
Confirm `tools/ffmpeg.exe` and `tools/ffprobe.exe` exist (not shipped in the
repo). If **either is missing**, stop and point the user to the easiest path
(`winget install Gyan.FFmpeg`, then copy both `.exe`s into `tools/`; **or** the
"essentials" build from https://www.gyan.dev/ffmpeg/builds/). Re-check both are
present before continuing.

### 1. The two inputs — ask for both up front
**Always ask at the start of every session, even if `media/` already has files
in it** — leftover media from a previous compilation may still be sitting there;
never silently reuse it. Ask for:
- **The Google Drive folder link** containing the course's hole photos/videos.
- **The golf course's website URL** (for the scorecard — par and yardage per
  hole). If the user doesn't have it handy, ask for the course name and search
  for it, or ask the user to paste the scorecard numbers directly instead.

List anything already in `media/`, ask whether to reuse, add to, or clear it,
then remove what isn't wanted so only the chosen files remain before building.

Pull the Drive folder: `gdown --folder <url>` (needs `beautifulsoup4`) drops
everything into a working folder — move the results into `media/`.

### 2. Front nine, back nine, or both?
Ask: **"Is this the front nine, the back nine, or all 18 holes?"** This decides
how many hole slots you're filling and how the numeric prefixes map to hole
numbers:
- **Front nine** → holes 1-9, prefixes `01_`...`09_`.
- **Back nine** → holes 10-18, prefixes `01_`...`09_` in the media folder but
  **labelled** hole 10-18 on the cards (keep a mapping, don't mislabel).
- **Both** → holes 1-18, prefixes `01_`...`18_`.

### 3. Order and missing holes
Ask: **"Is the media already in hole order — first file is hole 1 (or hole 10
for the back nine), and so on? Any holes missing a photo or video?"**
- **Default assumption: the media is in play order already** — number the files
  with prefixes in the order given (`01_`, `02_`, …) unless the user says
  otherwise.
- **If a hole has no media**, don't skip it — generate a **plain black 1080×1920
  frame** (PIL: `Image.new("RGB", (1080, 1920), "black")`, save as that hole's
  slot) so the hole count and pacing stay complete. Say which hole(s) got a
  placeholder so the user isn't surprised later.
- List the final hole → file mapping back to the user and confirm before moving
  on (offer to reorder or fix any mismatches).
- Supported — photos: `.jpg .jpeg .png .webp`; videos: `.mp4 .mov .m4v .webm`.

### 4. Extract each hole's par, distance, handicap, and layout map from the website
Fetch the course website (and its scorecard/hole-guide page if separate — many
courses have a "Course Guide," "Scorecard," or per-hole page). Pull, for each
hole in scope (front/back/both):
- **Par** (3, 4, or 5).
- **Distance from the whites** — the white tee yardage specifically; course
  sites often list multiple tee colors (black/blue/white/gold/red), so confirm
  you're reading the **white** column, not the back tees or the front. If the
  site doesn't label tee colors clearly, say so and ask the user to confirm the
  number for each hole rather than guessing.
- **Handicap** (a.k.a. stroke index / handicap rank) — the 1-18 difficulty
  ranking on the scorecard, usually its own column next to par/yardage. It's
  normally one shared ranking across tees (not per-tee like yardage), but
  confirm against the same table you're reading par/yards from rather than a
  separate handicap-only chart if the site has both. Each hole in scope should
  get a distinct number; flag it to the user if the scrape produces a
  duplicate or a gap, since that usually means a misread column.
- **Hole layout thumbnail, if the site has one.** Many courses publish a
  small top-down diagram of each hole (fairway/green/hazard shape) on the
  same scorecard or "Course Tour"/"Hole-by-Hole" page — sometimes a plain
  `<img>` per hole, sometimes served through an embedded widget (BirdieFire,
  Golf Genius, 18Birdies, or similar — check the page source/network requests
  for the image URLs if they're not plain `<img>` tags). Download whatever is
  found to `media/hole_maps/`, named to match the hole (`01_map.png`, etc.).
  **This is optional per hole** — not every course publishes one, some only
  offer a single flyover video or a scanned PDF scorecard with no per-hole
  images. If a hole has no map image available, just skip the thumbnail for
  that hole (no black-frame substitute needed — this isn't the hole media
  itself, just an optional accent) and tell the user which holes it's missing
  for.
  - **Fallback when the course's own site has nothing: build the thumbnail
    yourself from real satellite imagery, if the tools are available.** This
    isn't a general/reliable recipe yet (see the caveat at the end of this
    step), but it worked well end to end on the first course tried:
    1. **Find tee/green GPS coordinates per hole.** The course's own site
       almost never has these, but third-party golf-GPS sites often do
       (GolfTraxx's course pages, for one, embed tee/landing/green
       lat-lng pairs per hole in their page JS for the on-page satellite
       map — extract them by regex rather than trying to drive their
       interactive map). Sanity-check by computing tee-to-green distance
       from the coordinates and comparing it to the scorecard's yardage for
       that hole — a match within a few yards confirms the points are real
       and correctly paired.
    2. **Fetch the actual aerial pixels from Google Earth Engine**
       (`earthengine-api`, NAIP imagery for US courses — sub-meter
       resolution). This needs a one-time setup only the user can do:
       a registered Earth Engine Cloud project and an interactive
       `ee.Authenticate()` browser login (see the repo's session notes for
       the exact steps). Earth Engine's own built-in OAuth client is fine
       for this — a user-supplied custom OAuth client isn't needed unless
       you're building something beyond a local script.
    3. **Always rotate the crop so the hole reads vertically, tee at the
       bottom and green at the top** — the standard yardage-book
       convention — regardless of the hole's true compass direction.
       Compute the tee→green bearing, rotate the fetched square image by
       that many degrees so the tee→green vector points straight up, then
       center-crop to a fixed portrait size. Skipping the rotation and just
       cropping a bounding box in its natural orientation produces
       unreadable results for any hole that runs mostly east-west (a
       nearly straight hole's bounding box is a thin horizontal sliver at
       any zoom that also fits a portrait video frame).
    4. **Make it big.** A thumbnail sized to be a subtle corner accent reads
       as a smudge once it's sitting inside a 1080-wide vertical video
       frame — size it more like ~420×720px (roughly a third of the frame
       width, most of the frame height) so the fairway shape, bunkers, and
       green are actually legible, not just present.
  - **Caveat:** the GPS-lookup half of this (step 1) depends on a
    third-party site happening to have this specific course plotted, in a
    page structure that happens to still parse the same way — it's not
    guaranteed for the next course and may need a different source or a
    manual pin-drop from the user. The rotate-to-vertical-and-go-big half
    (steps 3-4), once you *have* coordinates from anywhere, is the reliable,
    repeatable part.

**Also pull the course's name and location** (city/state, or the fuller
address if the site gives one) from the same website — usually right in the
header, footer, or an "About"/"Contact" page. This is what opens the video
(see step 5 below), so confirm the spelling of the course name and the
city/state back to the user along with the par/yardage table.

Write the result to `prompts/holes.json`, one entry per hole, e.g.:
```json
{
  "1":  { "par": 4, "yards": 385, "handicap": 7, "map": "media/hole_maps/01_map.png" },
  "2":  { "par": 3, "yards": 162, "handicap": 15, "map": null },
  "...": "..."
}
```
(`"map"` is `null` for any hole with no layout image found.)

**Show the full table back to the user and get explicit confirmation** before
burning it onto anything — scraped scorecards are a common source of
transcription errors (wrong tee column, stale renovation-era yardage, a hole
out of order), and it's cheap to fix now versus after the burn. Also show
which holes did/didn't get a layout thumbnail so the user isn't surprised
later by an inconsistent card style across holes.

### 5. Opening title card — course name and location
Before hole 1 (or hole 10, back nine), the video opens with a short title
card: the **course name** and its **location** (city/state), pulled from the
course website in step 4 — not typed fresh, and not skipped even for a
front-nine-only or highlights cut. Build it the same way as the hole cards
(PIL, matching `make_cards.py`'s `header()`/`footer()` style — course name as
the big header line, location as a smaller line beneath), full 1080×1920
frame, held for a couple seconds before the drop-in into hole 1 begins. If
the site gives an ambiguous or multiple location (multiple courses/campuses
under one name), confirm which one with the user rather than guessing.

### 6. Burn the hole card onto each hole's media
For each hole, overlay a small consistent card — hole number, par, yardage,
handicap, and (if `holes.json` has one) the hole's layout thumbnail — onto
its image or video. Match the visual language of `make_cards.py`'s toolkit
(`header()` for the big number/eyebrow line, `stat_row()` for the
par/yards/handicap trio, `footer()` if a course name/date footer is wanted)
rather than inventing a new style:
- **Photos:** open with PIL, draw the card directly onto the image (top or
  bottom third — pick whichever is less busy for that hole's photo), save to a
  working folder.
- **Videos:** either `drawtext` the same info via ffmpeg for the clip's
  duration, or render a short PIL title-card frame and prepend it to the clip —
  ask the user which they'd prefer (drawtext keeps the hole visible the whole
  time; a title card is punchier and cleaner to time against narration).
- **Layout thumbnail, when available:** composite the downloaded map image as
  a small inset box (roughly the size of a broadcast hole-diagram graphic —
  a fraction of the frame width, not a dominant element) in the same corner
  as the stat card, with a thin border or subtle drop shadow so it reads
  clearly against varied photo backgrounds. It rides with `drawtext` clips
  the same duration as the rest of the card, or bakes into the PIL card frame
  for photos/title-card videos. For a hole with no thumbnail (`"map": null`),
  just render the card without it — don't stretch or fake one.
- **Blank placeholder holes:** still get the card (hole #, par, yards, and the
  layout thumbnail if one was found for that hole) burned onto the black
  frame, so a missing-media hole reads as "no photo yet," not as a glitch.

### 7. The script + the narrator
**a) Course-description script** → `prompts/script.txt`. Write a short script
describing the course as a whole (character of the layout, standout holes,
front vs. back nine if doing both, total yardage/par if useful) — draft it from
what you scraped plus anything the user tells you about the course, then let
them edit. Tell the user the **word budget** first from the target length (see
step 8) at ~150 wpm; run `python script_fit.py --target <N>` for the exact
number.

**b) Ask which narrator:** **"Voiceover in your cloned ElevenLabs voice, or the
free narrator?"**
- **ElevenLabs (cloned voice):** run `python elevenlabs_voice.py --check` first;
  walk through one-time setup if it's not SETUP COMPLETE. Then
  `python elevenlabs_voice.py --script prompts/script.txt` → writes
  `voiceover/vo_eleven.mp3`, prints characters used / cost (relay it). Costs
  per character — worth it for the voice match, not free.
- **Free narrator (no API key, no cost):** use `edge-tts` (Microsoft's free
  neural TTS — `pip install edge-tts` if not already present):
  ```
  edge-tts --voice en-US-GuyNeural --file prompts/script.txt --write-media voiceover/vo_edge.mp3
  ```
  Offer a couple of voice options (`en-US-GuyNeural`, `en-US-AriaNeural`,
  `en-GB-RyanNeural`, etc. — `edge-tts --list-voices` shows the full set) rather
  than defaulting silently. Quality is solid for a course-tour narration; it
  just isn't the user's own cloned voice.
- **Already have an audio file:** confirm it's in `voiceover/`; skip generation.

### 8. Length and pacing
Ask the target length the same way as the base README (max reach 7-15s, sweet
spot 15-30s, deep engagement 30-60s, long form beyond) — but note **9 or 18
holes each need a beat to register**, so a full 18-hole tour realistically wants
**deep engagement or long-form** (roughly 2-4s/hole minimum for a quick flash,
more if the narration lingers on a hole). For front-nine-only or a highlights
subset, the shorter bands work fine. Pick a concrete `--target-seconds` and
divide it across the holes in scope, weighting toward holes the narration spends
more time on.

### 9. Vertical drop-in transitions between holes
This is the format's signature move — **holes transition with a vertical
drop-in**, not a hard cut and not `make_reel.py`'s plain concat. The opening
title card (step 5) drops into hole 1 the same way one hole drops into the
next — treat it as segment zero in the chain, not a separate hard cut before
the tour starts. Use ffmpeg's `xfade` filter with a vertical transition type
between each consecutive pair of hole segments, chained across all of them:

```
ffmpeg -i hole1.mp4 -i hole2.mp4 -i hole3.mp4 -filter_complex \
"[0:v][1:v]xfade=transition=slidedown:duration=0.5:offset=<t1>[v01]; \
 [v01][2:v]xfade=transition=slidedown:duration=0.5:offset=<t2>[v012]" \
-map "[v012]" -c:v libx264 -crf 18 -pix_fmt yuv420p final/reel_<stamp>.mp4
```

- `transition=slidedown` makes the incoming hole slide down into frame from
  above the outgoing one; `wipedown` is the harder-edged alternative (no
  motion, just a wipe line moving down) if the user prefers a snappier look.
  Ask which if unsure — `slidedown` is the better default for a calm course
  tour.
- `offset=<tN>` is the cumulative running time at which that transition starts
  (each hole segment's duration minus the overlap, added up) — compute this
  per-segment from each hole's planned on-screen time (step 8), don't guess it.
  `duration=0.5` (half a second) is a good default transition length; faster
  bands (max reach) can go to 0.3.
- Every hole segment (photo-with-card or video-with-card) needs to already be
  normalized to 1080×1920 / same fps before `xfade` — same `normalize_image`
  /`normalize_video` cover-crop treatment `make_reel.py` uses, just applied by
  hand per segment here rather than through that script's plain-concat path.
- Mux the chosen narration track over the finished video afterward (`-i
  voiceover/vo_*.mp3 -c:v copy -c:a aac -shortest`), or fold it into the same
  `ffmpeg` call if it's simpler for the given hole count.

### 10. Captions and timer (optional, same as the base recipe)
- **Captions default to OFF for this format.** Don't burn in a transcript of
  the narration script — the per-hole card (step 6) already carries the
  on-screen text that matters (hole #, par, yards, handicap), and a second
  layer of scrolling narration captions competes with it for attention on a
  small vertical frame. Only add narration captions (same `.srt`-against-the-
  script approach as `make_reel.py --subtitles`) if the user explicitly asks
  for them.
- **Countdown timer:** ask **before** the final render — "How long did this
  compilation take to make?" — and bake in a countdown the same way the base
  README's timer works (`add_timer.py` after the fact, or fold the ASS overlay
  into the same `ffmpeg` pass if hand-building it here).

### 11. Verify before calling it done
Decode the finished render sequentially (`ffmpeg -i out.mp4 -vf
"fps=2,scale=160:-1" frames/f_%03d.png`, tile and look through it) rather than
spot-checking with `-ss` — confirm the opening title card shows the right
course name and location, every hole's card shows the right number, par,
yardage, and handicap, any layout thumbnails are legible and attached to the
correct hole, the blank-hole placeholders look intentional rather than
broken, and each transition actually drops in vertically rather than
reverting to a hard cut. This is the same "verify by full sequential decode, not `-ss`"
discipline documented in `ReadME.MD`'s raw-recording section, and it applies
here too — a wrong hole number burned onto the wrong hole's media is exactly
the kind of silent-but-wrong error that only shows up on a real look-through.

### 12. Report
Give the output path (`final/reel_<stamp>.mp4`), its length, and which narrator
was used; if captions or a timer were added, confirm they landed correctly. If
any holes used a blank placeholder, remind the user which ones so they know to
send that hole's media next time. If any holes had no layout thumbnail
available from the website, mention those too, in case the user has (or can
get) a scorecard image to supply by hand next time.

Every step writes a new timestamped file — nothing is overwritten.

---

## The hole card, explained

Each hole's media gets the same small, consistent overlay — modeled on
`make_cards.py`'s toolkit conventions:
- **Hole number** — large, top-line (the `header()` eyebrow/number style).
- **Par**, **yards from the whites**, and **handicap** — a compact stat trio
  (the `stat_row()` style), e.g. `PAR 4` · `385 YDS` · `HCP 7`.
- **Layout thumbnail** — an inset of the hole's top-down diagram, when one is
  available (from the course website, or the GPS+satellite-imagery fallback
  in step 4). It's an accent next to the stat row, not a replacement for it —
  a hole with no thumbnail still gets the full number/par/yards/handicap
  card, just without the inset. **Go big and always vertical**: ~420×720px
  (a corner-postage-stamp size reads as a smudge on a 1080-wide frame), with
  the hole rotated so tee→green points straight up regardless of the hole's
  true compass direction — the standard yardage-book convention, and the
  only way a nearly-straight east-west hole doesn't turn into an unreadable
  sliver.
- Keep the stats to those four facts. Resist adding hole names or other
  scorecard trivia unless the user specifically asks — the card should read
  at a glance while the hole is on screen for a few seconds.
- Placement: whichever third of the frame is least busy for that specific
  photo/video — there's no single fixed position across all 18 holes the way
  there is for a title in the base format, because course photography varies
  hole to hole. Keep the thumbnail inset in the same corner as the stat card
  so the eye only has one spot to check per hole.

---

## Notes & limits

- **Tee color matters.** "Distance from the whites" specifically means the
  white tee markers — don't default to the "member tees" or the back tees
  without checking; if a course's site doesn't clearly label tee colors, ask
  the user to confirm rather than guessing which column is white.
- **Handicap is a ranking, not a score.** It's the hole's 1-18 relative
  difficulty (stroke index), one shared list across tees — every hole in
  scope should get a distinct number; a repeat or gap almost always means a
  misread column, so double-check against the source table rather than
  guessing.
- **Missing holes get a black placeholder, not a skip** — the count (9 or 18)
  should always be complete so the compilation reads as a full tour.
- **Layout thumbnails are best-effort, not guaranteed.** Not every course
  publishes per-hole diagrams — some only have a flyover video, a scanned PDF
  scorecard, or nothing at all. Missing ones are just omitted from the card
  (no placeholder needed, unlike missing hole media), and reported to the
  user at the end so they know which holes could use a hand-supplied image
  next time.
- Source-clip audio is dropped in favor of the one narration track, same as the
  base format. Want music? Add it on Instagram.
- ElevenLabs costs per character (prints usage/cost each generation); `edge-tts`
  is free but is not the user's own voice — offer both, let the user choose.
- Keep reels under ~90s for the Instagram feed if doing a highlights cut; a full
  18-hole narrated tour will usually run long-form, which is fine for Reels but
  worth flagging to the user up front so the length isn't a surprise.
