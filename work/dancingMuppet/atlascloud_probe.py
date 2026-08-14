"""Experiment-0-equivalent probe on Atlas Cloud: does reference_audios drive beat-locked motion?"""
import base64
import json
import os
import sys
import time

import requests

ENV_PATH = r"C:\Users\DKYLE\Desktop\scripts\quickVid\.env"
IMAGE_PATH = r"C:\Users\DKYLE\Downloads\mupped_instgram.JPG"
AUDIO_PATH = r"C:\Users\DKYLE\Desktop\scripts\quickVid\work\dancingMuppet\probe_audio.mp3"
OUT_PATH = r"C:\Users\DKYLE\Desktop\scripts\quickVid\work\dancingMuppet\atlascloud_probe2.mp4"

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

    prompt = (
        "The character in the reference image is a round green felt-and-fleece plush "
        "creature, dense fuzzy fiber texture, wearing a black knit beanie and scarf with "
        "a white \"DC\" logo. Hold its exact build from the reference image: wide round "
        "eyes with visible white sclera and warm brown iris with a bright catchlight, a "
        "small nose, and an open smiling mouth with a hint of pink tongue — keep this "
        "exact face the whole video. Body plan: no separate arms or legs — only one soft "
        "round paw resting at its side and small foot nubs at the bottom.\n\n"
        "Cut the choreography to the rhythm of the reference audio, dancing a committed, "
        "full-amplitude Afrobeats groove — big confident movement, not a gentle sway. "
        "It dips down into a low bouncy crouch and springs back up tall repeatedly, hard "
        "on every beat, weight shifting side to side each time, paw pumping like an arm "
        "accent, head bobbing with the bounce. The motion should be large and obvious, "
        "not a subtle sway — full-body squash and stretch on every beat.\n\n"
        "Mouth stays closed, no singing. Locked-off camera, the character stays centered "
        "in frame, camera does not pan, zoom, or move."
    )

    payload = {
        "model": "bytedance/seedance-2.5/reference-to-video",
        "reference_images": [image_uri],
        "reference_audios": [audio_uri],
        "prompt": prompt,
        "duration": 5,
        "resolution": "720p",
        "ratio": "9:16",
        "generate_audio": True,
        "watermark": False,
    }

    print("Submitting generation...", file=sys.stderr)
    resp = requests.post(f"{API_BASE}/generateVideo", headers=headers, json=payload, timeout=60)
    print(f"HTTP {resp.status_code}", file=sys.stderr)
    print(resp.text[:2000], file=sys.stderr)
    resp.raise_for_status()
    body = resp.json()
    data = body.get("data", body)

    prediction_id = data.get("id") or data.get("prediction_id") or data.get("predictionId")
    poll_url = (data.get("urls") or {}).get("get") or f"{API_BASE}/prediction/{prediction_id}"
    if not prediction_id:
        print("No prediction id in response, dumping full body:", file=sys.stderr)
        print(json.dumps(body, indent=2), file=sys.stderr)
        sys.exit(1)

    print(f"prediction_id={prediction_id}", file=sys.stderr)
    print(f"poll_url={poll_url}", file=sys.stderr)

    for attempt in range(90):
        r = requests.get(poll_url, headers=headers, timeout=30)
        r.raise_for_status()
        rbody = r.json()
        d = rbody.get("data", rbody)
        status = d.get("status")
        print(f"[{attempt}] status={status}", file=sys.stderr)
        if status == "completed":
            outputs = d.get("outputs") or d.get("output") or []
            print(json.dumps(d, indent=2)[:3000], file=sys.stderr)
            if not outputs:
                print("Completed but no outputs field found", file=sys.stderr)
                sys.exit(1)
            video_url = outputs[0] if isinstance(outputs[0], str) else outputs[0].get("url")
            vr = requests.get(video_url, timeout=120)
            vr.raise_for_status()
            with open(OUT_PATH, "wb") as f:
                f.write(vr.content)
            print(f"Saved to {OUT_PATH}", file=sys.stderr)
            print(json.dumps({"usage": d.get("usage"), "cost": d.get("cost")}, indent=2))
            return
        if status in ("failed", "timeout", "error"):
            print(json.dumps(d, indent=2), file=sys.stderr)
            sys.exit(1)
        time.sleep(5)

    print("Timed out waiting for completion", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
