#!/usr/bin/env python3
"""
generate_shots.py — Generate the shots listed in a shots.json via the xAI
(Grok) generation API. See imageGenSkill.MD for the full pipeline, endpoint
contracts, and the shots.json format.

Shot types:
  - "image"          — text-to-image (grok-imagine-image / -image-quality).
  - "video"          — text-to-video (grok-imagine-video / -1.5), async.
  - "image_to_video" — animate a seed still into a video: the seed becomes
                       the FIRST frame, so the clip provably starts from a
                       known state (e.g. a plain uncarved watermelon) and
                       transforms. This is the reliable way to get a
                       continuous "being carved" reveal — see imageGenSkill.MD
                       section 6.

--- ONE-TIME SETUP -------------------------------------------------------------
  Get a key at https://console.x.ai (API Keys). Put it in .env:
      XAI_API_KEY=xxxxxxxx
  Verify it works:
      python generate_shots.py --check

--- EVERY JOB ----------------------------------------------------------------
  python generate_shots.py --shots wolf_reel/shots.json
  python generate_shots.py --shots wolf_reel/shots.json --shot 01_carve

Output goes to <project>/media/<name>.png or <name>.mp4 (or
<name>_take1.png... for images when --n > 1 — pick your favorite and rename
it to drop the _takeN suffix). Video shots always produce one take (each
generation is slow/async and billed, so --n is ignored for them).
"""

import argparse
import base64
import json
import mimetypes
import os
import sys
import time

import requests

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except Exception:
    pass

ROOT = os.path.dirname(os.path.abspath(__file__))
IMAGES_URL = "https://api.x.ai/v1/images/generations"
EDITS_URL = "https://api.x.ai/v1/images/edits"
VIDEOS_URL = "https://api.x.ai/v1/videos/generations"
VIDEO_STATUS_URL = "https://api.x.ai/v1/videos/{request_id}"

DEFAULT_IMAGE_MODEL = os.environ.get("XAI_IMAGE_MODEL", "grok-imagine-image")
DEFAULT_VIDEO_MODEL = os.environ.get("XAI_VIDEO_MODEL", "grok-imagine-video")

VIDEO_POLL_SECONDS = 5
VIDEO_TIMEOUT_SECONDS = 600

IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp")

_PING_PROMPT = "A simple test image of a red circle on a white background."


def api_key(required=True):
    k = os.environ.get("XAI_API_KEY")
    if not k and required:
        sys.exit("ERROR: XAI_API_KEY not set. Paste it into .env (see "
                  "imageGenSkill.MD).")
    return k


def _headers():
    return {"Authorization": f"Bearer {api_key()}", "Content-Type": "application/json"}


