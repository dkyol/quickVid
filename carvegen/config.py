"""Configuration: credentials, model/quality defaults, and job schema.

Two layers:
  - GLOBAL defaults + secrets (env / .env)   -> `Settings`
  - PER-JOB config (a JSON file)             -> `Job` / `Segment`

Keeping them separate means a job file is portable and secret-free, and the
recommended Kling settings live in ONE place (see RECOMMENDED_* below).
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), ".env"))
except Exception:
    pass

# --------------------------------------------------------------------------- #
# Recommended Kling settings for continuous carving videos.
#
# Why these:
#  - model kling-v2-master: best temporal consistency + motion realism, which
#    matters most here (the subject must stay the SAME across the whole carve).
#    kling-v1-6 is a cheaper fallback if v2 credits are tight.
#  - mode "pro": noticeably crisper detail than "std"; carving detail (rind
#    texture, shavings, wet flesh) is the whole appeal, so pay for pro.
#  - duration 5: shorter clips stay more on-model than 10s ones and give tighter
#    control over each carving stage. We reach a long video by STITCHING
#    several 5s segments, re-anchored by seed frames at each boundary.
#  - aspect_ratio 9:16: Reels/TikTok.
#  - cfg_scale 0.5: balance — high enough to follow the carving prompt, low
#    enough that motion stays natural (very high cfg makes motion stiff/warpy).
# --------------------------------------------------------------------------- #
RECOMMENDED_MODEL = "kling-v2-master"
RECOMMENDED_MODE = "pro"            # "std" | "pro"
RECOMMENDED_DURATION = 5            # Kling accepts 5 or 10 (seconds)
RECOMMENDED_ASPECT = "9:16"         # "16:9" | "9:16" | "1:1"
RECOMMENDED_CFG = 0.5              # 0.0 - 1.0

VALID_DURATIONS = (5, 10)
VALID_ASPECTS = ("16:9", "9:16", "1:1")
VALID_MODES = ("std", "pro")

# Output frame for the stitched reel (Kling returns close to this for 9:16).
DEFAULT_W, DEFAULT_H, DEFAULT_FPS = 1080, 1920, 30


@dataclass
class Settings:
    """Global secrets + endpoint config, from environment.

    Two Kling auth modes are supported:
      - PREFERRED: a single API key from https://kling.ai/dev, sent as
        `Authorization: Bearer <key>`. This is the current scheme and it
        covers the newest models.
      - LEGACY: an Access Key + Secret Key pair, signed into a JWT. Still
        works but won't unlock new models. Only used if no API key is set.
    """
    api_key: str = field(default_factory=lambda: os.environ.get("KLING_API_KEY", ""))
    access_key: str = field(default_factory=lambda: os.environ.get("KLING_ACCESS_KEY", ""))
    secret_key: str = field(default_factory=lambda: os.environ.get("KLING_SECRET_KEY", ""))
    # Global/Singapore: https://api-singapore.klingai.com (default; matches the
    # kling.ai/dev key). Mainland: https://api.klingai.com. Override KLING_API_BASE.
    api_base: str = field(default_factory=lambda: os.environ.get(
        "KLING_API_BASE", "https://api-singapore.klingai.com"))
    # Optional: xAI key, only used if you ask carvegen to GENERATE seed stills
    # (Grok images) instead of supplying your own. Video is always Kling.
    xai_api_key: str = field(default_factory=lambda: os.environ.get("XAI_API_KEY", ""))

    def require_kling(self):
        if not self.api_key and not (self.access_key and self.secret_key):
            raise SystemExit(
                "ERROR: no Kling credentials. Set KLING_API_KEY (from "
                "https://kling.ai/dev) in .env — or a legacy KLING_ACCESS_KEY + "
                "KLING_SECRET_KEY pair. See .env.example and CARVEGEN.md.")


@dataclass
class Segment:
    """One carving stage -> one Kling generation."""
    name: str
    stage: str = "deep_carving"          # outline|peeling|deep_carving|final_details
    duration: int = RECOMMENDED_DURATION  # 5 or 10
    seconds: Optional[float] = None       # timeline slot (defaults to duration)
    start_image: Optional[str] = None     # seed -> image-to-video (preferred)
    end_image: Optional[str] = None       # optional end keyframe (image_tail)
    prompt_extra: str = ""                # appended to the built stage prompt
    prompt_override: Optional[str] = None  # bypass the template entirely
    cfg_scale: Optional[float] = None      # per-segment override

    def timeline_seconds(self):
        return self.seconds if self.seconds is not None else float(self.duration)


@dataclass
class Output:
    crossfade: float = 0.4
    keep_source_audio: bool = True   # keep each clip's own foley (no music)
    music: Optional[str] = None      # path to a music bed (overrides foley)
    width: int = DEFAULT_W
    height: int = DEFAULT_H
    fps: int = DEFAULT_FPS


@dataclass
class Job:
    """A full carving video job (one JSON file)."""
    project: str
    subject: str                      # e.g. "snarling gray wolf head"
    material: str = "watermelon"      # "watermelon" | "wood"
    style: str = "hyperrealistic fruit carving, macro process video"
    model: str = RECOMMENDED_MODEL
    mode: str = RECOMMENDED_MODE
    aspect_ratio: str = RECOMMENDED_ASPECT
    cfg_scale: float = RECOMMENDED_CFG
    negative_prompt: Optional[str] = None   # None -> use material default
    segments: list = field(default_factory=list)
    output: Output = field(default_factory=Output)

    @staticmethod
    def load(path):
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        segs = [Segment(**s) for s in raw.pop("segments", [])]
        out = Output(**raw.pop("output", {}))
        job = Job(segments=segs, output=out, **raw)
        job.validate()
        return job

    def validate(self):
        if self.aspect_ratio not in VALID_ASPECTS:
            raise SystemExit(f"aspect_ratio must be one of {VALID_ASPECTS}")
        if self.mode not in VALID_MODES:
            raise SystemExit(f"mode must be one of {VALID_MODES}")
        if not self.segments:
            raise SystemExit("job has no segments")
        for s in self.segments:
            if s.duration not in VALID_DURATIONS:
                raise SystemExit(
                    f"segment {s.name}: duration must be one of {VALID_DURATIONS} "
                    f"(Kling only generates 5s or 10s clips).")

    def project_dir(self, root):
        return os.path.join(root, self.project)

    def to_json(self):
        d = asdict(self)
        return json.dumps(d, indent=2)
