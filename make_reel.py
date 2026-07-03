#!/usr/bin/env python3
"""
make_reel.py — Stitch the pictures and videos in ./media/ into one
Instagram-ready vertical reel (9:16, 1080x1920) and save it, datetime-stamped,
into ./final/.

You normally do NOT run this by hand — follow ReadME.MD and let Claude call it
with the right flags after asking you the sound question. But it also works
standalone:

    # Silent reel (add music later in the Instagram upload screen):
    python make_reel.py --sound none

    # Reel with a voiceover you already have as a file:
    python make_reel.py --sound voiceover --vo voiceover/my_track.mp3

    # Reel with a voiceover generated from your ElevenLabs voice clone:
    #   (first run elevenlabs_voice.py to produce the .mp3, then pass it here)
    python make_reel.py --sound voiceover --vo voiceover/vo_eleven.mp3

Ordering: clips are added in filename order. Prefix files with 01_, 02_, 03_...
to control the sequence.
"""

import argparse
import datetime
import math
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = os.path.dirname(os.path.abspath(__file__))
MEDIA_DIR = os.path.join(ROOT, "media")
VO_DIR = os.path.join(ROOT, "voiceover")
FINAL_DIR = os.path.join(ROOT, "final")
TMP_DIR = os.path.join(ROOT, "_tmp_build")

# --- Instagram Reel target format ---
TARGET_W = 1080
TARGET_H = 1920
FPS = 30

# Natural narration pace. ~150 words/minute is a comfortable spoken rate, so a
# reel's length caps how many words of voiceover/script actually fit.
WPM = 150


def word_budget(seconds, wpm=WPM):
    """How many words of narration comfortably fit in `seconds`."""
    return int(seconds * wpm / 60)


def count_words(text):
    return len(text.split())

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}


# --------------------------------------------------------------------------- #
# Tool discovery
# --------------------------------------------------------------------------- #
def _find(binary):
    """Locate ffmpeg/ffprobe: bundled tools/ first, then PATH, then sightTune."""
    local = os.path.join(ROOT, "tools", binary + ".exe")
    if os.path.exists(local):
        return local
    onpath = shutil.which(binary)
    if onpath:
        return onpath
    fallback = os.path.join(
        os.path.dirname(ROOT), "sightTune_video", "tools", binary + ".exe"
    )
    if os.path.exists(fallback):
        return fallback
    sys.exit(f"ERROR: could not find {binary}. Put {binary}.exe in ./tools/.")


FF = _find("ffmpeg")
FFPROBE = _find("ffprobe")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def run(args, label="", cwd=None):
    r = subprocess.run([FF, "-y", *args], capture_output=True, text=True, cwd=cwd)
    if r.returncode != 0:
        print(f"\nFFmpeg failed [{label}]:\n{r.stderr[-1500:]}", file=sys.stderr)
        sys.exit(1)


