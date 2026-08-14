"""Full 30s Seedance 2.5 R2V+Audio generation on Atlas Cloud, 1080p-esr."""
import base64
import json
import sys
import time

import requests

ENV_PATH = r"C:\Users\DKYLE\Desktop\scripts\quickVid\.env"
IMAGE_PATH = r"C:\Users\DKYLE\Downloads\mupped_instgram.JPG"
AUDIO_PATH = r"C:\Users\DKYLE\Desktop\scripts\quickVid\work\dancingMuppet\hook_full30.mp3"
OUT_PATH = r"C:\Users\DKYLE\Desktop\scripts\quickVid\work\dancingMuppet\atlascloud_full30.mp4"

API_BASE = "https://api.atlascloud.ai/api/v1/model"


def load_env(path):
    env = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def data_uri(path, mime):
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{b64}"


PROMPT = """@Image1 is the character and the exact style reference: a round green felt-and-fleece plush creature with a dense fuzzy fur texture rendered in soft studio lighting, wearing a black knit beanie and scarf with a white "DC" logo. Match @Image1's exact rendering style, material quality, fur density, and lighting throughout the video.

Hold its exact build from @Image1: wide round eyes with visible white sclera and warm brown iris with a bright catchlight, a small nose, and an open smiling mouth with a hint of pink tongue — keep this exact face the whole video. Body plan: no separate arms or legs — only one soft round paw resting at its side and small foot nubs at the bottom; it dances by bouncing, rocking, and swaying its whole round body, and swinging its one paw, never growing human arms, legs, elbows, or knees.

Cut the choreography to the rhythm of @Audio1 across the full 30 seconds. The motion must be LARGE and OBVIOUS the entire time — full-body squash and stretch on every beat, not a subtle sway or idle animation. Big, committed, exaggerated Afrobeats groove throughout.
0-4.5s: dips down hard into a low bouncy crouch and springs back up tall repeatedly, weight shifting side to side, paw pumping like an arm accent.
4.5-8.9s: stays low and wide, quick large side-to-side weight shifts, paw swinging hard on each accent hit.
8.9-13.3s: bigger dips down and springs back up tall, alternating sides, head bobbing hard with the bounce.
13.3-17.7s: rapid large bounces low to the ground, paw pumping fast on the double-time beat.
17.7-22.0s: leans and rocks hard side to side while staying in the low bouncy stance, paw thrown out wide on accents.
22.0-26.4s: one huge dramatic dip down low, then bursts back up tall on the beat, paw raised high.
26.4-30.0s: settles back into the steady large bouncy groove from the opening, ending in a planted stance like @Image1.

Mouth stays closed, no singing. Static locked-off camera, medium shot, the character stays centered in frame, camera does not pan, zoom, or move. The character's colors, proportions, fur texture, and face never change from @Image1."""


def main():
    env = load_env(ENV_PATH)
    api_key = env.get("ATLASCLOUD_API_KEY")
    if not api_key:
        print("ATLASCLOUD_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    image_uri = data_uri(IMAGE_PATH, "image/jpeg")
    audio_uri = data_uri(AUDIO_PATH, "audio/mpeg")

    payload = {
        "model": "bytedance/seedance-2.5/reference-to-video",
        "reference_images": [image_uri],
        "reference_audios": [audio_uri],
        "prompt": PROMPT,
        "duration": 30,
        "resolution": "1080p-esr",
        "ratio": "9:16",
        "generate_audio": True,
        "watermark": False,
    }

    print("Submitting full 30s generation at 1080p-esr...", file=sys.stderr)
    resp = requests.post(f"{API_BASE}/generateVideo", headers=headers, json=payload, timeout=60)
    print(f"HTTP {resp.status_code}", file=sys.stderr)
    print(resp.text[:2000], file=sys.stderr)
    resp.raise_for_status()
    body = resp.json()
    data = body.get("data", body)

    prediction_id = data.get("id")
    poll_url = (data.get("urls") or {}).get("get") or f"{API_BASE}/prediction/{prediction_id}"
    print(f"prediction_id={prediction_id}", file=sys.stderr)
    print(f"poll_url={poll_url}", file=sys.stderr)

    for attempt in range(180):
        r = requests.get(poll_url, headers=headers, timeout=30)
        r.raise_for_status()
        rbody = r.json()
        d = rbody.get("data", rbody)
        status = d.get("status")
        print(f"[{attempt}] status={status}", file=sys.stderr)
        if status == "completed":
            print(json.dumps(d, indent=2)[:3000], file=sys.stderr)
            outputs = d.get("outputs") or []
            if not outputs:
                print("Completed but no outputs field found", file=sys.stderr)
                sys.exit(1)
            video_url = outputs[0] if isinstance(outputs[0], str) else outputs[0].get("url")
            vr = requests.get(video_url, timeout=180)
            vr.raise_for_status()
            with open(OUT_PATH, "wb") as f:
                f.write(vr.content)
            print(f"Saved to {OUT_PATH}", file=sys.stderr)
            return
        if status in ("failed", "timeout", "error"):
            print(json.dumps(d, indent=2), file=sys.stderr)
            sys.exit(1)
        time.sleep(6)

    print("Timed out waiting for completion", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
