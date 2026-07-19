# quickVid — Photos + Videos → Instagram Reel, fast

Turn a pile of photos and clips into a finished **9:16 Instagram Reel** — the right
length, in your own voice, with a title, captions, and an optional countdown timer
— by having a short conversation with Claude. No editing software, no timeline.

**Prerequisites (three things):**
1. **Claude in VS Code, with this repo open.** The scripts are already in this
   folder.
2. **ffmpeg + ffprobe in `tools/`.** These aren't shipped in the repo (too large).
   Put `ffmpeg.exe` and `ffprobe.exe` in the **`tools/`** folder before building —
   download from https://www.gyan.dev/ffmpeg/builds/ (grab the "essentials" build,
   unzip, copy the two `.exe`s from its `bin/` into `tools/`), or install with
   `winget install Gyan.FFmpeg`. Claude checks for these and will walk you through
   it if they're missing.
3. **An ElevenLabs voice clone already set up**, with your `ELEVEN_API_KEY` and
   `ELEVEN_VOICE_ID` filled into the real **`.env`** file (see "One-time setup"
   below). This is what lets quickVid narrate in your own voice. *(Only skippable
   if you never want a cloned-voice voiceover — i.e. you'll go silent or supply
   your own audio file.)*

---

## Get started (this is the whole thing)

Drag **this file (`ReadME.MD`) into the Claude console** and type:

> **let's get started**

The file you drag in selects the workflow: **`ReadME.MD`** (this file) for the general
photos-and-clips builder, or **`potterySkill.MD`** for the one-video "process reel"
format with flashing points. Both start with the same phrase — "let's get started" —
so the dragged-in file is what tells Claude which recipe to follow.
Claude reads this file and walks you through it — asking for your media, the reel
length, a title, whether you want a voiceover, captions, and a timer — then builds
the reel and saves it to `final/` with a date-and-time stamp.

That's the intended path. You can also run the steps by hand (see the bottom).

---

## What you get

- A **9:16 vertical** video (1080×1920), the format Instagram Reels expects.
- Your photos and clips stitched in the order you choose.
- A **length you pick** from four bands (max-reach 7-15s, sweet-spot 15-30s, deep
  30-60s, or long-form up to 20 min); flash speed and clip trimming are tuned to
  hit it and look good.
- An optional **title** overlaid on the reel.
- **Voiceover in YOUR own voice** (an ElevenLabs voice clone, set up once), or an
  audio file you already have, or no voiceover.
- Optional **burned-in captions** (auto from your script, or your own `.srt`) —
  ~85% of reels are watched muted.
- An optional **countdown timer** (1/100 s) — tell it how long the reel took to
  make; it starts there and ticks to 00:00.00 across the reel.
- **Music is left to Instagram** — add it in one tap on the upload screen (faster,
  and you get the licensed IG music library).
- Output to `final/reel_<date>_<time>.mp4`. Nothing is ever overwritten.

---

## The folders

```
quickVid/
├─ voice_sample/ ← ONE-TIME: drop a sample of your voice here to clone it
├─ media/        ← your photos & videos (Claude puts them here for you)
├─ aroll/        ← talking-head base video: phone selfie or HeyGen avatar clip
├─ broll/        ← b-roll clips used as timed overlay panels (optional)
├─ chips/        ← rendered hook-chip PNGs (make_chip.py output)
├─ voiceover/    ← your own voiceover audio (only if not using the clone)
├─ prompts/      ← script.txt, timeline .json, caption .srt files
├─ final/        ← finished reels appear here, date-time stamped
├─ tools/        ← PUT ffmpeg.exe + ffprobe.exe HERE (not shipped — see Prerequisites)
├─ make_reel.py          ← slideshow builder (length, title, captions, timer)
├─ compose_reel.py       ← talking-head compositor (overlays over an A-roll)
├─ make_chip.py          ← hook-text chips ("🚨 …") as transparent PNGs
├─ make_cards.py         ← 9:16 infographic cards (toolkit + per-video deck)
├─ script_fit.py         ← how many script words fit a given reel length
├─ add_timer.py          ← overlays a countdown timer after the reel is built
├─ elevenlabs_voice.py   ← voice-clone setup + turns a script into your voiceover
├─ requirements.txt
└─ .env.example          ← copy to .env; put your ELEVEN_API_KEY + voice id here
```

