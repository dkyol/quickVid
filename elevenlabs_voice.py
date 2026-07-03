#!/usr/bin/env python3
"""
elevenlabs_voice.py — Generate the reel's voiceover in YOUR ElevenLabs voice clone.

This is the default voice for quickVid. One-time setup, then every reel uses it.

--- ONE-TIME SETUP -------------------------------------------------------------
  1. Put a 1-5 min sample of your voice in ./voice_sample/ (see the note there).
  2. Create the clone in ElevenLabs Voice Lab:  https://elevenlabs.io/app/voice-lab
     -> Add Voice -> Instant Voice Clone -> upload your sample -> save.
  3. Get an API key: https://elevenlabs.io/app/settings/api-keys . Put it in .env:
         ELEVEN_API_KEY=xxxxxxxx
  4. Verify everything and find your voice id:
         python elevenlabs_voice.py --check
  5. Save the id in .env:  ELEVEN_VOICE_ID=<your voice id>
     After this, --voice-id is optional; your clone is used automatically.

--- EVERY REEL -----------------------------------------------------------------
  python elevenlabs_voice.py --script prompts/script.txt
  # (uses ELEVEN_VOICE_ID from .env) -> writes ./voiceover/vo_eleven.mp3
  # or override:  --voice-id <ID>   /   inline text:  --text "..."
  # delivery style: --style warm|energetic|authoritative   (default warm)

ElevenLabs returns the spoken audio directly (no video step). Cost is per
character; after each call the characters used and your remaining quota are
printed, read from your ElevenLabs subscription.
"""

import argparse
import os
import sys
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except Exception:
    pass

ROOT = os.path.dirname(os.path.abspath(__file__))
VO_DIR = os.path.join(ROOT, "voiceover")
SAMPLE_DIR = os.path.join(ROOT, "voice_sample")
BASE = "https://api.elevenlabs.io"

DEFAULT_MODEL = os.environ.get("ELEVEN_MODEL_ID", "eleven_multilingual_v2")
USD_PER_1K_CHARS = float(os.environ.get("ELEVEN_USD_PER_1K_CHARS", "") or 0)

# Delivery presets (tuned per-style voice settings).
VOICE_SETTINGS = {
    "warm":          {"stability": 0.38, "similarity_boost": 0.82, "style": 0.08, "use_speaker_boost": False},
    "energetic":     {"stability": 0.30, "similarity_boost": 0.85, "style": 0.25, "use_speaker_boost": True},
    "authoritative": {"stability": 0.55, "similarity_boost": 0.75, "style": 0.15, "use_speaker_boost": False},
}


# --------------------------------------------------------------------------- #
# Auth / cost helpers
# --------------------------------------------------------------------------- #
def api_key(required=True):
    k = os.environ.get("ELEVEN_API_KEY")
    if not k and required:
        sys.exit("ERROR: ELEVEN_API_KEY not set. Add it to .env (see .env.example "
                 "and ReadME.MD -> one-time setup).")
    return k


def _headers(json=True):
    h = {"xi-api-key": api_key()}
    if json:
        h["Content-Type"] = "application/json"
    return h


def get_usage():
    """(characters_used, characters_limit) from the subscription, or (None, None)."""
    try:
        r = requests.get(f"{BASE}/v1/user/subscription", headers=_headers(False), timeout=30)
        if r.status_code == 200:
            d = r.json()
            return d.get("character_count"), d.get("character_limit")
    except Exception:
        pass
    return None, None


def report_cost(chars, used_after, limit):
    line = f"Voiceover cost: ~{chars} characters"
    if USD_PER_1K_CHARS > 0:
        line += f"  (~${chars / 1000 * USD_PER_1K_CHARS:.2f})"
    print(line)
    if used_after is not None and limit is not None:
        print(f"  Quota: {used_after}/{limit} characters used this period "
              f"({max(0, limit - used_after)} left).")
    else:
        print("  (set ELEVEN_USD_PER_1K_CHARS in .env for a $ estimate; "
              "quota unavailable.)")


# --------------------------------------------------------------------------- #
# Voices
# --------------------------------------------------------------------------- #
def fetch_voices():
    r = requests.get(f"{BASE}/v1/voices", headers=_headers(False), timeout=60)
    r.raise_for_status()
    return r.json().get("voices", [])


def list_voices():
    voices = fetch_voices()

    def sort_key(v):
        return (0 if v.get("category") == "cloned" else 1, v.get("name", "").lower())

    print(f"{'VOICE_ID':28} {'NAME':28} CATEGORY")
    print("-" * 74)
    for v in sorted(voices, key=sort_key):
        tag = "  <-- your clone" if v.get("category") == "cloned" else ""
        print(f"{v.get('voice_id',''):28} {v.get('name','')[:27]:28} "
              f"{v.get('category','')}{tag}")
    print("\nCopy your clone's voice_id into .env as ELEVEN_VOICE_ID=...")


