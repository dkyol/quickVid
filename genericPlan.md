 se# Short Promo Video — Generic Production Plan

**How to use this document:**
Upload this file plus your script file to a new Claude session and say: "Use `genericPlan.md` to produce a promo video from `<your-script-file>`." Claude will ask all intake questions, then execute the full production pipeline. No other inputs are required at the start.

**Tech stack required:**
- HeyGen — avatar presenter generation (2 options below)
- ElevenLabs API — expressive voiceover (optional: HeyGen native voice)
- Higgsfield CLI — cinematic b-roll generation
- FFmpeg (`tools/ffmpeg.exe`) — assembly and compositing
- Python (`C:\Users\DKYLE\.conda\envs\api\python.exe`)

**HeyGen Authentication (choose one):**
1. **MCP OAuth (recommended for plan credits):**
   - Endpoint: `https://mcp.heygen.com/mcp/v1/`
   - Setup: Add custom MCP connector in Claude Code → Settings → MCP Servers
   - Click "Connect", sign in to HeyGen, approve access (one-time OAuth flow)
   - Uses your HeyGen **plan credits** (no API key needed)
   - Env var: **Do NOT set HEYGEN_API_KEY** (unset it to enable MCP detection)
   
2. **Direct API (pay-as-you-go credits):**
   - Get key from `app.heygen.com` → Settings → API Keys
   - Set `HEYGEN_API_KEY` in `.env`
   - Uses your HeyGen **API credits**

**Other credentials:**
- `ELEVEN_API_KEY` in `.env` (ElevenLabs — voice generation)
- `HF_TOKEN` in `.env` (Higgsfield — b-roll generation)

---

## ⚠️ Avatar Gender Mismatch Rule

**CRITICAL:** If using HeyGen avatars, voice gender MUST match avatar gender:
- Male avatar → male voice (unsuitable: male avatar + female voice)
- Female avatar → female voice (unsuitable: female avatar + male voice)
- Mismatches break immersion and are unusable for final delivery

**Alternative:** Skip avatar entirely. For B2B promos, **voiceover + compelling b-roll** often outperforms avatars:
- Shows product/problem in action
- Voice carries message without visual distraction
- Reduces production complexity and potential mismatches

---

## ⚠️ CRITICAL PROCESS RULE

**DO NOT SKIP STEP 0.** Every video generation must start with the full intake questionnaire (0A–0G). Do not assume defaults, jump to generation, or make creative decisions without user input. Violations cause rework and wasted quota.

---

## STEP 0 — Intake Questionnaire

**Ask the user every question in this section before doing any generation.** Do not assume defaults — every answer shapes downstream decisions. Present each group as a short conversation, not a wall of text.

---

### 0A — Project Identity

1. **What is the product or service name?** (Exact spelling matters — will be used in TTS. Test pronunciation early.)
2. **What category is it?** (Mobile app / SaaS / physical product / service / other)
3. **What is the primary CTA?** ("Download on the App Store" / "Visit our website" / "Book a demo" / other)
4. **What is the target platform for this video?** Select all that apply:
   - App Store preview (15–30s, no audio autoplay)
   - Social media feed (Instagram/TikTok/X — 15–60s, vertical or square preferred)
   - Website hero (landscape, any length)
   - YouTube pre-roll (≤15s unskippable / 30s skippable)
5. **Target video length:** 30s / 45s / 60s / let the script determine
6. **Aspect ratio:** 16:9 landscape (default) / 9:16 vertical (mobile-first) / 1:1 square

---

### 0B — Tone and Visual Style

7. **Describe the mood in 2–3 words.** Examples: warm and inspiring / energetic and punchy / calm and premium / playful and bright / authoritative and clear
8. **What is the primary visual setting for b-roll?** Examples:
   - Lifestyle / real-world use (person using the product in their environment)
   - Cinematic / aspirational (dramatic lighting, symbolic imagery)
   - Product-focused (clean, close-up of the product/screen/UI)
   - Abstract / motion graphics (particles, light leaks, non-literal)
   - Location-specific (name the place: concert hall / modern office / outdoor / kitchen / gym)
9. **Brand color palette:** Primary hex + secondary hex (used for endcard background, text overlays, logo tint)
10. **Is there a tagline?** If yes, provide it. If no, Claude will draft 2–3 options from the script for approval.

---

### 0C — Presenter / Avatar

11. **Do you want a human avatar presenter?** Yes / No (b-roll + VO only)
12. If yes — **Presenter gender and ethnicity preference?** (or "no preference — pick the best available API option")
13. **Presenter setting preference?**
    - Luxury/neutral interior (Annie Sofa — confirmed working)
    - Formal/seated (Miyu — grey background, clean)
    - Office/professional (June — office desk baked in)
    - Other — describe and Claude will find the closest available HeyGen avatar
14. **How prominent should the presenter be?** Options:
    - Heavy: presenter on screen >60% of the video
    - Balanced: presenter alternates with b-roll roughly 50/50
    - Light: presenter bookends only (hook + close); b-roll carries the middle

---

### 0D — Voice

**⚠️ CRITICAL BEFORE ANSWERING:** If you selected an avatar in 0C, **voice gender MUST match avatar gender.** Mismatches (male avatar + female voice) break immersion and are unusable.

15. **Do you have a pre-recorded or pre-generated audio file for the voiceover?**
    - **No — generate from script** (most common path; Claude will generate from the `.txt` script file)
    - **Yes — provide the file path** (Claude will upload it and use it for avatar lip-sync directly)

16. **If generating from script — voice preference:**
    
    **For female avatars:**
    - Option A — **ElevenLabs Sarah** (warm, natural American female; recommended for best expressiveness)
    - Option B — **ElevenLabs other female voice** (specify: Bella, Olivia, etc. or describe tone/energy)
    - Option C — **HeyGen native female TTS** (simpler, fewer steps; less expressive)
    
    **For male avatars:**
    - Option A — **ElevenLabs male voice** (Adam, Chris, Dave, Ethan, Jackson, Marcus, etc. — specify preference)
    - Option B — **HeyGen native male TTS** (simpler, fewer steps; less expressive)
    
    **For non-avatar (b-roll + VO only):**
    - Any voice works — pick based on tone/expressiveness preference