---

## One-time setup — your voice clone (only if you want voiceover)

quickVid narrates in **your own cloned voice**. Set this up once:

1. **Drop a voice sample** in **`voice_sample/`** — 1-5 min of you talking, clean
   audio (see the note in that folder).
2. **Create the clone** at **https://elevenlabs.io/app/voice-lab** → Add Voice →
   Instant Voice Clone → upload that sample → save.
3. **Add your API key** — copy `.env.example` to **`.env`** and set
   `ELEVEN_API_KEY=...` (from https://elevenlabs.io/app/settings/api-keys).
   **`.env` is the one place your key goes.**
4. **Verify + get your voice id:**
   ```
   python elevenlabs_voice.py --check
   ```
   Confirms the key, shows remaining characters, lists your voices. Copy your
   clone's `voice_id`.
5. **Save it** in `.env` as `ELEVEN_VOICE_ID=...`, then re-run `--check` until it
   says **SETUP COMPLETE**.

(Prefer no voiceover, or already have an audio file? You can skip this.)

---

## FOR CLAUDE — run this when the user drags in `ReadME.MD` and says "let's get started"

**Have a short conversation, one topic at a time. Ask before generating; don't
assume. Use sensible defaults and keep it moving.**

**Which builder?** This flow (steps 0-9) is the **slideshow** path: photos and
clips flashed in sequence by `make_reel.py`. If the user wants the
**talking-head / creator format** — a person (or their HeyGen avatar) on camera
the whole time, with cards, b-roll and a hook chip layered over them — skip to
**"FOR CLAUDE — talking-head recipe"** further down instead.

### 0. Preflight — make sure ffmpeg is installed
Before anything else, confirm `tools/ffmpeg.exe` and `tools/ffprobe.exe` exist
(they're not shipped in the repo). If **either is missing**, stop and ask the user
to install them — the build can't run without them. Point them to the easiest path
and offer to help:
- **Recommended:** `winget install Gyan.FFmpeg`, then copy `ffmpeg.exe` +
  `ffprobe.exe` into `tools/`; **or**
- Download the "essentials" build from https://www.gyan.dev/ffmpeg/builds/, unzip,
  and copy the two `.exe`s from its `bin/` into `tools/`.

Re-check that both files are present before continuing. Don't start the media step
until ffmpeg is in place.

### 1. Media — get it into `media/`
**Always ask which file(s) to use at the start of every session — even if `media/`
already has files in it.** Leftover media from a previous reel may still be sitting
in `media/`; never silently reuse whatever happens to be there. First list anything
already in `media/` and ask the user whether to use it, add to it, or clear it —
then remove whatever they don't want so only the chosen files remain before you build.

Ask the user for the **paths or links** to the photos/videos they want (a folder,
a list of files, or URLs). Then:
- Copy/move them into `media/`, renaming with numeric prefixes (`01_`, `02_`, …)
  to set play order. For local paths use `cp`; for URLs download them. For a shared
  Google Drive **folder**, `gdown --folder <url>` pulls every file at once (needs
  `beautifulsoup4`).
- **Play order is whatever the user wants** — it's just the numeric prefix, so you
  can honor any request: "put the sunset first," "these three at the end," a fully
  custom sequence, etc. The user can also **reuse the same image in more than one
  slot** — e.g. "make IMG_3111 the first *and* last frame" → copy it to both `01_`
  and the final prefix so it bookends the reel. Duplicating a file under two
  prefixes is fine; each prefix is an independent slot.
- List what's now in `media/` back to the user in play order and confirm the order
  is right (offer to reorder, duplicate, or drop any by renaming).
- Supported — photos: `.jpg .jpeg .png .webp`; videos: `.mp4 .mov .m4v .webm`.
- **Screen recordings / landscape content:** if the user's media is a screen capture
  or any landscape (16:9 or wider) source, add `--fit` to the build command. This
  fits the content inside the 9:16 frame with black bars instead of cropping into it.

### 2. Length — the type of reel
Ask, offering four options:

> **How long should the reel be?**
> 1. **Max reach (7-15s)** — fastest cuts; discovery / hook-and-go.
> 2. **Sweet spot (15-30s, recommended)** — the highest-performing Reel length.
> 3. **Deep engagement (30-60s)** — room for a fuller story.
> 4. **Long form (60s-20min)** — the user names the exact length.

**You decide the pacing to hit the length and look good** (per-case judgement):
pick a concrete target (midpoint of the band, or the user's number) to pass as
`--target-seconds <N>`, and decide video truncation with `--max-clip-seconds`
(short bands + long clips → trim to ~2-4s each; longer bands → keep clips fuller).
Sanity-check with `python script_fit.py --target <N>` — it recommends the flash
speed and warns about too much / too little media.

### 3. Title
Ask: **"Want a title overlaid on the reel? If so, what should it say?"** If yes,
pass `--title "<text>"`. Default shows for the first 3s at the top; offer
`--title-seconds 0` (whole reel) or `--title-position middle` if they want.

### 4. Voiceover — is it needed?
Ask: **"Do you want a voiceover?"**
- **Yes, my cloned voice (default):**
  - Run `python elevenlabs_voice.py --check`. If it doesn't say SETUP COMPLETE,
    walk them through the one-time setup (voice sample → clone at
    https://elevenlabs.io/app/voice-lab → `ELEVEN_API_KEY` + `ELEVEN_VOICE_ID` in
    `.env`). Don't generate until `--check` passes.
  - **Tell the user the word budget before asking for the script.** From the
    chosen length, quote the target at ~150 wpm so they write to the right size —
    e.g. "A 12s reel fits **about 30 words** (~26-33); send me your script and I'll
    check it." Rough guide: 7-15s → ~18-37 words, 15-30s → ~37-75, 30-60s →
    ~75-150, then ~150 words per added minute. Run `script_fit.py --target <N>`
    for the exact budget for the picked length.
  - Get the script into `prompts/script.txt` (ask for the words, or write what
    they dictate).
  - **Check it fits (step 6 below), then** generate:
    `python elevenlabs_voice.py --script prompts/script.txt`
    → writes `voiceover/vo_eleven.mp3`. It prints the **characters used / cost** —
    relay that. Add `--style energetic|authoritative` if they want a different read.
  - Build with `--sound voiceover`.
- **Yes, a file I have:** confirm an audio file is in `voiceover/` (or ask its
  path); build with `--sound voiceover`.
- **No:** build with `--sound none`; remind them music is added on Instagram.

### 5. Captions (offer — recommended)
Ask: **"Add burned-in captions? (recommended — most reels are watched muted.)"**
- **From the script** → `--subtitles auto` (uses `prompts/script.txt`).
- **From my `.srt`** → `--subtitles file --sub-file "<path>"`.
- **No** → skip.

### 6. Script-fit check (whenever a script drives voiceover or auto-captions)
Before generating a voiceover or auto-captions, run
`python script_fit.py --target <N>`. It reports the reel length, the **word
budget** (~150 wpm), and whether `prompts/script.txt` fits. If it's too long, tell
the user the budget and **offer to summarize** the script down to fit (keep the
hook and CTA), rewrite `prompts/script.txt`, and re-check.

### 7. Countdown timer — ask BEFORE building
**Ask this before the build**, so the timer is baked into the same render (one
file, no second pass): **"How long did it take you to create this? I can overlay a
countdown that starts there and ticks to `00:00.00` across the reel — or skip it."**
- **If they give a time** → add `--timer --timer-seconds <e.g. 23:00 or 1380>` to
  the build flags in step 8. (Counts down by default; `--timer-direction up` counts
  up. Top-center by default so it clears the title/captions.)
- **If they skip** → no timer flags.
- Only fall back to `add_timer.py` (below) if the reel was *already* built and they
  decide they want a timer after the fact.

### 8. Build
Assemble the flags from the answers (including any timer flags from step 7) and run
`make_reel.py` with `C:\Users\DKYLE\.conda\envs\api\python.exe` (falls back to
`python`). Example:
```
python make_reel.py --sound voiceover --target-seconds 22 --max-clip-seconds 3 \
    --title "MY EPIC TRIP" --subtitles auto --timer --timer-seconds 23:00
```

### 9. Report
Give the output path (`final/reel_<stamp>.mp4`), its length, and the `Built in:`
time; if silent, remind them to add music on Instagram. If they included a timer,
confirm it's counting from their time.

**After-the-fact timer (only if the reel was already built without one):**
```
python add_timer.py --seconds <e.g. 23:00 or 1380>
```
It reads the newest reel and writes a new `reel_<stamp>_timer.mp4` (original
untouched). Report the new path.

Every step writes a new timestamped file — nothing is overwritten.

---

## Reel length & pacing

Pick a band; the tool tunes photo-flash speed (and clip trimming if you ask) to
hit it. Longer target = slower, lingering cuts; shorter = faster flashes.

| Band | Length | Feel |
|------|--------|------|
| Max reach | 7-15s | Fast, punchy; built for the scroll |
| Sweet spot (recommended) | 15-30s | Highest-performing Reel length |
| Deep engagement | 30-60s | Room for a fuller story |
| Long form | 60s-20min | You name the exact length |

- Build to a target: `make_reel.py --target-seconds 22` (add `--max-clip-seconds 3`
  to trim clips). Photos flash no faster than 0.4s and hold no longer than 8s;
  within that the target is matched exactly.
- Plan first (no render): `script_fit.py --band sweet-spot` (or `--target 22`).

---

## The countdown timer, explained

Tell it how long the reel took to make; it starts the clock there and runs it to
zero across the whole reel, precise to the hundredth of a second.

- **"This reel took 23 minutes" on a 45s reel** → shows `23:00.00` on the first
  frame, `11:30.00` at the halfway point, `00:00.00` at the end. The 23-minute span
  is compressed into the reel's 45 seconds.
- If you don't give a time, it counts down from the reel's own length.
- Add it after building (`add_timer.py`) or in the same build (`make_reel.py
  --timer`). Top-center by default so it never collides with the title or captions.
  `--direction up` (or `--timer-direction up`) counts up instead.
- Whenever the timer is shown, the label **"Estimated Time to Create"** is drawn
  directly above it, so viewers know what the running clock represents.

---

## Talking-head reels — the creator format (`compose_reel.py` + `make_chip.py`)

`make_reel.py` **concatenates**: one clip at a time, source audio dropped. The
reels that consistently outperform are built the other way around — they
**composite**: a person talks to camera full-screen for the whole reel (the
**A-roll**), and the evidence slides in as timed panels *over* them. Notes
from comparing a top-performing talking-head wildfire explainer against a
cards-only slideshow of the same story:

- **A face + continuous voice is the retention engine.** Faces stop the
  scroll; speech sets the pace so the viewer never decides to keep watching.
  A silent slideshow asks the viewer to *read* — that's work, and they swipe.
- **Something must move every few seconds.** A static card held 13s is an
  eternity; the same card as a 6s panel over a talking head is a highlight.
- **The hook is decided in the first 2 seconds**: dramatic first frame plus a
  text chip like "🚨 Nobody is Talking About This".
- **Receipts beat polish**: real footage, live maps and raw charts read as
  credible. Keep the polished cards — but layer them over a human voice.

### Get an A-roll (two ways)

1. **Record yourself**: phone camera, 9:16 portrait, good light, mic close,
   talking the script straight into the lens.
2. **HeyGen avatar clone**: paste the script into HeyGen (your avatar + your
   cloned voice), portrait/9:16 output, download the .mp4. If Claude has the
   HeyGen connector, it can drive this from the script directly.

Drop the file in **`aroll/`**. Its speech is **kept** and loudness-normalized;
its length *is* the reel's length (~150 words of script per minute).

### Hook chips

```
python make_chip.py --text "🚨 Nobody is Talking About This"
```

Renders a transparent PNG chip — rounded dark lozenge, Segoe UI Black, real
color emoji — into `chips/`. `--style light` inverts it; `--fontsize` /
`--max-width` tune size and wrapping. Timelines can also render chips inline
(`"type": "chip"`) so you rarely run this by hand.

### The timeline (what plays over the A-roll, and when)

A JSON file (see `prompts/timeline_example.json`):

```json
{
  "aroll": "aroll/take1.mp4",
  "overlays": [
    { "type": "chip",  "text": "🚨 Nobody is Talking About This",
      "start": 0.4, "end": 4.5, "pos": "upper" },
    { "type": "video", "file": "broll/smoke.mp4", "from": 3,
      "start": 4.5, "end": 10, "pos": "top", "width": 1.0, "height": 0.38,
      "slide": "top", "fade": 0.3 },
    { "type": "image", "file": "cards/card1.png",
      "start": 11, "end": 18, "pos": "center", "height": 0.55 }
  ]
}
```

Overlay fields: `start`/`end` (seconds on screen) · `pos` = `top / upper /
center / lower / bottom` (or `x`/`y` fractions 0-1) · `width`/`height` as
fractions of the frame — give **both** to cover-crop into that box (the
full-width band over a talking head), give **one** to keep the media's own
aspect (a whole card, scaled) · `fade` seconds (default 0.25) · `slide` =
`top/bottom/left/right` ease-in · `from` = source offset for video clips.
Top-level extras: `"voice"` (audio file that replaces the a-roll's track),
`"music"` (`{"file", "gain_db", "duck"}` — a bed auto-ducked under speech),
`"loudnorm"` (default true), `"fit"` (letterbox the a-roll instead of crop).

### Build it

```
python compose_reel.py prompts/timeline.json
python compose_reel.py prompts/timeline.json --srt prompts/captions.srt
```

Output: `final/composed_<datetime>.mp4` (1080x1920, 30 fps, audio kept).
`--srt` burns captions in the same style as `make_reel.py`.

### Sourcing B-roll — filling `broll/`

Drop any `.mp4/.mov` into `broll/` and reference it from the timeline. Two
things make sourcing easy: the cover-crop band means **landscape footage works
fine** (a 16:9 clip cropped into a top band loses little), and the `"from"`
field pulls the best 5 seconds out of any long clip. Where to find footage,
in order of preference:

1. **Screen-record public dashboards and live sites** — the most credible
   asset there is, and free. Government data portals, live tracker maps
   (wildfires, flights, earthquakes, weather), official rankings and price
   boards: open the page in a browser and screen-record it (Windows:
   Win+Alt+R Game Bar; or record your phone scrolling the site). Leave the
   site's own logo, timestamp and legend in frame — the raw UI chrome is
   what makes it read as a *receipt*, not a graphic. Claude can automate
   these captures with a browser.
2. **Free licensed stock** — Pexels (pexels.com), Pixabay (pixabay.com),
   Mixkit (mixkit.co): free for commercial use, no attribution required,
   searchable by keyword ("wildfire aerial", "city timelapse"...). Filter
   vertical if you can, but landscape is fine (see above). Both Pexels and
   Pixabay have free APIs if you want fetching scripted.
3. **Public-domain government footage** — U.S. federal agency footage is
   generally public domain: NASA (images.nasa.gov), USFS/BLM/National
   Interagency Fire Center, NOAA, the National Archives. Slower to search
   than stock, but often the most dramatic real-event footage you can use
   with zero rights risk.
4. **Viral / eyewitness clips — caution.** Commentary creators repost these
   constantly and it clearly performs, but it's someone else's copyrighted
   footage: a strike risk on an account you're growing, especially
   monetized. Prefer a stock or public-domain equivalent of the same shot;
   if a specific clip is irreplaceable, credit the source on screen and keep
   it short inside your own commentary — and know it can still be struck.
5. **Charts: plot the data yourself** instead of screenshotting someone's
   graphic. Public datasets (government statistics portals, agency
   databases) + matplotlib or the `make_cards.py` toolkit give you a clean
   chart you own — cite the dataset on the card face, like the source
   footers the cards already use.

---

## FOR CLAUDE — talking-head recipe (user wants the creator format)

1. **Script first.** Ask for the topic and hook. Word budget = target length
   × ~150 wpm (a 60s reel ≈ 150 words). Write/collect the script into
   `prompts/script.txt`. The first sentence must be the hook.
2. **Get the A-roll.** Ask: **"Record yourself reading it, or generate it
   with your HeyGen clone?"** For HeyGen: give the user the final script to
   paste (or drive the HeyGen connector if available) — portrait 9:16 —
   and have the .mp4 land in `aroll/`. Don't proceed without the A-roll;
   everything is timed against it.
3. **Build the assets** while/after the A-roll is made: a card deck
   (`make_cards.py` — swap the DECK half), b-roll clips into `broll/`
   (see "Sourcing B-roll" above — prefer dashboard screen-captures, free
   stock, and public-domain agency footage; warn before using viral clips),
   chip text(s) agreed with the user.
4. **Write the timeline** to `prompts/timeline_<topic>.json`, timed against
   the script at ~150 wpm (or probe the A-roll for its real length). Rules of
   thumb: hook chip at ~0.4-4.5s; first panel on screen by ~5s; something new
   every 4-7s; no overlay longer than ~8s; panels in `top`/`upper`/`center`
   so they clear the caption band; face visible at least a third of the time.
5. **Compose** with `compose_reel.py`. Offer burned-in captions: hand-write a
   `.srt` cued to the script (most viewers are muted) and pass `--srt`.
6. **Report** the output path and length; remind that music can be added on
   Instagram if no bed was mixed in.

---

## Infographic / data cards (`make_cards.py`)

9:16 cards (1080x1920) drawn with PIL at 2x and downsampled. The file is two
halves: a reusable **TOOLKIT** (background, header/footer chrome, panels,
stat rows, spline/tapered-limb primitives, a small map projection, icons) and
a per-video **DECK** (the `card_*()` functions). To make cards for a new
reel, replace only the DECK half and re-run `python make_cards.py [out_dir]`.
Keep text minimal (the toolkit's `header` + `stat_row` + one `para` is a full
card); put years/dates only in source footers so card faces don't date. Use
the cards as slideshow frames (`make_reel.py`) or as timed panels over a
talking head (`compose_reel.py`).

---

## Run it yourself (optional — no Claude needed)

```powershell
# one-time: install the two small deps
C:\Users\DKYLE\.conda\envs\api\python.exe -m pip install -r requirements.txt

# one-time: verify your ElevenLabs voice clone (key, clone, voice id)
C:\Users\DKYLE\.conda\envs\api\python.exe elevenlabs_voice.py --check

# plan a length: recommend flash speed for a sweet-spot (15-30s) reel
C:\Users\DKYLE\.conda\envs\api\python.exe script_fit.py --band sweet-spot

# default flow: narrate prompts/script.txt in your cloned voice, then build 22s
C:\Users\DKYLE\.conda\envs\api\python.exe script_fit.py --target 22   # does the script fit?
C:\Users\DKYLE\.conda\envs\api\python.exe elevenlabs_voice.py --script prompts/script.txt
C:\Users\DKYLE\.conda\envs\api\python.exe make_reel.py --sound voiceover --target-seconds 22 --title "MY TITLE"

# silent 12s max-reach reel: trim long clips to 3s, add auto captions
C:\Users\DKYLE\.conda\envs\api\python.exe make_reel.py --sound none --target-seconds 12 --max-clip-seconds 3 --subtitles auto

# screen recording / landscape content: fit inside the frame with black bars
C:\Users\DKYLE\.conda\envs\api\python.exe make_reel.py --sound none --target-seconds 60 --max-clip-seconds 60 --speed-to-fit --fit --title "My Title"

# AFTER building: overlay a countdown of how long it took you to make it
C:\Users\DKYLE\.conda\envs\api\python.exe add_timer.py --seconds 23:00
```

Useful `make_reel.py` flags: `--target-seconds 22` (hit a length) or
`--image-seconds 4` (fixed per-photo time); `--max-clip-seconds 6` (trim clips);
`--title "..."` with `--title-seconds` / `--title-position`; `--subtitles auto|file`;
`--timer` with `--timer-seconds`; `--no-ken-burns`; `--fit-audio`;
`--fit` (screen recordings / landscape content — letterbox instead of crop);
`--speed-to-fit` (with `--max-clip-seconds`: speed up to fit duration rather than cut).

---

## Notes & limits

- Source-clip audio is dropped so the reel has one clean soundtrack (silence or
  your voiceover). Want spoken audio? Use a voiceover. Want music? Use Instagram.
- Keep reels under ~90s for the Instagram feed (long-form supports up to 20 min).
- The bundled `tools/ffmpeg.exe`/`ffprobe.exe` cover the video side; the voiceover
  needs `requests` + `python-dotenv` (in `requirements.txt`).
- Voiceover cost is per character (ElevenLabs); each generation prints characters
  used and your remaining quota. Set `ELEVEN_USD_PER_1K_CHARS` in `.env` for a `$`
  estimate.
