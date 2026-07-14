# potterySkill — One video → a calm, "process" Instagram Reel with flashing points

A standalone recipe for a specific kind of Reel: **one continuous video** (satisfying,
process-y footage — think a pottery wheel spinning, hands centering clay, a smooth
screen recording) turned into a finished **9:16 Instagram Reel**, in your own voice,
with a title and — the star of this format — **short text "points" that flash on-screen
one at a time, timed to land exactly when the voiceover mentions them**, sitting in a
safe zone so they never obscure the action.

If you want the general photos-and-clips reel builder, use **ReadME.MD** instead. This
file is the same engine (`make_reel.py`), pointed at a narrower, higher-polish format.

**What makes this format different from the base README:**
- **One video, looped.** You bring a single clip. If it's shorter than the reel
  length, it's **looped seamlessly** to fill the whole thing (`--loop-to-target`).
- **Timed on-screen points.** In addition to the title, a series of short lines
  **fade in and out at cue times you set**, aligned to the narration, placed in the
  upper third so the center of frame (the wheel, the hands, the screen) stays clear
  (`--points`). This is separate from bottom captions and from the title.

---

## Prerequisites (three things)

1. **Claude in VS Code, with this repo open.** The scripts are already in this folder.
2. **ffmpeg + ffprobe in `tools/`.** Not shipped in the repo (too large). Put
   `ffmpeg.exe` and `ffprobe.exe` in the **`tools/`** folder before building — download
   from https://www.gyan.dev/ffmpeg/builds/ (grab the "essentials" build, unzip, copy
   the two `.exe`s from its `bin/` into `tools/`), or `winget install Gyan.FFmpeg`.
   Claude checks for these and will walk you through it if they're missing.