17. **Delivery pacing:** Normal / Slightly slower with emphasis / Energetic and fast
18. **Any words in the script that might be mispronounced?** (Product names, acronyms, unusual spellings.) Claude will test pronunciation in a short clip before committing to the full render.

---

### 0E — B-Roll

18. **How many b-roll scenes are needed?** (Rule of thumb: one scene per 5–8s of non-presenter time. For a 45s video with 50% presenter: ~3 b-roll scenes.)
19. **Describe each b-roll scene** — or provide reference images/URLs and Claude will reverse-engineer a prompt. If unsure, describe the moment in the script each scene should illustrate:
    - Scene 1: what moment in the script / what visual?
    - Scene 2: ...
    - Scene 3: ...
20. **B-roll motion style:** Slow cinematic push-in (default) / Static / Dynamic handheld / Zoom-out reveal

---

### 0F — Audio

21. **Music bed / brand jingle?**
    - Yes — generate a short brand sting via ElevenLabs (5–8s, describe mood/instrument)
    - Yes — I have a music file (provide path)
    - No music — voice only
22. If yes — **When should the jingle play?** At the end only (after VO) / Under the entire video at low volume / Both (fade in at start, swell at end)
23. **Endcard audio:** Silence / Jingle continues / Short logo sting

---

### 0G — Logo and Branding

24. **Logo file path?** (PNG with transparent background preferred. If not available, describe and Claude will generate a placeholder.)
25. **Corner logo:** Displayed on all non-endcard frames? Yes / No
26. **Endcard layout:** Standard (centered logo + product name + CTA badge) / Custom — describe
27. **App Store / Play Store badge needed?** Apple only / Google only / Both / Neither

---

## STEP 0.5 — B-Roll Segmentation Plan (BEFORE any generation)

**⚠️ CRITICAL:** Create a segmented timeline BEFORE generating avatar or voiceover. This prevents concatenation errors and ensures b-roll integrates with narrative, not against it.

### 0.5A — Map script to b-roll segments

1. **Read the script aloud** — time it naturally (~150 words ≈ 60s)
2. **Identify 4–6 key narrative moments:**
   - Hook / opening (0–5s)
   - Problem statement (5–15s)
   - Solution intro (15–25s)
   - Product demo (25–40s)
   - Institutional/bigger picture (40–50s)
   - Close / CTA (50–60s)
3. **Assign one b-roll scene to each moment** — describe what visual should play during each section

Example (SightTune conservatory):
| Time | Script Section | B-Roll Scene | Duration |
|------|---|---|---|
| 0–5s | Hook | Avatar or establishing shot | 5s |
| 5–15s | Pain (drilling notes) | Student drilling / repetitive practice | 10s |
| 15–25s | Solution (iPad practice) | iPad interface, student using app | 10s |
| 25–40s | Payoff (lesson time) | Faculty teaching, student lesson | 15s |
| 40–50s | Digital twin | Data visualization, progress dashboard | 10s |
| 50–60s | Close + CTA | Institution/studio, call-to-action text | 10s |

### 0.5B — Generate b-roll scenes (Higgsfield)

For each segment, create a corresponding b-roll visual:
- Use Higgsfield CLI to generate images from prompts (Cinematic Studio 2.5)
- Animate each image to 5-second video clips (Seedance 2.0)
- Label outputs: `scene_0_hook`, `scene_1_drilling`, `scene_2_ipad`, etc.

### 0.5C — Assembly strategy

**Do NOT concatenate.** Use FFmpeg complex filter or dedicated editor to:
1. Layer voiceover as primary timeline
2. Splice b-roll clips at exact timestamps (matching script section boundaries)
3. Add avatar bookends if needed (opening + close)
4. Ensure each b-roll moment matches the narrative pacing

Example assembly structure (v23 reference):
```
[0–5s]   Avatar hook
[5–15s]  B-roll scene 1 (problem)
[15–25s] Avatar + b-roll scene 2 (solution)
[25–40s] B-roll scene 3 (payoff)
[40–50s] B-roll scene 4 (institutional)
[50–60s] Avatar close / endcard
```

---

## STEP 1 — Voice Generation

**Do this before avatar generation.** Voice duration determines the entire edit structure — every segment timing depends on it.

**Choose one of three paths based on your intake answer (question 15):**

---

### Path 1A — Text script only, HeyGen native TTS (fewest steps)

Use when: you have no audio file and want the simplest path. HeyGen generates TTS and lip-sync together in one call — no separate audio step, no upload.

**Trade-off:** Less expressive delivery than ElevenLabs; you get HeyGen's built-in voice character with less control over pacing and emotion.

1. Confirm your script file is at `prompts/<script>.txt`
2. Run pronunciation test first (see section 1D below) — pass the script text to HeyGen's TTS preview or a short HeyGen test render
3. If pronunciation is correct: skip to **Step 2 — Avatar Generation**
   - In the HeyGen call (`heygen_client.py` or direct API), use:
     ```python
     "voice": {
         "type": "text",
         "input_text": open("prompts/<script>.txt").read().strip(),
         "voice_id": os.environ["HEYGEN_VOICE_ID"]   # or any compatible voice_id
     }
     ```
   - HeyGen handles TTS and lip-sync internally — no separate audio file is produced
4. **Note the rendered video's duration** (needed for assembly math) — get it from FFmpeg after download:
   ```powershell
   & tools\ffmpeg.exe -i output\clips\avatar_v1.mp4 2>&1 | Select-String "Duration"
   ```

---

### ⚠️ Sync Quality Note

**TESTED:** Uploading ElevenLabs audio to HeyGen for lip-sync does **NOT produce better sync** than HeyGen native TTS. The added complexity (generate → upload → HeyGen) produces inferior mouth-sync results. Use Path 1A (native TTS) for better sync quality, or use ElevenLabs TTS with non-HeyGen avatar systems.

---

