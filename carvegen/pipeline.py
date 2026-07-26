"""Generation pipeline: turn a Job into a finished reel.

Flow per job:
  1. For each segment: build its prompt, resolve seed frame(s), generate the
     clip on Kling (image-to-video when a seed exists, else text-to-video),
     download to <project>/media/<name>.mp4.
  2. Stitch all segments into <project>/final/<project>_<stamp>.mp4.
  3. Write a result manifest (prompts, task settings, paths) to <project>/final/.

Separation of concerns: this module only ORCHESTRATES — prompt text comes from
prompts.py, API calls from kling_client.py, seed resolution from seeds.py, and
stitching from post.py.
"""

import json
import logging
import os
from datetime import datetime

from . import prompts, seeds
from .kling_client import KlingClient, KlingError

log = logging.getLogger(__name__)


def _stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def generate_segment(job, segment, client, project_dir, *, dry_run=False):
    """Generate one segment; return dict with prompt, paths, and settings."""
    prompt = prompts.build_segment_prompt(job, segment)
    neg = prompts.negative_for(job.material, job.negative_prompt)
    if dry_run:
        # Don't require seed files to exist yet when only previewing prompts.
        start, end = segment.start_image, segment.end_image
    else:
        start = seeds.resolve_seed(segment.start_image, project_dir)
        end = seeds.resolve_seed(segment.end_image, project_dir)
    cfg = segment.cfg_scale if segment.cfg_scale is not None else job.cfg_scale
    kind = "image2video" if (start or end) else "text2video"

    record = {
        "name": segment.name, "stage": segment.stage, "kind": kind,
        "duration": segment.duration, "prompt": prompt, "negative_prompt": neg,
        "start_image": start, "end_image": end, "cfg_scale": cfg,
    }

    log.info("[%s] %s (%s, %ds)", segment.name, segment.stage, kind, segment.duration)
    log.debug("prompt: %s", prompt)
    if dry_run:
        record["output"] = None
        return record

    url = client.generate(
        prompt=prompt, model=job.model, mode=job.mode,
        aspect_ratio=job.aspect_ratio, duration=segment.duration,
        cfg_scale=cfg, start_image=start, end_image=end, negative_prompt=neg)
    dst = os.path.join(project_dir, "media", f"{segment.name}.mp4")
    client.download(url, dst)
    log.info("[%s] downloaded -> %s", segment.name, dst)
    record["output"] = dst
    record["source_url"] = url
    return record


def run_job(job, settings, root, *, dry_run=False, skip_existing=False):
    """Generate + stitch a whole job. Returns the manifest dict."""
    from . import post  # local import so --dry-run works without ffmpeg present

    project_dir = job.project_dir(root)
    os.makedirs(os.path.join(project_dir, "media"), exist_ok=True)
    # Credentials/client only needed for real generation; --dry-run stays free
    # and offline so you can vet prompts without keys.
    client = None
    if not dry_run:
        settings.require_kling()
        client = KlingClient.from_settings(settings)

    records, seg_files, seg_secs = [], [], []
    for seg in job.segments:
        dst = os.path.join(project_dir, "media", f"{seg.name}.mp4")
        if skip_existing and os.path.isfile(dst) and not dry_run:
            log.info("[%s] exists, skipping generation", seg.name)
            rec = {"name": seg.name, "output": dst, "reused": True}
        else:
            rec = generate_segment(job, seg, client, project_dir, dry_run=dry_run)
        records.append(rec)
        if rec.get("output"):
            seg_files.append(rec["output"])
            seg_secs.append(seg.timeline_seconds())

    manifest = {
        "project": job.project, "subject": job.subject, "material": job.material,
        "model": job.model, "mode": job.mode, "aspect_ratio": job.aspect_ratio,
        "created": _stamp(), "segments": records, "final": None,
    }

    if not dry_run and seg_files:
        out = os.path.join(project_dir, "final",
                           f"{job.project}_{_stamp()}.mp4")
        post.stitch(seg_files, seg_secs, out,
                    width=job.output.width, height=job.output.height,
                    fps=job.output.fps, crossfade=job.output.crossfade,
                    keep_source_audio=job.output.keep_source_audio,
                    music=job.output.music)
        manifest["final"] = out

    # Write manifest next to the output for reproducibility.
    man_dir = os.path.join(project_dir, "final")
    os.makedirs(man_dir, exist_ok=True)
    man_path = os.path.join(man_dir, f"{job.project}_{_stamp()}_manifest.json")
    with open(man_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    log.info("manifest -> %s", man_path)
    if manifest["final"]:
        log.info("DONE -> %s", manifest["final"])
    return manifest


def run_batch(job_paths, settings, root, **kw):
    """Generate several jobs in sequence. Continues past a failed job so one
    bad prompt doesn't sink the batch; returns per-job results."""
    from .config import Job
    results = []
    for p in job_paths:
        log.info("=== job: %s ===", p)
        try:
            job = Job.load(p)
            results.append({"job": p, "manifest": run_job(job, settings, root, **kw)})
        except (SystemExit, KlingError, Exception) as e:  # noqa: BLE001
            log.error("job %s failed: %s", p, e)
            results.append({"job": p, "error": str(e)})
    return results