def check_setup():
    """Verify the one-time setup is complete; print what (if anything) is missing."""
    print("=" * 60)
    print("ElevenLabs voice-clone setup check")
    print("=" * 60)
    ok = True

    samples = [f for f in (os.listdir(SAMPLE_DIR) if os.path.isdir(SAMPLE_DIR) else [])
               if os.path.splitext(f)[1].lower()
               in {".mp4", ".mov", ".wav", ".mp3", ".m4a", ".webm", ".flac"}]
    print(f"[{'ok ' if samples else '-- '}] voice sample in voice_sample/: "
          f"{samples[0] if samples else 'none yet (optional once cloned)'}")

    if not api_key(required=False):
        print("[FAIL] ELEVEN_API_KEY: not set in .env")
        print("\nAdd ELEVEN_API_KEY to .env, then re-run --check.")
        return False
    try:
        voices = fetch_voices()
        print(f"[ok ] ELEVEN_API_KEY: valid ({len(voices)} voices available)")
    except Exception as e:
        print(f"[FAIL] ELEVEN_API_KEY set but the API rejected it: {e}")
        return False

    used, limit = get_usage()
    if used is not None:
        print(f"[ok ] Character quota: {used}/{limit} used ({max(0, limit-used)} left).")
    else:
        print("[-- ] Could not read character quota (non-fatal).")

    vid = os.environ.get("ELEVEN_VOICE_ID")
    if not vid:
        ok = False
        print("[FAIL] ELEVEN_VOICE_ID: not set in .env")
        print("\nYour voices (pick your clone and add its id to .env):\n")
        list_voices()
    else:
        match = next((v for v in voices if v.get("voice_id") == vid), None)
        if match:
            print(f"[ok ] ELEVEN_VOICE_ID: {vid}  ({match.get('name','?')}, "
                  f"{match.get('category','?')})")
        else:
            ok = False
            print(f"[FAIL] ELEVEN_VOICE_ID {vid} is not in your ElevenLabs voices.")
            print("\nYour voices:\n")
            list_voices()

    print("=" * 60)
    print("SETUP COMPLETE - your cloned voice is the default." if ok
          else "SETUP INCOMPLETE - fix the FAIL line(s) above, then re-run --check.")
    print("=" * 60)
    return ok


# --------------------------------------------------------------------------- #
# Generation
# --------------------------------------------------------------------------- #
def generate(text, voice_id, out_path, style="warm", model_id=DEFAULT_MODEL):
    text = text.strip()
    if not text:
        sys.exit("ERROR: script/text is empty.")
    if not voice_id:
        sys.exit("ERROR: no voice id. Set ELEVEN_VOICE_ID in .env (run --check) "
                 "or pass --voice-id.")
    settings = VOICE_SETTINGS.get(style, VOICE_SETTINGS["warm"])

    print(f"Generating voiceover in your cloned voice ({style}, {model_id})...")
    r = requests.post(
        f"{BASE}/v1/text-to-speech/{voice_id}",
        headers=_headers(),
        json={"text": text, "model_id": model_id, "voice_settings": settings},
        timeout=180,
    )
    if r.status_code >= 400:
        sys.exit(f"ERROR: ElevenLabs rejected the request ({r.status_code}):\n"
                 f"{r.text[:600]}")

    os.makedirs(VO_DIR, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(r.content)

    used_after, limit = get_usage()
    report_cost(len(text), used_after, limit)

    print("\n" + "=" * 60)
    print("VOICEOVER READY (your cloned voice)")
    print("=" * 60)
    print(f"File: {out_path}")
    print("Next: make_reel.py picks this up automatically, or run:")
    print(f'  python make_reel.py --sound voiceover --vo "{out_path}"')
    print("=" * 60)


def main():
    ap = argparse.ArgumentParser(description="ElevenLabs voice-clone voiceover generator")
    ap.add_argument("--check", action="store_true",
                    help="Verify the one-time setup (key, clone, voice id) and stop.")
    ap.add_argument("--list-voices", action="store_true",
                    help="List your ElevenLabs voices (find your clone's voice_id).")
    ap.add_argument("--voice-id", default=os.environ.get("ELEVEN_VOICE_ID"),
                    help="Cloned voice id. Defaults to ELEVEN_VOICE_ID from .env.")
    ap.add_argument("--script", help="Path to a .txt file with the narration.")
    ap.add_argument("--text", help="Narration text passed inline (instead of --script).")
    ap.add_argument("--style", choices=list(VOICE_SETTINGS), default="warm",
                    help="Delivery style (default warm).")
    ap.add_argument("--out", default=os.path.join(VO_DIR, "vo_eleven.mp3"),
                    help="Output audio path (default voiceover/vo_eleven.mp3).")
    args = ap.parse_args()

    if args.check:
        sys.exit(0 if check_setup() else 1)
    if args.list_voices:
        list_voices()
        return

    if args.script:
        text = Path(args.script).read_text(encoding="utf-8")
    elif args.text:
        text = args.text
    else:
        sys.exit("ERROR: provide --script <file> or --text \"...\". "
                 "(First time? Run --check to set up your clone.)")

    generate(text, args.voice_id, args.out, style=args.style)


if __name__ == "__main__":
    main()