### Path 1B — Text script → ElevenLabs → HeyGen lip-sync (NOT RECOMMENDED)

Use when: you want the most expressive, natural-sounding voiceover. Requires ElevenLabs API key and an extra upload step, but produces noticeably better delivery.

**Pronunciation test first (section 1D below) — required before full render.**

**Step 1: Generate full voiceover via ElevenLabs API**

```python
# tools/generate_voice_el.py — already written; loads keys from .env
# Edit SCRIPT and VOICE_ID at the top, then run:
C:\Users\DKYLE\.conda\envs\api\python.exe tools/generate_voice_el.py
# Output: output/clips/vo_v1.mp3
```

Or call the API directly:

```python
import requests, os, pathlib

script = pathlib.Path("prompts/<script>.txt").read_text().strip()

r = requests.post(
    "https://api.elevenlabs.io/v1/text-to-speech/<VOICE_ID>",
    headers={"xi-api-key": os.environ["ELEVEN_API_KEY"], "Content-Type": "application/json"},
    json={
        "text": script,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.38,        # lower = more natural variation (counter-intuitive)
            "similarity_boost": 0.82,
            "style": 0.08,            # minimal stylization — softer, less theatrical
            "use_speaker_boost": False # avoids over-sharpening
        }
    }
)
with open("output/audio/vo_v1.mp3", "wb") as f:
    f.write(r.content)
```

**Step 2: Upload to catbox.moe**

```python
from heygen_client import upload_audio
audio_url = upload_audio("output/audio/vo_v1.mp3")
print(audio_url)  # https://files.catbox.moe/xxxxxx.mp3
```

> catbox.moe is the only confirmed-working upload host on this machine. tmpfiles.org, transfer.sh, file.io, 0x0.st, and pixeldrain all fail.

**Step 3: Submit to HeyGen with audio URL**

In `heygen_client.py` or direct API call, use:
```python
"voice": {
    "type": "audio",
    "audio_url": audio_url   # catbox URL from step 2
}
```

HeyGen lip-syncs the avatar to the uploaded audio. The returned video has the audio baked in.

**Step 4: Use the HeyGen video's own audio in assembly** — do NOT mux the original `.mp3` separately. The baked audio guarantees frame-accurate sync.

---

### Path 1C — Pre-existing audio file → HeyGen lip-sync

Use when: you already have a recorded or generated audio file (`.mp3`, `.wav`, `.m4a`).

1. Confirm the file exists and plays correctly
2. Upload to catbox.moe:
   ```python
   from heygen_client import upload_audio
   audio_url = upload_audio("path/to/your/audio.mp3")
   ```
3. Pass `audio_url` to HeyGen exactly as in Path 1B Step 3
4. Note the audio duration — it sets the avatar clip length and all downstream timing

---

### 1D — Pronunciation test (run before any full render)

Always test product names and unusual words in a short clip before committing to a full generation (which takes 10–15 minutes and uses quota).

**ElevenLabs pronunciation test:**
```python
import requests, os
test_text = "<PRODUCT_NAME>. <any unusual word>."
r = requests.post(
    "https://api.elevenlabs.io/v1/text-to-speech/EXAVITQu4vr4xnSDxMaL",
    headers={"xi-api-key": os.environ["ELEVEN_API_KEY"]},
    json={"text": test_text, "model_id": "eleven_multilingual_v2",
          "voice_settings": {"stability": 0.38, "similarity_boost": 0.82,
                             "style": 0.08, "use_speaker_boost": False}}
)
open("output/audio/pronunciation_test.mp3", "wb").write(r.content)
```

**HeyGen native TTS pronunciation test:** Submit a 5-second test video with just the product name as the script. Check the result before submitting the full script.

If mispronounced: adjust spelling in the script file — break compound words into two words (e.g., "SightTune" → "Sight Tune"), or use phonetic spelling. Re-test before proceeding.

---

### 1E — Approved ElevenLabs voice reference

| Voice | ID | Best for |
|-------|----|----------|
| Sarah (recommended) | `EXAVITQu4vr4xnSDxMaL` | Warm, natural, American female |
| Rachel | `21m00Tcm4TlvDq8ikWAM` | Authoritative, clear, American female |
| Adam | `pNInz6obpgDQGcFmaJgB` | Warm, conversational, American male |

**ElevenLabs settings by delivery style:**

| Parameter | Warm/Natural | Energetic | Authoritative |
|-----------|-------------|-----------|---------------|
| `stability` | 0.38 | 0.30 | 0.55 |
| `similarity_boost` | 0.82 | 0.85 | 0.75 |
| `style` | 0.08 | 0.25 | 0.15 |
| `use_speaker_boost` | False | True | False |

**Output of Step 1 (regardless of path):** `output/clips/avatar_v1.mp4` (after Step 2 generates it with the voice) or `output/audio/vo_v1.mp3`. Record the exact VO duration in seconds — you will need it for every timing calculation in Step 5.

---

## STEP 2 — Avatar Generation

**Only use HeyGen for avatar/presenter clips.** Higgsfield is b-roll only.

### 2A — Avatar selection rules

- Only use avatars with `supported_api_engines: ["avatar_v", "avatar_iv"]` — newer studio avatars have `[]` and cannot be used via API
- Choose an avatar with **simple, contained hair** (short, tied back, or smooth). Flyaway or voluminous hairstyles cause visual artifacts on b-roll cuts
- Background is **always baked in** — `background` API parameter is silently ignored for all studio avatars
- Choose the avatar whose baked background fits the video's aesthetic

**Confirmed API-compatible avatars (as of 2026-06):**

| Avatar | Look ID | Background | Hair | Notes |
|--------|---------|------------|------|-------|
| Annie | `Annie_Sofa_Sitting_Front_public` | Luxury living room, large windows | Long wavy | Monitor for hair artifacts |
| Annie | `Annie_Lounge_Standing_Front_public` | Same room, standing | Long wavy | |
| Miyu | `Miyu_public` | Clean grey | Neat | Very clean, formal |
| June | `June_sitting_office_front` | Office desk | Neat | Background not ideal for lifestyle |
| Abigail | (concert hall look) | Concert hall setting | Neat | Good for performance/arts products |