def has_audio(path):
    r = subprocess.run(
        [FFPROBE, "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=index",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    return bool(r.stdout.strip())


def duration_of(path):
    r = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def natural_key(name):
    """Sort so 2_x comes before 10_x."""
    return [int(t) if t.isdigit() else t.lower()
            for t in re.split(r"(\d+)", name)]


# --- Subtitles ---------------------------------------------------------- #
# Burned-in caption styling (libass). White text, thick black outline, no
# shadow, sat in the lower third above Instagram's UI. NOTE: SRT has no
# resolution header, so libass renders in a 384x288 space and scales up
# ~6.7x to 1920 tall — these numbers are chosen for that scaled space
# (Fontsize 16 -> ~107px; MarginV 55 -> ~365px off the bottom).
SUB_STYLE = ("Fontname=Arial,Fontsize=16,Bold=1,"
             "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
             "BorderStyle=1,Outline=3,Shadow=0,Alignment=2,MarginV=55")


def split_captions(text, max_words=6):
    """Break a script into short on-screen caption chunks."""
    caps, cur = [], []
    for w in text.split():
        cur.append(w)
        if len(cur) >= max_words or w.endswith((".", "!", "?", ":", ";")):
            caps.append(" ".join(cur))
            cur = []
    if cur:
        caps.append(" ".join(cur))
    return caps


def _srt_time(t):
    h, rem = divmod(int(t), 3600)
    m, s = divmod(rem, 60)
    ms = int(round((t - int(t)) * 1000))
    if ms == 1000:
        s, ms = s + 1, 0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(captions, total_dur, path):
    """Spread captions across total_dur, timed proportional to text length."""
    total_chars = sum(max(1, len(c)) for c in captions) or 1
    cum = 0
    blocks = []
    for i, c in enumerate(captions, 1):
        start = total_dur * cum / total_chars
        cum += max(1, len(c))
        end = total_dur * cum / total_chars
        blocks.append(f"{i}\n{_srt_time(start)} --> {_srt_time(end)}\n{c}\n")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(blocks))


# --- Timer overlay ------------------------------------------------------ #
# A running stopwatch burned over the whole reel, precise to 1/100 s. Built
# as a per-frame .ass file (rock-solid vs. drawtext expression escaping) with
# resolution in real pixels, so font size / margins are exact.
_TIMER_ALIGN = {"top": 8, "middle": 5, "bottom": 2}


def _ass_ts(t):
    """seconds -> ASS timestamp H:MM:SS.cc (centisecond precision)."""
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _fmt_timer(v, show_hours):
    cs = int(v * 100)  # floor, like a real stopwatch
    if show_hours:
        h, r = divmod(cs, 360000)
        m, r = divmod(r, 6000)
        s, c = divmod(r, 100)
        return f"{h}:{m:02d}:{s:02d}.{c:02d}"
    m, r = divmod(cs, 6000)
    s, c = divmod(r, 100)
    return f"{m:02d}:{s:02d}.{c:02d}"


def write_timer_ass(path, video_dur, target_seconds, fps=FPS,
                    fontsize=72, position="top", direction="down"):
    """One dialogue event per frame, precise to 1/100 s, spanning the whole reel.

    direction="down" (default): starts at target_seconds and counts DOWN to 0
        across the reel — e.g. "23 minutes" starts at 23:00.00 and hits 00:00.00
        exactly at the end, compressed into the reel's length.
    direction="up": counts UP from 0 to target_seconds instead.
    """
    show_hours = target_seconds >= 3600
    align = _TIMER_ALIGN.get(position, 8)
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {TARGET_W}\nPlayResY: {TARGET_H}\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, "
        "Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
        "MarginR, MarginV, Encoding\n"
        f"Style: Timer,Consolas,{fontsize},&H00FFFFFF,&H00000000,&H64000000,"
        f"1,0,0,0,100,100,0,0,1,4,1,{align},0,0,90,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
        "Effect, Text\n"
    )
    n = max(1, int(math.ceil(video_dur * fps)))
    lines = [header]
    for i in range(n):
        t0 = i / fps
        t1 = min((i + 1) / fps, video_dur)
        if t1 <= t0:
            continue
        frac = (t0 / video_dur) if video_dur > 0 else 0
        val = target_seconds * (1 - frac) if direction == "down" \
            else target_seconds * frac
        lines.append(f"Dialogue: 0,{_ass_ts(t0)},{_ass_ts(t1)},Timer,,0,0,0,,"
                     f"{_fmt_timer(val, show_hours)}\n")
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)


# --- Title overlay ------------------------------------------------------ #
_TITLE_ALIGN = {"top": 8, "middle": 5, "bottom": 2}


def write_title_ass(path, video_dur, text, seconds=3.0, fontsize=64,
                    position="top"):
    """A headline burned over the reel. Shows for `seconds` (0 = whole reel).

    Placed in the upper third by default so it clears bottom captions and the
    top-edge timer. Real-pixel resolution -> fontsize/margins are exact.
    """
    text = (text.strip().replace("{", "(").replace("}", ")")
            .replace("\n", "\\N"))
    align = _TITLE_ALIGN.get(position, 8)
    marginv = 0 if position == "middle" else 240
    end = (video_dur if (not seconds or seconds <= 0 or seconds >= video_dur)
           else seconds)
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\nWrapStyle: 0\n"
        f"PlayResX: {TARGET_W}\nPlayResY: {TARGET_H}\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, "
        "Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
        "MarginR, MarginV, Encoding\n"
        f"Style: Title,Arial,{fontsize},&H00FFFFFF,&H00000000,&H64000000,"
        f"1,0,0,0,100,100,0,0,1,5,1,{align},80,80,{marginv},1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
        "Effect, Text\n"
        f"Dialogue: 0,{_ass_ts(0)},{_ass_ts(end)},Title,,0,0,0,,{text}\n"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(header)


