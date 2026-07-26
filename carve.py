#!/usr/bin/env python3
"""
carve.py — CLI for carvegen (Kling-powered continuous carving videos).

Examples
--------
  # verify Kling credentials work
  python carve.py check

  # see the prompts a job will send WITHOUT generating (free)
  python carve.py gen jobs/wolf_watermelon.json --dry-run

  # generate + stitch one job
  python carve.py gen jobs/wolf_watermelon.json

  # only (re)generate missing segments, then re-stitch
  python carve.py gen jobs/wolf_watermelon.json --skip-existing

  # batch several jobs
  python carve.py batch jobs/wolf_watermelon.json jobs/lion_wood.json

  # plan seeds from a reference video (how many frames, at what times)
  python carve.py plan "C:/path/ref.mp4" --project wolf_watermelon --every 4

Credentials live in .env: KLING_ACCESS_KEY, KLING_SECRET_KEY (see CARVEGEN.md).
"""

import argparse
import logging
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from carvegen.config import Job, Settings          # noqa: E402
from carvegen.logging_setup import setup_logging    # noqa: E402
from carvegen import pipeline                        # noqa: E402


def cmd_check(args, settings, log):
    settings.require_kling()
    from carvegen.kling_client import KlingClient, KlingError
    client = KlingClient.from_settings(settings)
    try:
        client.auth_check()
        log.info("[ok] Kling auth works (base=%s)", settings.api_base)
    except KlingError as e:
        log.error("[FAIL] Kling auth: %s", e)
        sys.exit(1)


def cmd_gen(args, settings, log):
    job = Job.load(args.job)
    pipeline.run_job(job, settings, ROOT,
                     dry_run=args.dry_run, skip_existing=args.skip_existing)


def cmd_batch(args, settings, log):
    results = pipeline.run_batch(args.jobs, settings, ROOT,
                                 dry_run=args.dry_run,
                                 skip_existing=args.skip_existing)
    ok = sum(1 for r in results if "manifest" in r)
    log.info("batch done: %d/%d jobs ok", ok, len(results))
    if ok < len(results):
        sys.exit(1)


def cmd_plan(args, settings, log):
    # Thin wrapper over the standalone planner so everything is one CLI.
    import runpy
    sys.argv = ["plan_seeds.py", args.reference, "--project", args.project,
                "--every", str(args.every)]
    if args.count:
        sys.argv += ["--count", str(args.count)]
    runpy.run_path(os.path.join(ROOT, "plan_seeds.py"), run_name="__main__")


def main():
    ap = argparse.ArgumentParser(description="carvegen — Kling carving videos")
    ap.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check", help="verify Kling credentials")

    g = sub.add_parser("gen", help="generate + stitch one job")
    g.add_argument("job")
    g.add_argument("--dry-run", action="store_true",
                   help="print prompts, generate nothing (free)")
    g.add_argument("--skip-existing", action="store_true",
                   help="reuse already-downloaded segment clips")

    b = sub.add_parser("batch", help="generate several jobs")
    b.add_argument("jobs", nargs="+")
    b.add_argument("--dry-run", action="store_true")
    b.add_argument("--skip-existing", action="store_true")

    p = sub.add_parser("plan", help="plan seeds from a reference video")
    p.add_argument("reference")
    p.add_argument("--project", required=True)
    p.add_argument("--every", type=float, default=4.0)
    p.add_argument("--count", type=int, default=None)

    args = ap.parse_args()
    log = setup_logging(logging.DEBUG if args.verbose else logging.INFO)
    settings = Settings()

    {"check": cmd_check, "gen": cmd_gen, "batch": cmd_batch,
     "plan": cmd_plan}[args.cmd](args, settings, log)


if __name__ == "__main__":
    main()