### 2B — Generation call

```python
# heygen_client.py pattern
payload = {
    "video_inputs": [{
        "character": {
            "type": "avatar",
            "avatar_id": "<LOOK_ID>",
            "avatar_style": "normal"
        },
        "voice": {
            "type": "audio",          # if using uploaded EL audio
            "audio_url": "<CATBOX_URL>"
            # OR for HeyGen native:
            # "type": "text",
            # "input_text": "<SCRIPT_TEXT>",  # Spell product names phonetically if needed
            # "voice_id": "<HEYGEN_VOICE_ID>"
        }
    }],
    "dimension": {"width": 1280, "height": 720},
    "aspect_ratio": "16:9"
}
```

**Quota notes:**
- `audio_url` forces Avatar IV engine — depletes Avatar IV monthly quota
- Text-only input uses Avatar V — slower (~10–15 min for 30s clip) but better quality and uses separate quota
- If quota error `AVATAR_IV_VIDEO_GENERATION_DURATION_LIMIT_REACHED`: switch to text input + HeyGen native voice, or wait for quota reset
- Avatar V render time: 10–15 min for a 30s script; Avatar IV: 3–5 min

**Output:** `output/clips/avatar_v1.mp4` — note duration

---

## STEP 3 — B-Roll Generation

**Use Higgsfield CLI only.** The MCP tool uses wrong auth. The REST API key/secret approach returns 403. Always use OAuth via `higgsfield auth login`.

### 3A — Auth check

```powershell
higgsfield auth status   # confirm credentials are valid
# If expired: ! higgsfield auth login   (opens browser, ~5 seconds)
```

### 3B — Model list check (always run before generation)

```powershell
higgsfield model list
```

Model IDs change. Do not hardcode. As of 2026-06, confirmed working:
- Image: `cinematic_studio_2_5`, `seedream_v4_5`, `soul_cinematic`
- Video: `seedance_2_0`, `seedance1_5`, `kling3_0`, `cinematic_studio_video_v2`

### 3C — Generate hero image first (establishes the venue)

Before generating any scene, generate ONE hero wide-shot image to lock the visual style. All subsequent scenes must copy this description exactly to maintain venue consistency.

```powershell
higgsfield generate create cinematic_studio_2_5 `
  --prompt "<hero image prompt>" `
  --wait --json
# Result JSON contains result_url — download immediately (CDN URLs expire)
Invoke-WebRequest -Uri "<result_url>" -OutFile "output/broll/hero_raw.png"
```

**Hero image prompt structure:**
```
<subject description>, <setting with specific architecture and lighting details>,
<camera angle>, <mood adjectives>, cinematic, no hands on keys/controls/devices [if relevant]
```

### 3D — Generate remaining scene images

Each additional scene image must include the exact venue description from the hero prompt. Only the subject framing changes (wide → medium → close-up).

| Scene | Framing | Prompt additions |
|-------|---------|-----------------|
| Wide (establishing) | Full subject in environment | As hero |
| Medium | Waist-up, environment still visible | Same venue + "medium side shot" |
| Close-up / product shot | Product or detail prominent | Same venue + "close-up, [product] visible, blurred background" |
| Audience / reaction | Viewer's perspective | Same venue + "audience perspective, subject silhouette, bokeh foreground" |

**Important rules:**
- Never show hands/fingers interacting with a device or instrument — Higgsfield struggles with this and produces artifacts
- Square images only (`seedream_v4_5` always outputs 1:1) — crop to 16:9 in FFmpeg: `crop=2048:1152:0:448,scale=1280:720`
- Download images immediately — CDN URLs expire

### 3E — Animate each image to video

```powershell
higgsfield generate create seedance_2_0 `
  --image "output/broll/scene1_raw.png" `
  --prompt "slow cinematic push-in, warm lighting, no motion on hands or devices" `
  --wait --wait-timeout 20m --json
```

Animate all scenes. Each returns a video URL — download immediately to `output/clips/broll_scene1.mp4` etc.

- **Local image paths work** — the CLI auto-uploads them (`Media flags accept a UUID or a local
  file path — paths are auto-uploaded`). You do NOT need to pass the CDN URL; a local `.png` path
  is fine. If you see `Media "..." is neither a UUID nor an existing file path`, the path you
  passed is simply wrong/misspelled — verify the exact filename, don't conclude "local paths
  don't work."

#### ⚠️ Seedance video jobs are SLOW — always set `--wait-timeout 20m`

**This is the #1 cause of "b-roll didn't generate."** Seedance (and other video models) routinely
take **5–15 minutes** per clip. `--wait` alone uses a short default window; the CLI then prints:

```
Error: Timeout after 5m0s; last status "in_progress".
```

`in_progress` means **the job is rendering fine on Higgsfield's servers** — only the client gave up
waiting. The job is NOT failed. Two consequences:

1. **Always pass `--wait-timeout 20m`** (or longer) for any *video* model. Image models
   (`cinematic_studio_2_5`, `seedream_v4_5`) are fast and rarely need it; video models always do.
2. A client-side timeout does **not** cancel the job. You can re-poll or just re-run; do not assume
   the credit was wasted.

#### Never swallow errors in batch generation scripts

A batch loop that animates N scenes MUST surface failures, or you get silent partial output
(e.g. "1 of 5 videos generated" with no explanation). Required pattern for each job:

```python
r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
if r.returncode != 0:
    print(f"[{name}] rc={r.returncode}")
    print(f"  STDOUT: {r.stdout.strip()[:300]}")   # ALWAYS print both streams
    print(f"  STDERR: {r.stderr.strip()[:300]}")
    # retry (transient) or fail loudly — never `except: pass`