def parse_duration(s):
    """Accept '12.34', 'SS.cc', 'MM:SS.cc', or 'HH:MM:SS.cc' -> seconds."""
    s = str(s).strip()
    if ":" not in s:
        return float(s)
    parts = [float(p) for p in s.split(":")]
    total = 0.0
    for p in parts:
        total = total * 60 + p
    return total


def burn_subs(src, dst, sub_filename, style=None):
    """Burn a subtitle/timer file (in TMP_DIR) onto src -> dst, keeping audio."""
    filt = f"subtitles={sub_filename}"
    if style:
        filt += f":force_style='{style}'"
    audio_args = ["-c:a", "copy"] if has_audio(src) else ["-an"]
    # cwd=TMP_DIR so the filter gets a bare filename (avoids Windows drive-colon
    # escaping problems).
    run(["-i", os.path.abspath(src), "-vf", filt,
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
         *audio_args, os.path.abspath(dst)], "burn", cwd=TMP_DIR)


def gather_media():
    if not os.path.isdir(MEDIA_DIR):
        sys.exit(f"ERROR: media folder not found: {MEDIA_DIR}")
    files = []
    for name in sorted(os.listdir(MEDIA_DIR), key=natural_key):
        ext = os.path.splitext(name)[1].lower()
        if ext in IMAGE_EXT or ext in VIDEO_EXT:
            files.append(os.path.join(MEDIA_DIR, name))
    if not files:
        sys.exit(f"ERROR: no images or videos found in {MEDIA_DIR}. "
                 f"Drop your pictures/clips there and run again.")
    return files


# --- Length targeting --------------------------------------------------- #
# Reels have sweet-spot lengths. Rather than fix a per-photo time, the caller
# gives a TARGET total length; we derive how fast the stills flash to hit it.
# The model still decides video truncation (--max-clip-seconds) case by case.
MIN_STILL = 0.4   # fastest a photo flashes (frames still register)
MAX_STILL = 8.0   # longest a single photo holds before it drags

LENGTH_BANDS = {   # name -> (low, high) seconds; midpoint is the default target
    "max-reach": (7, 15),
    "sweet-spot": (15, 30),
    "deep": (30, 60),
    "long-form": (60, 1200),
}


def plan_pacing(media, target, max_clip=None,
                min_still=MIN_STILL, max_still=MAX_STILL):
    """Given a target total length, work out the still-flash seconds needed.

    Returns a dict: image_seconds (or None if no stills), projected total,
    counts, video_time, and human notes (e.g. clamping / need-to-truncate).
    """
    imgs = [f for f in media if os.path.splitext(f)[1].lower() in IMAGE_EXT]
    vids = [f for f in media if os.path.splitext(f)[1].lower() in VIDEO_EXT]
    video_time = 0.0
    for v in vids:
        d = duration_of(v)
        video_time += min(d, max_clip) if max_clip else d

    notes = []
    if imgs:
        want = (target - video_time) / len(imgs)
        image_seconds = max(min_still, min(max_still, want))
        if abs(image_seconds - want) > 0.02:
            if want < min_still:
                notes.append(f"too much media for {target:g}s even at the fastest "
                             f"flash ({min_still:g}s/photo) - either raise the target "
                             f"or truncate videos with --max-clip-seconds.")
            else:
                notes.append(f"not enough media for {target:g}s - photos held at the "
                             f"max {max_still:g}s each; add media or lower the target.")
        total = video_time + image_seconds * len(imgs)
    else:
        image_seconds = None
        total = video_time
        if not max_clip and video_time > target + 0.5:
            notes.append(f"videos alone run {video_time:.1f}s (> {target:g}s target) - "
                         f"set --max-clip-seconds to truncate them.")
    return {"image_seconds": image_seconds, "total": total,
            "n_img": len(imgs), "n_vid": len(vids),
            "video_time": video_time, "notes": notes}


# cover-and-crop to fill a 1080x1920 frame with no black bars
_COVER = (f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=increase,"
          f"crop={TARGET_W}:{TARGET_H},setsar=1,fps={FPS},format=yuv420p")


