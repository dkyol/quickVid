"""Seed images: resolve user-provided files, or OPTIONALLY generate a starting
still with Grok (xAI) images when you have no frame to supply.

Video generation is always Kling. Seed image generation is optional and
pluggable — Grok is used here only because the key is already configured; you
could swap in Kling's Kolors image endpoint or any other generator behind the
same `generate_seed()` signature.

Seeds are looked up in <project>/seeds/ then <project>/media/, by exact name or
with a common image extension appended.
"""

import logging
import os

import requests

log = logging.getLogger(__name__)

IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp")
_XAI_IMAGES_URL = "https://api.x.ai/v1/images/generations"


def resolve_seed(ref, project_dir):
    """Turn a segment's start_image/end_image value into a local file path or
    URL usable by the Kling client. Returns the value unchanged if it is a URL
    or an existing absolute path; otherwise searches project seeds/ and media/."""
    if not ref:
        return None
    if ref.startswith("http://") or ref.startswith("https://") or os.path.isfile(ref):
        return ref
    seeds_dir = os.path.join(project_dir, "seeds")
    media_dir = os.path.join(project_dir, "media")
    bases = []
    for d in (seeds_dir, media_dir):
        bases += [os.path.join(d, ref)]
    candidates = list(bases)
    for b in bases:
        candidates += [b + e for e in IMAGE_EXT]
    for c in candidates:
        if os.path.isfile(c):
            return c
    raise SystemExit(
        f"ERROR: seed '{ref}' not found in {seeds_dir} or {media_dir} "
        f"(tried exact and {'/'.join(IMAGE_EXT)}).")


def generate_seed(prompt, dst, xai_api_key, model="grok-imagine-image"):
    """Optionally generate a starting still via Grok images. Saves to `dst`.
    Only used when a job/segment asks carvegen to make its own seed."""
    if not xai_api_key:
        raise SystemExit("ERROR: seed generation requested but XAI_API_KEY is "
                          "not set. Provide your own seed image instead, or set "
                          "XAI_API_KEY in .env.")
    log.info("generating seed image via Grok: %s", os.path.basename(dst))
    r = requests.post(
        _XAI_IMAGES_URL,
        headers={"Authorization": f"Bearer {xai_api_key}",
                 "Content-Type": "application/json"},
        json={"model": model, "prompt": prompt, "n": 1, "response_format": "url"},
        timeout=120)
    if r.status_code != 200:
        raise SystemExit(f"ERROR: Grok image API {r.status_code}: {r.text[:400]}")
    url = r.json()["data"][0]["url"]
    img = requests.get(url, timeout=120)
    img.raise_for_status()
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "wb") as f:
        f.write(img.content)
    return dst