```

- **Never use bare `except:` / `except: pass`** around a generation call. It hides timeouts,
  quota errors, and parse errors alike.
- **Add at least one retry** — video-model failures are often transient (server load). A second
  attempt with the same inputs frequently succeeds.
- **Keep filenames consistent** — save the PNG and reference it for animation under the *exact*
  same name. A naming mismatch between the download step and the animate step produces a bogus
  "file path does not exist" error that looks like an API problem but is your own typo.
- Reference implementation: `animate_broll_v25.py` (long timeout + visible errors + retry).

---

## STEP 4 — Assets

### 4A — Logo / corner overlay

- Logo file: `assets/<logo>.png` with transparent background (RGBA)
- Corner overlay size: 36×65px (height 65px scales to ~9% of 720p frame height — visible but not intrusive)
- Build if not provided:

```python
# tools/make_corner_logo.py pattern
from PIL import Image
img = Image.open("assets/<logo>.png").convert("RGBA")
img.thumbnail((36, 65), Image.LANCZOS)
img.save("output/corner_owl.png")
```

### 4B — Brand jingle

If generating via ElevenLabs Sound Effects or a music model:
- Target: 5–8s, matches brand mood, ends cleanly
- After generating, **always pre-convert** to AAC 48kHz before mixing:

```powershell
& tools\ffmpeg.exe -i "output/audio/jingle_raw.mp3" `
    -ar 48000 -c:a aac -b:a 256k `
    "output/audio/jingle_hq.m4a" -y
```

Never use raw MP3 in assembly — default FFmpeg AAC drops to ~127 kb/s; pre-converting yields ~238 kb/s at 48kHz.

### 4C — Endcard

Standard endcard (4s):
- White background (full frame, 1280×720)
- Logo centered, large (~50% frame height)
- Product name in large spaced uppercase sans-serif below logo
- Tagline in smaller uppercase below that
- Platform badge (App Store / Play Store) bottom-right corner
- No corner logo on endcard (clean white frame)

Build with Pillow + FFmpeg:
```python
# tools/build_endcard.py pattern
from PIL import Image, ImageDraw, ImageFont
canvas = Image.new("RGB", (1280, 720), "white")
# Place logo, draw text, save as output/endcard_frame.png
# Then: ffmpeg -loop 1 -i output/endcard_frame.png -t 4 output/endcard_v1.mp4
```

App Store badge: Download official PNG from Apple's badge assets page. Do not draw a substitute for final output.

---

## STEP 4.5 — The Core Audio/Video Pattern (CRITICAL CONCEPT)

**This is the foundation of modern short-form promos. Understand this before assembly.**

### Pattern: Continuous Narrator Over Visual Transitions

The narrator/voiceover is **continuous and uninterrupted** for the entire duration. The video cuts/transitions between avatar, b-roll, and endcard while the audio plays underneath.

```
AUDIO (narrator):  [========== CONTINUOUS VOICEOVER 60s ==========]
VIDEO:             [Avatar] [B-roll 1] [B-roll 2] [B-roll 3] [Avatar] [Endcard]
                   0-5s     5-15s      15-25s     25-40s     40-60s   60-64s
```

**Why this works:**
- The narrator never "stops" — audience stays engaged
- Visual cuts break up monotony and reinforce the message
- Tight pacing: each b-roll moment illustrates what the narrator is saying at that exact second
- Professional: this is the standard for YouTube promos, LinkedIn, TV ads

**What NOT to do:**
- ❌ Cut the narrator's audio into pieces and sync to individual segments (produces jumpy, unprofessional pacing)
- ❌ Use silent b-roll with separate audio track added later (misses lip-sync, timing, emotional impact)
- ❌ Avatar-only without b-roll (boring for >30s promos; okay for testimonials)

**Assembly steps for this pattern:**
1. Generate voiceover once (full length, uninterrupted)
2. Generate avatar video (optional; can use for hook/close only)
3. Generate b-roll scenes for the narrative moments you want to visualize
4. Build a video track with cuts at natural narrative points
5. Mux: video track + continuous audio track
6. Result: narrator talks over all transitions; audience never notices the cuts

---

## STEP 5 — Edit Structure and Assembly

### 5A — Edit structure decisions

Answer these before writing the assembly script:

1. **Does the script have a clear hook (first 3–5s)?** If not, identify the most attention-grabbing line and reorder to lead with it.
2. **Where are the natural cut points?** Mark the script at each beat: hook / problem / solution intro / product moment / brand close
3. **Which b-roll goes where?** Map each scene to a script moment:
   - Problem scene: illustrates the pain point being solved
   - Solution / product shot: shows the product in action (most important scene — must appear here)
   - Atmospheric / tagline scene: visual punctuation at the end

**Standard 9-segment template (scalable — add/remove middle segments):**

| # | Segment | Source | Typical duration |
|---|---------|--------|-----------------|
| s1 | Hook | Avatar (0s → cut point 1) | 4–6s |
| s2 | Problem | B-roll wide | 4–6s |
| s3a | Solution intro | Avatar (cut point 1 → cut point 2) | 3–4s |
| s3b | Product visual | B-roll close-up / product shot | 3–4s |
| s3c | Solution confirm | Avatar (cut point 2 → cut point 3) | 3–5s |
| s4 | Product in use | B-roll medium | 2–4s |
| s5 | Brand close | Avatar (cut point 3 → end of VO) | 3–6s |
| s6 | Tagline | B-roll atmospheric + text overlay | 4–5s |
| s7 | Endcard | Endcard + logo | 3–4s |

**Total target:** VO duration + 9–10s (tagline + endcard)

### 5B — Assembly script structure (`tools/assemble_vXX.py`)

```python
"""Assemble <product>_promo_vXX.mp4 — <avatar> + <voice> + <jingle description>."""
import subprocess, os, sys

ROOT  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FF    = os.path.join(ROOT, "tools", "ffmpeg.exe")
CLIPS = os.path.join(ROOT, "output", "clips")
OUT   = os.path.join(ROOT, "output")
TMP   = os.path.join(OUT, "_tmp_vXX")
FONT  = r"C\:/Windows/Fonts/arialbd.ttf"
OWL   = os.path.join(OUT, "corner_owl.png")
FINAL = os.path.join(OUT, "<product>_promo_vXX.mp4")
os.makedirs(TMP, exist_ok=True)