3. **An ElevenLabs voice clone already set up**, with your `ELEVEN_API_KEY` and
   `ELEVEN_VOICE_ID` filled into the real **`.env`** file (see "One-time setup" below).
   This is what lets it narrate in your own voice. *(Only skippable if you never want a
   cloned-voice voiceover — i.e. you'll go silent or supply your own audio file.)*

---

## Get started (this is the whole thing)

Drag **this file (`potterySkill.MD`) into the Claude console** and type:

> **let's get started**

The file you drag in selects the workflow: **`potterySkill.MD`** for this one-video
"process reel" format (flashing points, looped clip), or **`ReadME.MD`** for the
general photos-and-clips builder. Both start with the same phrase — "let's get
started" — so the dragged-in file is what tells Claude which recipe to follow.
Claude reads this file and walks you through it — asking for your **one video**, the
reel length, a title, your **script and the points to flash**, whether you want a
voiceover and captions, and a timer — then loops the video to length, burns everything
in, and saves to `final/` with a date-and-time stamp.

That's the intended path. You can also run the steps by hand (see the bottom).

---

## What you get

- A **9:16 vertical** video (1080×1920), the format Instagram Reels expects.
- **Your one clip looped** to the length you pick — no gaps, no freeze-frame.
- An optional **title** for the first few seconds.
- **Flashing on-screen points** — short lines that fade in/out at their cue times,
  in the upper third so they clear the subject in the center of frame.
- **Voiceover in YOUR own voice** (an ElevenLabs voice clone), or an audio file you
  already have, or no voiceover.
- Optional **burned-in bottom captions** (auto from your script, or your own `.srt`).
- An optional **countdown timer** (1/100 s) showing how long the reel took to make.
- **Music is left to Instagram** — add it in one tap on the upload screen.
- Output to `final/reel_<date>_<time>.mp4`. Nothing is ever overwritten.

---

## The folders

```
quickVid/
├─ voice_sample/ ← ONE-TIME: drop a sample of your voice here to clone it
├─ media/        ← your ONE video goes here (Claude puts it there for you)
├─ voiceover/    ← your own voiceover audio (only if not using the clone)
├─ prompts/      ← script.txt (narration/captions) + points.txt (flashing points)
├─ final/        ← finished reels appear here, date-time stamped
├─ tools/        ← PUT ffmpeg.exe + ffprobe.exe HERE (not shipped — see Prerequisites)
├─ make_reel.py          ← builds the reel (loop, title, points, captions, timer)
├─ script_fit.py         ← how many script words fit a given reel length
├─ add_timer.py          ← overlays a countdown timer after the reel is built
├─ elevenlabs_voice.py   ← voice-clone setup + turns a script into your voiceover
├─ requirements.txt
└─ .env.example          ← copy to .env; put your ELEVEN_API_KEY + voice id here
```

---

## One-time setup — your voice clone (only if you want voiceover)

Narration is in **your own cloned voice**. Set this up once:

1. **Drop a voice sample** in **`voice_sample/`** — 1-5 min of you talking, clean audio.
2. **Create the clone** at **https://elevenlabs.io/app/voice-lab** → Add Voice →
   Instant Voice Clone → upload that sample → save.
3. **Add your API key** — copy `.env.example` to **`.env`** and set `ELEVEN_API_KEY=...`
   (from https://elevenlabs.io/app/settings/api-keys). **`.env` is the one place your
   key goes.**
4. **Verify + get your voice id:** `python elevenlabs_voice.py --check` — confirms the
   key, shows remaining characters, lists your voices. Copy your clone's `voice_id`.
5. **Save it** in `.env` as `ELEVEN_VOICE_ID=...`, then re-run `--check` until it says
   **SETUP COMPLETE**.

(Prefer no voiceover, or already have an audio file? You can skip this.)

---

## FOR CLAUDE — run this when the user drags in `potterySkill.MD` and says "let's get started"

**Have a short conversation, one topic at a time. Ask before generating; don't assume.
Use sensible defaults and keep it moving.** This format is calm and deliberate — the
default vibe is meditative, not hype.

### 0. Preflight — make sure ffmpeg is installed
Confirm `tools/ffmpeg.exe` and `tools/ffprobe.exe` exist (not shipped in the repo). If
**either is missing**, stop and point the user to the easiest path (`winget install
Gyan.FFmpeg`, then copy both `.exe`s into `tools/`; **or** the "essentials" build from
https://www.gyan.dev/ffmpeg/builds/). Re-check both are present before continuing.

### 1. The video — get the ONE clip into `media/`
**Always ask which file(s) to use at the start of every session — even if `media/`
already has a clip in it.** A leftover video from a previous reel may still be sitting
in `media/`; never silently reuse whatever happens to be there. First list anything
already in `media/` and ask the user whether to use it or replace it — then remove
whatever they don't want so only the chosen clip(s) remain before you build.

Ask for the **path or link** to the single video (a satisfying, continuous process
shot works best). Then:
- Copy/move it into `media/` as `01_<name>.ext`. For a local path use `cp`; for a URL
  download it; for a Google Drive **folder** use `gdown --folder <url>`.
- This format expects **one video**. If the user brings 2-3 short clips they want in
  sequence, that's fine — prefix `01_`, `02_`, `03_` and the whole sequence loops as a
  unit. Confirm the order.
- Supported videos: `.mp4 .mov .m4v .webm`.
- **Screen recordings / landscape content:** if the clip is a screen capture or any
  landscape (16:9 or wider) source, add `--fit` so it's letterboxed inside the 9:16
  frame instead of cropped. (Pottery-wheel footage shot vertically won't need this.)

### 2. Length — the type of reel
Ask, offering four options (this format's sweet spot is **30-45s**):

> **How long should the reel be?**
> 1. **Max reach (7-15s)** — fastest; discovery / hook-and-go.
> 2. **Sweet spot (15-30s)** — highest-performing Reel length.
> 3. **Deep engagement (30-45s, recommended for this format)** — room for the full
>    process arc and all your points to breathe.
> 4. **Long form (up to 20 min)** — the user names the exact length.

Pick a concrete target (midpoint, or the user's number) to pass as `--target-seconds
<N>`. **Because there's one looped video, you almost always want `--loop-to-target`**
so the clip fills the whole length. (No `--max-clip-seconds` here — you're looping to
extend, not trimming to shorten.)

### 3. Title
Ask: **"Want a title for the first few seconds? e.g. 'Throwing a Reel on the AI
Wheel'."** If yes, pass `--title "<text>"`. Default shows the first 3s at the top
(`--title-seconds 0` for the whole reel; `--title-position middle` to center it). Keep
it short so it clears the first flashing point.

### 4. The script + the points — the heart of this format
This is the extra step versus the base README. You need **two aligned things**:

**a) The narration script** → `prompts/script.txt` (drives the voiceover and/or the
   bottom captions). Tell the user the **word budget first** so they write to size —
   at ~150 wpm: 15-30s ≈ 37-75 words, 30-45s ≈ 75-115 words. Run `python script_fit.py
   --target <N>` for the exact budget.

**b) The flashing points** → `prompts/points.txt`. One point per line, in the format:

```
# prompts/points.txt — one point per line:  START-END | TEXT
# START/END accept  SS  |  SS.cc  |  MM:SS  |  HH:MM:SS
0:00-0:03  | Raw clips → Polished Reel
0:03-0:06  | Claude (in VS Code)
0:06-0:09  | VS Code
0:09-0:12  | github.com/dkyol/quickvid
0:22-0:30  | github.com/dkyol/quickvid
```

- **Time each point to the moment its idea is spoken.** Read the script, estimate when
  each key line lands (~150 wpm ≈ 2.5 words/sec), and set START to just before it. Keep
  each point on screen ~2-4s. It's fine to repeat a point (e.g. the repo URL near the
  CTA), and fine to leave gaps where no point shows.
- **Keep them short** — a few words each; they're glanceable, not paragraphs. Long
  lines wrap and start to crowd the frame.
- Points fade in/out and sit in the **upper third** by default (`--points-position
  top`), clear of the centered subject and of any bottom captions. Use
  `--points-position bottom` or `middle` only if the footage's dead space is elsewhere.
- **Offer to draft `points.txt` for the user** from their script — pull out the 3-6
  key beats (tools named, the payoff, the CTA/link) and propose timings, then let them
  adjust.

### 5. Voiceover — is it needed?
Ask: **"Do you want a voiceover?"**
- **Yes, my cloned voice (default):** Run `python elevenlabs_voice.py --check`. If it
  doesn't say SETUP COMPLETE, walk them through the one-time setup. Get the script into
  `prompts/script.txt`, **check it fits (step 7), then** generate:
  `python elevenlabs_voice.py --script prompts/script.txt` → writes
  `voiceover/vo_eleven.mp3` and prints characters used / cost (relay it). For this
  format add `--style calm` if available, else the default read; the vibe is steady and
  unhurried. Build with `--sound voiceover`.
- **Yes, a file I have:** confirm an audio file is in `voiceover/`; build `--sound
  voiceover`.
- **No:** build `--sound none`; remind them music is added on Instagram.

**Aligning voice length to the loop:** set `--target-seconds` to roughly the voiceover
length so the looped video and the narration end together. If the voiceover runs a bit
long, either trim the script or add `--fit-audio`.

### 6. Bottom captions (offer — optional here)
The flashing points are already carrying the on-screen text, so bottom captions are
**optional** for this format (they can compete with the points). If the user wants them
anyway (most reels are watched muted):
- **From the script** → `--subtitles auto` (uses `prompts/script.txt`).
- **From my `.srt`** → `--subtitles file --sub-file "<path>"`.
- **No** → skip. Points stay the sole on-screen text.

### 7. Script-fit check (whenever a script drives voiceover or auto-captions)
Before generating, run `python script_fit.py --target <N>`. It reports the reel length,
the **word budget** (~150 wpm), and whether `prompts/script.txt` fits. If it's too
long, tell the user the budget and **offer to summarize** it to fit (keep the hook and
CTA), rewrite `prompts/script.txt`, re-check — and re-time `points.txt` to match.

### 8. Countdown timer — ask BEFORE building
**Ask before the build** so it's baked into the same render: **"How long did it take
you to create this? I can overlay a countdown that starts there and ticks to `00:00.00`
across the reel — or skip it."**
- **If they give a time** → add `--timer --timer-seconds <e.g. 23:00 or 1380>`.
- **If they skip** → no timer flags.
- Only fall back to `add_timer.py` if the reel was *already* built.

### 9. Build
Assemble the flags and run `make_reel.py` with `C:\Users\DKYLE\.conda\envs\api\python.exe`
(falls back to `python`). Example (the pottery concept, ~30s):
```
python make_reel.py --sound voiceover --target-seconds 30 --loop-to-target \
    --title "THROWING A REEL ON THE AI WHEEL" \
    --points prompts/points.txt --points-position top \
    --timer --timer-seconds 15:00
```

### 10. Report
Give the output path (`final/reel_<stamp>.mp4`), its length, and the `Built in:` time;
if silent, remind them to add music on Instagram. Confirm the points landed where
intended and, if a timer was used, that it's counting from their time.

**After-the-fact timer (only if the reel was already built without one):**
```
python add_timer.py --seconds <e.g. 15:00 or 900>
```
Reads the newest reel, writes a new `reel_<stamp>_timer.mp4` (original untouched).

Every step writes a new timestamped file — nothing is overwritten.

---

## The flashing points, explained

`--points prompts/points.txt` burns short lines that **fade in and out at cue times you
set**, one at a time. They're distinct from the title (a single headline) and from
captions (the bottom band):

- **Placement:** upper third by default (`--points-position top`), so a centered
  subject — hands on a wheel, a screen recording, a face — stays unobscured. `middle`
  and `bottom` are available for footage whose dead space is elsewhere.
- **Timing:** each line is `START-END | TEXT`; it appears from START to END with a
  ~250 ms fade on each side. Times accept `SS`, `SS.cc`, `MM:SS`, or `HH:MM:SS`.
- **Styling:** white, bold, thick black outline (readable over any footage), font size
  52 by default (`--points-fontsize`).
- **Rule of thumb:** 3-6 points across a 30s reel, each 2-4s on screen, cued just
  before the narration says the thing. Repeat the CTA/link near the end.

---

## Reel length & pacing (looping edition)

Pick a length; with one video the clip is **looped to fill it** (`--loop-to-target`).
Longer target = the same footage cycles more times.

| Band | Length | Feel |
|------|--------|------|
| Max reach | 7-15s | Fast, punchy; built for the scroll |
| Sweet spot | 15-30s | Highest-performing Reel length |
| Deep engagement (recommended) | 30-45s | Full process arc; room for every point |
| Long form | 45s-20min | You name the exact length |

- Loop to a target: `make_reel.py --target-seconds 30 --loop-to-target`.
- Plan first (no render): `script_fit.py --target 30`.

---

## The countdown timer, explained

Tell it how long the reel took to make; it starts the clock there and runs it to zero
across the whole reel, precise to the hundredth of a second. Label **"Estimated Time to
Create"** is drawn just above it. Top-center by default so it never collides with the
title, points, or captions. `--timer-direction up` counts up instead. If you don't give
a time, it counts down from the reel's own length.

---

## Run it yourself (optional — no Claude needed)

```powershell
# one-time: install the two small deps
C:\Users\DKYLE\.conda\envs\api\python.exe -m pip install -r requirements.txt

# one-time: verify your ElevenLabs voice clone (key, clone, voice id)
C:\Users\DKYLE\.conda\envs\api\python.exe elevenlabs_voice.py --check

# does the script fit a 30s reel?
C:\Users\DKYLE\.conda\envs\api\python.exe script_fit.py --target 30

# narrate the script in your cloned voice
C:\Users\DKYLE\.conda\envs\api\python.exe elevenlabs_voice.py --script prompts/script.txt

# build: one video looped to 30s, title, timed points, voiceover
C:\Users\DKYLE\.conda\envs\api\python.exe make_reel.py --sound voiceover --target-seconds 30 ^
    --loop-to-target --title "THROWING A REEL ON THE AI WHEEL" --points prompts/points.txt

# silent version, screen-recording footage letterboxed, points at top
C:\Users\DKYLE\.conda\envs\api\python.exe make_reel.py --sound none --target-seconds 30 ^
    --loop-to-target --fit --points prompts/points.txt

# AFTER building: overlay a countdown of how long it took you to make it
C:\Users\DKYLE\.conda\envs\api\python.exe add_timer.py --seconds 15:00
```

Flags most relevant to this format: `--loop-to-target` (loop the one video to
`--target-seconds`); `--points <file>` with `--points-position top|middle|bottom` and
`--points-fontsize`; `--title "..."` with `--title-seconds` / `--title-position`;
`--sound voiceover|none`; `--subtitles auto|file`; `--timer` with `--timer-seconds`;
`--fit` (screen recordings / landscape); `--no-ken-burns` (n/a for pure video).

---

## A worked example — "Throwing a Reel on the AI Wheel"

The reference concept for this format. Calm, meditative, ~30s. One continuous
pottery-wheel clip (hands centering clay), looped to length.

**`prompts/script.txt`** (voiceover, ~75 words):

> Creating Reels doesn't have to feel like wrestling with editing software. You only
> need three things: a Claude account running right inside VS Code, VS Code itself, and
> this GitHub repo — dkyol/quickvid. It already has the README, prompts, and the Python
> for stitching clips, captions, voice-overs, and timers. So Claude never re-writes the
> same assembly code. Bring your clip, say the words, and watch it take shape. Your next
> Reel is already waiting to be thrown.

**`prompts/points.txt`** (flashing points, cued to the narration):

```
0:00-0:03  | Raw clips → Polished Reel
0:04-0:07  | Claude (in VS Code)
0:07-0:10  | VS Code
0:10-0:14  | github.com/dkyol/quickvid
0:22-0:30  | github.com/dkyol/quickvid
```

**Build:**
```
python make_reel.py --sound voiceover --target-seconds 30 --loop-to-target ^
    --title "THROWING A REEL ON THE AI WHEEL" --title-seconds 3 ^
    --points prompts/points.txt --points-position top
```

**Instagram caption (copy-paste):**

> Throwing a Reel on the AI wheel 🏺✨
>
> No more wrestling with editing software or burning tokens rewriting the same
> boilerplate every video. Just three things:
> 1. Claude (inside VS Code)  2. VS Code  3. github.com/dkyol/quickvid
>
> The repo already has the README, prompts, and ready Python scripts for stitching,
> captions, ElevenLabs voice-overs, and timers. Claude just orchestrates — you shape
> the vision. Drop your clip, give it a prompt, and watch it come together.
>
> Link in bio + comment "quickvid" for the starter prompt I use. Who else is tired of
> repetitive video setup work?

---

## Notes & limits

- Source-clip audio is dropped so the reel has one clean soundtrack (silence or your
  voiceover). Want music? Add it on Instagram.
- The loop is a plain repeat of the clip; for the smoothest cycle, use footage whose
  first and last frames are similar (a wheel mid-spin loops better than a clip that
  ends on a hard stop).
- Keep reels under ~90s for the Instagram feed (long-form supports up to 20 min).
- Voiceover cost is per character (ElevenLabs); each generation prints characters used
  and remaining quota. Set `ELEVEN_USD_PER_1K_CHARS` in `.env` for a `$` estimate.