def load_shots(path):
    if not os.path.isfile(path):
        sys.exit(f"ERROR: shots file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "shots" not in data or not data["shots"]:
        sys.exit(f"ERROR: {path} has no \"shots\" list.")
    return data


def media_dir(shots_path):
    return os.path.join(os.path.dirname(os.path.abspath(shots_path)), "media")


def download(url, dst):
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    with open(dst, "wb") as f:
        f.write(r.content)


def file_to_data_uri(path):
    mime = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{b64}"


# --------------------------------------------------------------------------- #
# Images
# --------------------------------------------------------------------------- #
def generate_image(prompt, model, n=1):
    r = requests.post(IMAGES_URL, headers=_headers(),
                       json={"model": model, "prompt": prompt, "n": n,
                             "response_format": "url"},
                       timeout=120)
    if r.status_code != 200:
        sys.exit(f"ERROR: xAI images API returned {r.status_code}: {r.text[:800]}")
    data = r.json().get("data", [])
    if not data:
        sys.exit(f"ERROR: no images returned: {r.text[:800]}")
    return data


def edit_image(prompt, image, model="grok-imagine-image-quality"):
    """Natural-language edit of an existing image (POST /v1/images/edits).

    `image` is a local path or URL. Returns the result image URL. This is the
    ladder builder's workhorse: regressing a finished master still to earlier
    carve stages preserves composition/palette in a way fresh text-to-image
    never does (t2i renders finished subjects — measured 2026-07-26).
    """
    url = image if str(image).startswith("http") else file_to_data_uri(image)
    r = requests.post(EDITS_URL, headers=_headers(),
                       json={"model": model, "prompt": prompt,
                             "image": {"url": url, "type": "image_url"},
                             "response_format": "url"},
                       timeout=180)
    if r.status_code != 200:
        sys.exit(f"ERROR: xAI edits API returned {r.status_code}: {r.text[:800]}")
    data = r.json().get("data", [])
    if not data:
        sys.exit(f"ERROR: no edited image returned: {r.text[:800]}")
    return data[0]["url"]


# --------------------------------------------------------------------------- #
# Video (async: submit -> poll -> download). image_url set => image-to-video.
# --------------------------------------------------------------------------- #
def generate_video(prompt, model, aspect_ratio=None, duration=None, image_url=None,
                    resolution=None):
    body = {"model": model, "prompt": prompt}
    if aspect_ratio:
        body["aspect_ratio"] = aspect_ratio
    if duration:
        body["duration"] = duration
    if resolution:
        body["resolution"] = resolution
    if image_url:
        body["image"] = {"url": image_url}
    r = requests.post(VIDEOS_URL, headers=_headers(), json=body, timeout=120)
    if r.status_code != 200:
        sys.exit(f"ERROR: xAI videos API returned {r.status_code}: {r.text[:800]}")
    request_id = r.json().get("request_id")
    if not request_id:
        sys.exit(f"ERROR: no request_id returned: {r.text[:800]}")

    waited = 0
    while waited <= VIDEO_TIMEOUT_SECONDS:
        time.sleep(VIDEO_POLL_SECONDS)
        waited += VIDEO_POLL_SECONDS
        pr = requests.get(VIDEO_STATUS_URL.format(request_id=request_id),
                           headers=_headers(), timeout=60)
        if pr.status_code not in (200, 202):
            sys.exit(f"ERROR: status check returned {pr.status_code}: {pr.text[:800]}")
        result = pr.json()
        status = result.get("status")
        print(f"  ...{status} ({waited}s, progress={result.get('progress', '?')})")
        if status == "done":
            return result["video"]["url"]
        if status in ("failed", "expired"):
            sys.exit(f"ERROR: video generation {status}: {json.dumps(result)}")
    sys.exit(f"ERROR: video generation timed out after {VIDEO_TIMEOUT_SECONDS}s "
              f"(request_id={request_id})")


def resolve_seed(seed, out_dir, generated_urls):
    """Turn a shot's `seed` into a value usable as image-to-video input.

    A seed may be:
      - the name of an image shot generated earlier in THIS run -> its fresh
        result URL (preferred; no re-upload),
      - an http(s) URL -> passed through,
      - a path to a local image (absolute, or relative to media/, with or
        without extension) -> encoded as a base64 data URI.
    """
    if seed in generated_urls:
        return generated_urls[seed]
    if seed.startswith("http://") or seed.startswith("https://"):
        return seed
    # Local file: try as given, and relative to media/ and a sibling seeds/
    # folder, with and without each image extension. User-provided seed
    # images can live in either <project>/media/ or <project>/seeds/.
    seeds_dir = os.path.join(os.path.dirname(out_dir), "seeds")
    bases = [seed, os.path.join(out_dir, seed), os.path.join(seeds_dir, seed)]
    candidates = list(bases)
    for base in bases:
        for ext in IMAGE_EXT:
            candidates.append(base + ext)
    for c in candidates:
        if os.path.isfile(c):
            return file_to_data_uri(c)
    sys.exit(f"ERROR: could not resolve seed '{seed}' — not a generated shot "
              f"name from this run, not a URL, and no local file found "
              f"(looked for {seed}[.png/.jpg/...] in media/ and seeds/).")


def check():
    k = api_key(required=False)
    if not k:
        print("[FAIL] XAI_API_KEY: not set in .env")
        sys.exit(1)
    try:
        data = generate_image(_PING_PROMPT, DEFAULT_IMAGE_MODEL, n=1)
        print(f"[ok ] XAI_API_KEY valid, image model={DEFAULT_IMAGE_MODEL}, "
              f"got {len(data)} image(s)")
    except SystemExit:
        raise
    except Exception as e:
        print(f"[FAIL] XAI_API_KEY set but request failed: {e}")
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", help="Path to a shots.json (see imageGenSkill.MD).")
    ap.add_argument("--shot", default=None,
                     help="Regenerate only this shot by name. Default: all shots. "
                          "(An image_to_video shot whose seed was generated in "
                          "the same run needs the seed present too; if you "
                          "regenerate just the video, its seed is loaded from "
                          "the saved media/<seed>.png instead.)")
    ap.add_argument("--n", type=int, default=1,
                     help="Candidates per image shot (default 1); ignored for "
                          "video and image_to_video shots.")
    ap.add_argument("--check", action="store_true",
                     help="Verify XAI_API_KEY works and exit.")
    args = ap.parse_args()

    if args.check:
        check()
        return

    if not args.shots:
        sys.exit("ERROR: --shots <path/to/shots.json> is required "
                  "(or use --check).")

    config = load_shots(args.shots)
    out_dir = media_dir(args.shots)
    os.makedirs(out_dir, exist_ok=True)

    image_model = config.get("image_model", DEFAULT_IMAGE_MODEL)
    video_model = config.get("video_model", DEFAULT_VIDEO_MODEL)
    aspect_ratio = config.get("aspect_ratio")
    # 480p | 720p | 1080p — omitted defaults to 480p (848x480), so always set
    # this for a deliverable. Per-shot "resolution" overrides.
    resolution = config.get("resolution")

    all_shots = config["shots"]
    if args.shot:
        shots = [s for s in all_shots if s["name"] == args.shot]
        if not shots:
            sys.exit(f"ERROR: no shot named '{args.shot}' in {args.shots}")
    else:
        shots = all_shots

    generated_urls = {}  # shot name -> fresh result URL (for seed reuse)

    for shot in shots:
        name, prompt = shot["name"], shot["prompt"]
        shot_type = shot.get("type", "image")

        if shot_type == "image":
            model = shot.get("model") or image_model
            print(f"Generating {name} (image, model={model}, n={args.n})...")
            data = generate_image(prompt, model, n=args.n)
            for i, item in enumerate(data, start=1):
                suffix = f"_take{i}.png" if args.n > 1 else ".png"
                dst = os.path.join(out_dir, name + suffix)
                download(item["url"], dst)
                print(f"  -> {dst}")
            if args.n == 1:
                generated_urls[name] = data[0]["url"]

        elif shot_type in ("video", "image_to_video"):
            model = shot.get("model") or video_model
            shot_ar = shot.get("aspect_ratio", aspect_ratio)
            duration = shot.get("duration")
            shot_res = shot.get("resolution", resolution)
            image_url = None
            if shot_type == "image_to_video":
                seed = shot.get("seed")
                if not seed:
                    sys.exit(f"ERROR: shot '{name}' is image_to_video but has "
                              f"no \"seed\".")
                image_url = resolve_seed(seed, out_dir, generated_urls)
                print(f"Generating {name} (image_to_video, model={model}, "
                      f"aspect_ratio={shot_ar}, resolution={shot_res}, "
                      f"duration={duration}, seed={seed})...")
            else:
                print(f"Generating {name} (video, model={model}, "
                      f"aspect_ratio={shot_ar}, resolution={shot_res}, "
                      f"duration={duration})...")
            url = generate_video(prompt, model, shot_ar, duration, image_url,
                                  resolution=shot_res)
            dst = os.path.join(out_dir, name + ".mp4")
            download(url, dst)
            print(f"  -> {dst}")

        else:
            sys.exit(f"ERROR: shot '{name}' has unknown type '{shot_type}' "
                      f"(expected image, video, or image_to_video).")

    print(f"\nDone. Media in {out_dir}")
    if args.n > 1:
        print("Pick your favorite take for each image shot and rename it to "
              "drop the _takeN suffix (e.g. 02_fur_take2.png -> 02_fur.png).")


if __name__ == "__main__":
    main()