# -- Input files
AVATAR  = os.path.join(CLIPS, "avatar_vXX.mp4")   # <duration>s
BROLL_W = os.path.join(CLIPS, "broll_wide.mp4")
BROLL_C = os.path.join(CLIPS, "broll_closeup.mp4")
BROLL_M = os.path.join(CLIPS, "broll_medium.mp4")
BROLL_T = os.path.join(CLIPS, "broll_tagline.mp4")
ENDCARD = os.path.join(OUT, "endcard_vXX.mp4")
JINGLE  = os.path.join(OUT, "audio", "jingle_hq.m4a")  # pre-converted AAC

VO_DURATION    = 0.0   # FILL IN: exact avatar VO length in seconds
TOTAL_DURATION = VO_DURATION + 9.0  # +5s tagline + 4s endcard

def run(args, label=""):
    cmd = [FF, "-y"] + args
    print(f"  [{label}]")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("STDERR:", r.stderr[-800:])
        sys.exit(1)

def avatar_segment(dst, start, end):
    dur = end - start
    fc = (f"[0:v]trim={start}:{end},setpts=PTS-STARTPTS[trimmed];"
          "[1:v]scale=36:65[owl];"
          "[trimmed][owl]overlay=20:20[out]")
    run(["-i", AVATAR, "-loop", "1", "-i", OWL, "-filter_complex", fc,
         "-map", "[out]", "-t", str(dur),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", "-an", dst], label)

def broll_segment(src, dst, start=0, end=5):
    dur = end - start
    fc = (f"[0:v]trim={start}:{end},setpts=PTS-STARTPTS[trimmed];"
          "[1:v]scale=36:65[owl];"
          "[trimmed][owl]overlay=20:20[out]")
    run(["-i", src, "-loop", "1", "-i", OWL, "-filter_complex", fc,
         "-map", "[out]", "-t", str(dur),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", "-an", dst], label)

def tagline_segment(src, dst, text, dur=5):
    safe_text = text.replace(":", "\\:")
    fc = (f"[0:v]trim=0:{dur},setpts=PTS-STARTPTS,"
          "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720[scaled];"
          "[1:v]scale=36:65[owl];"
          "[scaled][owl]overlay=20:20[withowl];"
          f"[withowl]drawtext=text='{safe_text}':"
          f"fontfile='{FONT}':"
          "fontsize=48:fontcolor=white:"
          "shadowcolor=black@0.85:shadowx=2:shadowy=2:"
          "x=(w-tw)/2:y=h*0.87[out]")
    run(["-i", src, "-loop", "1", "-i", OWL, "-filter_complex", fc,
         "-map", "[out]", "-t", str(dur),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", "-an", dst], "tagline")

# BUILD SEGMENTS — fill in cut points after reviewing avatar clip
# avatar_segment(f"{TMP}/s1_hook.mp4",   0,   5)
# broll_segment(BROLL_W,  f"{TMP}/s2_problem.mp4",  0, 5)
# avatar_segment(f"{TMP}/s3a.mp4",      10,  13)
# broll_segment(BROLL_C,  f"{TMP}/s3b.mp4",          0,  4)
# avatar_segment(f"{TMP}/s3c.mp4",      13,  20)
# broll_segment(BROLL_M,  f"{TMP}/s4.mp4",            0,  3)
# avatar_segment(f"{TMP}/s5_close.mp4", 20, VO_DURATION)
# tagline_segment(BROLL_T, f"{TMP}/s6_tagline.mp4", "<TAGLINE TEXT>")

# ENDCARD
run(["-i", ENDCARD, "-vf", "trim=0:4,setpts=PTS-STARTPTS", "-t", "4",
     "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", "-an",
     f"{TMP}/s7_endcard.mp4"], "endcard")

# CONCAT VIDEO
segment_names = ["s1_hook", "s2_problem", "s3a", "s3b", "s3c", "s4", "s5_close", "s6_tagline", "s7_endcard"]
concat_txt = os.path.join(TMP, "concat.txt")
with open(concat_txt, "w") as f:
    for n in segment_names:
        f.write(f"file '{TMP}/{n}.mp4'.replace('\\\\', '/')\n")
run(["-f", "concat", "-safe", "0", "-i", concat_txt,
     "-vf", "setsar=1:1", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
     f"{TMP}/video_only.mp4"], "concat")

# AUDIO MIX: VO + jingle after VO ends
JINGLE_START = VO_DURATION
jingle_fade_out = TOTAL_DURATION - JINGLE_START - 1.0
run(["-i", AVATAR, "-i", JINGLE,
     "-filter_complex",
     f"[0:a]atrim=0:{VO_DURATION},asetpts=PTS-STARTPTS[vo];"
     f"anullsrc=r=48000:cl=stereo,atrim=duration={TOTAL_DURATION:.3f}[base];"
     "[vo][base]amix=inputs=2:duration=longest:dropout_transition=0[votrack];"
     f"[1:a]aresample=48000,volume=0.35,"
     f"afade=t=in:st=0:d=0.8,afade=t=out:st={jingle_fade_out:.1f}:d=1.0,"
     f"adelay={int(JINGLE_START*1000)}|{int(JINGLE_START*1000)}[jingle];"
     "[votrack][jingle]amix=inputs=2:duration=longest:normalize=0[aout]",
     "-map", "[aout]", "-c:a", "aac", "-ar", "48000", "-b:a", "256k",
     f"{TMP}/audio.m4a"], "audio")

# MUX
run(["-i", f"{TMP}/video_only.mp4", "-i", f"{TMP}/audio.m4a",
     "-c:v", "copy", "-c:a", "copy", "-shortest", FINAL], "mux")
print(f"\nDone: {FINAL}")
```

### 5C — Avatar portrait-in-landscape (blurred pillarbox)

HeyGen avatars may output portrait-format content in a 16:9 frame. Fix with blurred pillarbox fill:

```python
def avatar_landscape_segment(dst, start, end, brightness=-0.15):
    dur = end - start
    fc = (
        f"[0:v]trim={start}:{end},setpts=PTS-STARTPTS[src];"
        "[src]scale=1280:720:force_original_aspect_ratio=decrease[fg];"
        f"[src]scale=1280:720:force_original_aspect_ratio=increase,"
        f"crop=1280:720,boxblur=20:5,eq=brightness={brightness}[bg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2[comp];"
        "[1:v]scale=36:65[owl];"
        "[comp][owl]overlay=20:20[out]"
    )
    run(["-i", AVATAR, "-loop", "1", "-i", OWL, "-filter_complex", fc,
         "-map", "[out]", "-t", str(dur),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", "-an", dst], label)
```

### 5D — Static image segment with zoompan (hall b-roll alternative)

When a b-roll clip isn't available but a still image is, animate it:

```python
def zoompan_segment(src_img, dst, dur=5):
    frames = dur * 30
    fc = (
        "[0:v]scale=3072:3072,crop=3072:1728:0:(ih-1728)/2,"
        f"zoompan=z='1+0.00167*on':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':"
        f"d={frames}:s=1280x720:fps=30[zoomed];"
        "[1:v]scale=36:65[owl];"
        "[zoomed][owl]overlay=20:20[out]"
    )
    run(["-loop", "1", "-i", src_img, "-loop", "1", "-i", OWL,
         "-filter_complex", fc, "-map", "[out]", "-t", str(dur),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", "-an", dst], "zoompan")
```

---

## STEP 6 — Quality Check

Extract preview frames and review before calling the version final:

```powershell
# Extract frames at key timestamps
$ff = "tools\ffmpeg.exe"
$timestamps = @(2, 6, 12, 20, 28, 34, 38)
foreach ($t in $timestamps) {
    & $ff -ss $t -i "output/<product>_promo_vXX.mp4" -frames:v 1 "output/preview_${t}s.jpg" -y
}
```

**Review checklist:**
- [ ] Avatar lip-sync looks natural at all cut-in and cut-out points
- [ ] All b-roll clips share a consistent visual venue (same architecture, lighting, color palette)
- [ ] No b-roll clip is reused in two different segments
- [ ] Corner logo visible on all segments except endcard
- [ ] No corner logo on endcard
- [ ] Tagline text is legible and properly positioned (not cut off at edges)
- [ ] Product name is pronounced correctly (listen to VO)
- [ ] Audio levels: voice clear, jingle clearly subordinate (~−18 dB relative to VO)
- [ ] Endcard has correct logo, product name, tagline, and platform badge
- [ ] Video ends cleanly (no freeze frames, no audio pop at end)
- [ ] Total duration matches the intended target

---

## Hard Rules (do not skip)

These are learned constraints — each represents a past failure. Violating any will waste a generation credit.

1. **HeyGen only for avatar/presenter.** Higgsfield for b-roll only. Never generate an avatar in Higgsfield.
2. **Never chroma-key Higgsfield output.** No green screen — compositing always destroys skin tones and hair.
3. **Never attempt alpha extraction from WebM.** Produces hard fringing; not usable.
4. **Higgsfield backgrounds are unique per generation.** Even with identical prompts, every call produces a different background. Generate all b-roll images first (locking the aesthetic in prompt text), then animate.
5. **HeyGen avatar backgrounds are always baked in.** `background` API parameter is silently ignored for all studio avatars — do not waste time testing it.
6. **New HeyGen studio avatars (2025+) cannot be used via API.** Check `supported_api_engines` in avatar metadata — must include `"avatar_v"` or `"avatar_iv"`. If the list is empty, skip this avatar.
7. **HeyGen asset upload API is broken.** Use catbox.moe via `curl.exe` for audio hosting. Do not attempt the HeyGen upload endpoint.
8. **ElevenLabs-via-HeyGen engine routing degrades audio.** Always generate EL audio directly via EL API, not via `engine_settings.engine_type = "elevenlabs"` in HeyGen.
9. **Test product name pronunciation before full render.** Generate a 5-word clip first. If mispronounced, adjust spelling in the script (e.g., compound words → two words). Never splice corrected audio onto a full-length render.
10. **Higgsfield auth is OAuth only.** API key/secret returns 403 (points to a different/empty account). Auth via `higgsfield auth login` CLI. Check `higgsfield auth status` before each session.
11. **Higgsfield model IDs change.** Always run `higgsfield model list` before generation. Do not hardcode model names.
11a. **Higgsfield video jobs need `--wait-timeout 20m`.** Seedance/video models take 5–15 min. `--wait` alone times out with `last status "in_progress"` — that means the job is still rendering server-side (NOT failed), the client just gave up. Image models are fast and don't need it.
11b. **Never wrap Higgsfield calls in bare `except:`.** Batch scripts MUST print stdout+stderr on failure and retry once, or you get silent partial output ("1 of 5 generated") with no cause. Local image paths auto-upload — a "not a valid file path" error means your filename is wrong, not that paths are unsupported.
12. **Higgsfield images are square.** Crop to 16:9 before animating: `crop=2048:1152:0:448,scale=1280:720` (for 2048×2048 output).
13. **Never prompt Higgsfield for fingers/hands interacting with objects.** Produces distorted artifacts. Describe the subject's posture as "arms resting," "hands in lap," or "not playing/touching."
14. **Pre-convert all jingles to AAC 48kHz before mixing.** FFmpeg's default AAC drops to ~127 kb/s. Use `ffmpeg -ar 48000 -c:a aac -b:a 256k`. Always use `_hq.m4a` in assembly, never raw MP3.
15. **Always specify `-b:a 256k` in assembly audio encoding.** Default FFmpeg AAC is too low.
16. **Version every output file.** Never overwrite a prior version. Use `_v1`, `_v2`, etc. suffixes on all output files.
17. **FFmpeg binary is at `tools/ffmpeg.exe`.** Never assume it is on PATH.
18. **Python interpreter is `C:\Users\DKYLE\.conda\envs\api\python.exe`.** `python` is not on PATH.
19. **Read script from file — never hardcode in scripts.** Script lives at `prompts/<script_name>.txt`.
20. **All API keys live in `.env`.** Never hardcode in source files. `.env` is gitignored.

---

## Platform-Specific Output Notes

### App Store Preview (Apple)
- Max 30s; no audio plays automatically — visuals must communicate without sound
- Export at 1080×1920 (portrait) or 1920×1080 (landscape) for best quality
- No watermarks, no editorial text overlays with pricing claims
- App icon should be visible at least once
- Re-encode for App Store: `ffmpeg -i input.mp4 -c:v libx264 -profile:v high -level 4.0 -pix_fmt yuv420p -c:a aac -b:a 256k output_appstore.mp4`

### Instagram / TikTok (vertical)
- Target 9:16 at 1080×1920; hook must land in first 1.5s (autoplay, sound off)
- Captions/subtitles strongly recommended (85% of social video watched muted)
- Consider adding burned-in subtitles via FFmpeg `drawtext` or exporting SRT for platform upload

### YouTube pre-roll
- ≤15s unskippable, or 30s skippable (skip happens at 5s — hook must land before that)
- 16:9 1920×1080 preferred; 1280×720 acceptable

### Website hero embed
- 16:9 landscape, autoplay muted (captions or on-screen text needed)
- Loop-friendly: design the endcard to transition back to opening cleanly, or output a separate looping version without endcard

---

## Industry Standard Production Tips

### Hook (first 3–5 seconds)
The hook determines whether anyone watches the rest. It must do one of:
- State the audience's specific pain ("You've been turning pages by hand in recitals…")
- Make a bold/surprising claim ("What if your music app could read your eyes?")
- Show the end result first, then explain how (reverse chronology)

The question-format hook ("What if I told you…") works well for problem-solution products. Avoid generic openers ("Hi, I'm here to tell you about…").

### Problem/Solution structure (the only structure that works for <60s)
1. **Hook** — get attention, establish context (5s)
2. **Problem** — name the specific frustration the audience knows (5–8s)
3. **Solution** — introduce the product as the fix (5–10s)
4. **Proof / product moment** — show it working (3–5s)
5. **CTA** — one clear action ("Check it out" / "Download now") (3–5s)
6. **Tagline + endcard** — brand memory (4–6s)

### Music bed mixing
- VO should be dominant: music bed at −18 dB relative to VO (volume=0.25 in FFmpeg amix)
- Jingle/sting at end: −9 dB (volume=0.35) — can be louder since VO has ended
- Fade in music: 0.8s; fade out: 1.0s before video end — never cut music abruptly
- Low-pass filter if the music bed competes with the voice: `lowpass=f=800`

### Cut pacing
- Short-form promo: average shot length 3–5s
- Never hold on a static frame >6s without a reason
- Avatar on screen for extended dialog: cut to b-roll to break visual monotony
- Rule of 3: use at least 3 different b-roll clips. Repeating a clip signals low production value.

### Typography on screen
- 1 font family maximum; bold weight for readability at small sizes
- Tagline: horizontally centered, ~85–90% down the frame (clear of subject)
- Shadow for legibility over variable backgrounds: `shadowcolor=black@0.85:shadowx=2:shadowy=2`
- Keep text on screen ≥2s — faster than that and it's not readable
- Uppercase for brand names and taglines; sentence case for descriptive text

### Color consistency
- Pick one primary accent color for text overlays; use it every time
- Endcard: white background reads as most premium for B2C apps; dark background for tech/SaaS
- Logo must be the highest-contrast element on the endcard — it's the last thing the viewer sees

### Audio quality hierarchy
1. VO must always be the clearest, most prominent element
2. Music bed is decoration, not content
3. Sound effects (if any) must not compete with VO frequency range (VO lives in 200Hz–4kHz)
4. Final mix: VO peaks at −6 dBFS; music bed peaks at −24 dBFS; jingle sting peaks at −12 dBFS

---

## APPENDIX — Lessons Learned & Known Issues

### Voice Quality & Sync

**ElevenLabs + HeyGen lip-sync (NOT RECOMMENDED):**
- Uploading ElevenLabs audio to HeyGen for lip-sync produces **inferior sync quality** compared to HeyGen native TTS
- The added complexity (generate → upload → HeyGen) does not justify results
- **Tested:** EL audio URL lip-sync shows worse mouth-sync than HeyGen native TTS

**Recommendation:** If using ElevenLabs for expressive voiceover, do NOT use with HeyGen avatars. Use with non-HeyGen video platforms. If using HeyGen avatars, use HeyGen native TTS for better sync.

### HeyGen API Issues

**Voice provider transient errors:**
- HeyGen voice transcription service occasionally becomes "temporarily unavailable"
- Error: `VOICE_PROVIDER_TRANSIENT` with message "Voice transcription timed out"
- **This is a HeyGen infrastructure issue**, not a problem with our API key or approach
- **Fix:** Retry after 5-30 minutes when service recovers

**Timeout handling:**
- Avatar generation for 80+ second videos takes 15-30+ minutes (not 10 minutes)
- Use timeout: **5400 seconds (90 minutes) minimum** for videos >60s
- Polling interval: 30 seconds (not 10) to reduce API load

### Avatar/Voice Gender Matching

**CRITICAL:** Always match voice gender to avatar gender
- Male avatar + Female voice = unusable (breaks immersion)
- Female avatar + Male voice = unusable (breaks immersion)
- **Always verify** voice actually sounds like claimed gender before committing to full generation

### B-Roll Integration

**DO NOT concatenate clips.** Proper integration requires:
- Segmented timeline mapped to script narrative
- B-roll spliced at specific timestamps (not stitched end-to-end)
- Each segment duration matched to corresponding script section
- See STEP 0.5 for segmentation process

### Process Discipline

**HARD RULES (no exceptions):**
1. Always do STEP 0 (full intake questionnaire) before any generation
2. Always create STEP 0.5 (b-roll segmentation plan) before generating voiceover or avatar
3. Always test pronunciation with short clips before full renders
4. Always map b-roll to script segments — never concatenate
5. Always match voice gender to avatar gender
6. Never assume defaults — ask the user