def normalize_image(src, dst, dur, ken_burns=True):
    if ken_burns:
        frames = int(dur * FPS)
        # gentle slow zoom-in (Ken Burns)
        vf = (
            f"scale={TARGET_W*2}:{TARGET_H*2}:force_original_aspect_ratio=increase,"
            f"crop={TARGET_W*2}:{TARGET_H*2},"
            f"zoompan=z='min(zoom+0.0006,1.12)':d={frames}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"s={TARGET_W}x{TARGET_H}:fps={FPS},setsar=1,format=yuv420p"
        )
    else:
        vf = _COVER
    run(["-loop", "1", "-i", src, "-t", f"{dur:.3f}", "-vf", vf,
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS), "-an", dst],
        os.path.basename(src))


def normalize_video(src, dst, max_dur):
    args = ["-i", src]
    d = duration_of(src)
    if max_dur and d > max_dur:
        args = ["-t", f"{max_dur:.3f}", *args]
    run([*args, "-vf", _COVER,
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS), "-an", dst],
        os.path.basename(src))


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="Build a 9:16 Instagram reel from ./media/")
    ap.add_argument("--sound", choices=["none", "voiceover"], default="none",
                    help="none = silent reel (add music on IG). "
                         "voiceover = mux the --vo audio file.")
    ap.add_argument("--vo", default=None,
                    help="Path to the voiceover audio file (when --sound voiceover). "
                         "If omitted, the first audio file in ./voiceover/ is used.")
    ap.add_argument("--target-seconds", default=None,
                    help="Target TOTAL reel length ('MM:SS' or seconds). When set, "
                         "the photo-flash speed is derived automatically to hit it "
                         "(overrides --image-seconds). Combine with --max-clip-seconds "
                         "to also truncate videos. Bands: max-reach 7-15, sweet-spot "
                         "15-30, deep 30-60, long-form 60-1200.")
    ap.add_argument("--image-seconds", type=float, default=3.0,
                    help="Seconds each still photo is shown (default 3.0). Ignored "
                         "when --target-seconds is given.")
    ap.add_argument("--max-clip-seconds", type=float, default=0.0,
                    help="Trim each source video to at most this many seconds "
                         "(0 = keep full length).")
    ap.add_argument("--no-ken-burns", action="store_true",
                    help="Disable the slow zoom on still photos.")
    ap.add_argument("--fit-audio", action="store_true",
                    help="With --sound voiceover: stretch the reel's last photo so "
                         "total video length matches the voiceover length.")
    ap.add_argument("--subtitles", choices=["none", "auto", "file"], default="none",
                    help="none = no captions. auto = generate evenly-timed captions "
                         "from the script text. file = burn a provided .srt.")
    ap.add_argument("--sub-script", default=None,
                    help="Text file the auto captions are built from "
                         "(default: prompts/script.txt).")
    ap.add_argument("--sub-file", default=None,
                    help="Path to a .srt file to burn in (with --subtitles file).")
    ap.add_argument("--title", default=None,
                    help="Headline text to overlay on the reel.")
    ap.add_argument("--title-seconds", type=float, default=3.0,
                    help="How long the title shows (default 3.0; 0 = whole reel).")
    ap.add_argument("--title-position", choices=["top", "middle", "bottom"],
                    default="top", help="Where the title sits (default top).")
    ap.add_argument("--title-fontsize", type=int, default=64,
                    help="Title font size in px (default 64).")
    ap.add_argument("--timer", action="store_true",
                    help="Burn a running timer (1/100 s) over the whole reel.")
    ap.add_argument("--timer-seconds", default=None,
                    help="How long it took to create this (the timer's starting "
                         "value; 'MM:SS.cc', 'HH:MM:SS.cc', or plain seconds). "
                         "By default the timer counts DOWN from here to 00:00.00 "
                         "across the reel. Default value: the reel's own length.")
    ap.add_argument("--timer-direction", choices=["down", "up"], default="down",
                    help="down (default): start at --timer-seconds, count to 0. "
                         "up: start at 0, count up to --timer-seconds.")
    ap.add_argument("--timer-position", choices=["top", "middle", "bottom"],
                    default="top", help="Where the timer sits (default top).")
    ap.add_argument("--timer-fontsize", type=int, default=72,
                    help="Timer font size in px (default 72).")
    args = ap.parse_args()
    t_start = time.time()

    os.makedirs(FINAL_DIR, exist_ok=True)
    if os.path.isdir(TMP_DIR):
        shutil.rmtree(TMP_DIR)
    os.makedirs(TMP_DIR)

    media = gather_media()
    print(f"Found {len(media)} media file(s):")
    for m in media:
        print("   ", os.path.basename(m))

    # Decide photo-flash speed. If a target length is given, derive it; else use
    # the fixed --image-seconds.
    max_clip = args.max_clip_seconds if args.max_clip_seconds else None
    image_seconds = args.image_seconds
    if args.target_seconds is not None:
        target = parse_duration(args.target_seconds)
        plan = plan_pacing(media, target, max_clip=max_clip)
        if plan["image_seconds"] is not None:
            image_seconds = plan["image_seconds"]
            print(f"\nTarget {target:g}s -> photos flash at {image_seconds:.2f}s each "
                  f"({plan['n_img']} photos, {plan['n_vid']} clips = "
                  f"{plan['video_time']:.1f}s of video).")
        else:
            print(f"\nTarget {target:g}s -> no photos; length set by the video clips "
                  f"({plan['video_time']:.1f}s).")
        for note in plan["notes"]:
            print(f"  NOTE: {note}")

    # 1) Normalize every item to a uniform 1080x1920 / 30fps segment
    segments = []
    for i, src in enumerate(media):
        dst = os.path.join(TMP_DIR, f"seg_{i:03d}.mp4")
        ext = os.path.splitext(src)[1].lower()
        if ext in IMAGE_EXT:
            normalize_image(src, dst, image_seconds,
                            ken_burns=not args.no_ken_burns)
        else:
            normalize_video(src, dst, max_clip)
        segments.append(dst)

    # 2) Concatenate
    concat_txt = os.path.join(TMP_DIR, "concat.txt")
    with open(concat_txt, "w", encoding="utf-8") as f:
        for s in segments:
            f.write(f"file '{s.replace(os.sep, '/')}'\n")
    video_only = os.path.join(TMP_DIR, "video_only.mp4")
    run(["-f", "concat", "-safe", "0", "-i", concat_txt,
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS), "-an",
         video_only], "concat")

    vid_dur = duration_of(video_only)
    budget = word_budget(vid_dur)
    print(f"\nStitched video length: {vid_dur:.1f}s")
    print(f"Script budget: about {budget} words of voiceover fit this reel "
          f"(~{WPM} words/min).")
    script_txt = os.path.join(ROOT, "prompts", "script.txt")
    if os.path.exists(script_txt):
        have = count_words(Path(script_txt).read_text(encoding="utf-8"))
        if have > budget * 1.1:
            print(f"  NOTE: prompts/script.txt has {have} words - longer than the "
                  f"~{budget}-word budget. Summarize it (or use --fit-audio) or the "
                  f"end may be cut off. Run script_fit.py for details.")
        else:
            print(f"  prompts/script.txt has {have} words - fits.")

    # 3) Audio -> produce base.mp4 (video, with voiceover if requested)
    base = os.path.join(TMP_DIR, "base.mp4")
    if args.sound == "none":
        shutil.copyfile(video_only, base)
    else:
        vo = args.vo
        if not vo:
            cand = [os.path.join(VO_DIR, n) for n in sorted(os.listdir(VO_DIR))
                    if os.path.splitext(n)[1].lower() in
                    {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}]
            if not cand:
                sys.exit("ERROR: --sound voiceover but no --vo given and "
                         "./voiceover/ has no audio file.")
            vo = cand[0]
        if not os.path.exists(vo):
            sys.exit(f"ERROR: voiceover file not found: {vo}")
        vo_dur = duration_of(vo)
        print(f"Voiceover: {os.path.basename(vo)} ({vo_dur:.1f}s)")
        if vo_dur > vid_dur + 0.3 and not args.fit_audio:
            print(f"  WARNING: the voiceover ({vo_dur:.1f}s) is longer than the "
                  f"visuals ({vid_dur:.1f}s). The end will be cut off. Either "
                  f"shorten the script (~{budget} words) or re-run with --fit-audio "
                  f"to stretch the visuals to match.")

        if args.fit_audio:
            # Re-render the reel so its length equals the VO length by
            # holding the final photo/clip. Simple approach: pad video by
            # freezing last frame via tpad, then trim to VO length.
            padded = os.path.join(TMP_DIR, "video_fit.mp4")
            run(["-i", video_only,
                 "-vf", f"tpad=stop_mode=clone:stop_duration={max(0, vo_dur - vid_dur):.3f}",
                 "-t", f"{vo_dur:.3f}",
                 "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS), "-an",
                 padded], "fit")
            video_only = padded
            vid_dur = vo_dur

        # Mux: keep the video length; pad/trim audio to match it.
        run(["-i", video_only, "-i", vo,
             "-filter_complex",
             f"[1:a]aresample=48000,apad,atrim=0:{vid_dur:.3f},"
             f"asetpts=PTS-STARTPTS[a]",
             "-map", "0:v:0", "-map", "[a]",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
             "-shortest", base], "mux")

    base_dur = duration_of(base)
    current = base  # each overlay pass consumes `current` and produces the next

    # 4) Captions (optional burn-in)
    if args.subtitles != "none":
        srt_path = os.path.join(TMP_DIR, "subs.srt")
        if args.subtitles == "file":
            if not args.sub_file or not os.path.exists(args.sub_file):
                sys.exit("ERROR: --subtitles file requires an existing --sub-file <path.srt>.")
            shutil.copyfile(args.sub_file, srt_path)
        else:  # auto
            src = args.sub_script or os.path.join(ROOT, "prompts", "script.txt")
            if not os.path.exists(src):
                sys.exit(f"ERROR: --subtitles auto needs script text. "
                         f"Provide --sub-script <file> or create prompts/script.txt "
                         f"(not found: {src}).")
            captions = split_captions(Path(src).read_text(encoding="utf-8"))
            if not captions:
                sys.exit("ERROR: subtitle script is empty.")
            write_srt(captions, base_dur, srt_path)
            print(f"Captions: {len(captions)} lines over {base_dur:.1f}s")
        withsubs = os.path.join(TMP_DIR, "withsubs.mp4")
        burn_subs(current, withsubs, "subs.srt", style=SUB_STYLE)
        current = withsubs

    # 5) Title overlay (optional burn-in)
    if args.title:
        title_ass = os.path.join(TMP_DIR, "title.ass")
        write_title_ass(title_ass, base_dur, args.title,
                        seconds=args.title_seconds,
                        fontsize=args.title_fontsize,
                        position=args.title_position)
        withtitle = os.path.join(TMP_DIR, "withtitle.mp4")
        burn_subs(current, withtitle, "title.ass")
        current = withtitle
        span = ("whole reel" if args.title_seconds <= 0
                else f"first {min(args.title_seconds, base_dur):.1f}s")
        print(f"Title: \"{args.title}\" ({args.title_position}, {span}).")

    # 6) Timer overlay (optional burn-in)
    if args.timer:
        target = (parse_duration(args.timer_seconds)
                  if args.timer_seconds is not None else base_dur)
        ass_path = os.path.join(TMP_DIR, "timer.ass")
        write_timer_ass(ass_path, base_dur, target,
                        fps=FPS, fontsize=args.timer_fontsize,
                        position=args.timer_position,
                        direction=args.timer_direction)
        withtimer = os.path.join(TMP_DIR, "withtimer.mp4")
        burn_subs(current, withtimer, "timer.ass")
        current = withtimer
        shown = _fmt_timer(target, target >= 3600)
        span = (f"{shown} -> 00:00.00" if args.timer_direction == "down"
                else f"00:00.00 -> {shown}")
        print(f"Timer: {span} across the {base_dur:.1f}s reel ({args.timer_position}).")

    # 7) Finalize
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    final_path = os.path.join(FINAL_DIR, f"reel_{stamp}.mp4")
    shutil.copyfile(current, final_path)

    shutil.rmtree(TMP_DIR, ignore_errors=True)
    elapsed = time.time() - t_start
    print("\n" + "=" * 60)
    print("REEL READY")
    print("=" * 60)
    print(f"File:     {final_path}")
    print(f"Length:   {duration_of(final_path):.1f}s   Format: {TARGET_W}x{TARGET_H} (9:16)")
    print(f"Built in: {elapsed:.2f}s")
    print("Upload this to Instagram as a Reel.")
    if args.sound == "none":
        print("Tip: add music on Instagram's 'Add audio' screen during upload.")
    print("=" * 60)


if __name__ == "__main__":
    main()
