#!/usr/bin/env python3
"""compose_reel.py — layer B-roll panels, infographic cards, and hook chips
OVER a full-screen talking-head video (the "A-roll"), keeping its speech.

This is the "creator format" builder: where make_reel.py CONCATENATES media
one clip at a time (and drops all source audio), compose_reel.py COMPOSITES —
the A-roll runs underneath for the whole reel and timed overlays slide in and
out on top of it, like the picture-in-picture explainers that dominate
Reels/TikTok. The A-roll can be a phone selfie video or a HeyGen avatar clip
generated from a script.

Usage:
    python compose_reel.py prompts/timeline.json
    python compose_reel.py prompts/timeline.json --srt prompts/captions.srt

The timeline is JSON:

{
  "aroll": "aroll/take1.mp4",          // full-screen base; audio kept
  "fit": false,                        // true = letterbox instead of crop
  "voice": null,                       // optional: audio file that REPLACES
                                       //   the a-roll's own audio track
  "music": {                           // optional bed, auto-ducked under voice
    "file": "music/bed.mp3", "gain_db": -18, "duck": true
  },
  "loudnorm": true,                    // normalize voice to reel loudness
  "overlays": [
    // A hook chip rendered on the fly by make_chip.py:
    { "type": "chip", "text": "🚨 Nobody is Talking About This",
      "start": 0.4, "end": 4.5, "pos": "upper", "fontsize": 58 },

    // An image panel (e.g. a make_cards.py card), slid in from the top.
    // width/height are FRACTIONS of the 1080x1920 frame. Give both to
    // cover-crop into that box (full-width band, like B-roll on top of a
    // talking head); give one to keep the image's own aspect.
    { "type": "image", "file": "cards/card1.png",
      "start": 8, "end": 16, "pos": "top", "width": 1.0, "height": 0.42,
      "slide": "top", "fade": 0.3 },

    // A muted video clip as a panel ("from" = source offset in seconds):
    { "type": "video", "file": "broll/smoke.mp4", "from": 3,
      "start": 16, "end": 22, "pos": "top", "width": 1.0, "height": 0.38 }
  ]
}

Overlay fields:
  start/end   when it's on screen (seconds; 'MM:SS' also accepted)
  pos         top | upper | center | lower | bottom  (or x/y: 0..1 fractions,
              0 = left/top edge, 1 = right/bottom edge, 0.5 = centered)
  width/height  size as a fraction of the frame (see above)
  fade        fade in/out seconds (default 0.25; 0 = hard cut)
  slide       top | bottom | left | right — eases in from that edge
  from        (video only) seconds into the source file to start

Output: final/composed_<datetime>.mp4 (1080x1920, 30fps). Never overwrites.
"""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import time

import make_reel as mr           # ffmpeg discovery + shared helpers
from make_chip import render_chip

ROOT = os.path.dirname(os.path.abspath(__file__))
FINAL_DIR = os.path.join(ROOT, "final")
TMP_DIR = os.path.join(ROOT, "_tmp_compose")

# Chip text can contain emoji; Windows consoles often default to cp1252.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")
    except AttributeError:
        pass

W, H, FPS = mr.TARGET_W, mr.TARGET_H, mr.FPS

POS = {  # preset -> (x-fraction, y-fraction) of the leftover space
    "top": (0.5, 0.0), "upper": (0.5, 0.18), "center": (0.5, 0.5),
    "lower": (0.5, 0.78), "bottom": (0.5, 1.0),
}
SLIDE_PX = 150      # how far a slide-in travels
SLIDE_SECS = 0.45   # how long the slide takes (ease-out)

IMAGE_EXT = mr.IMAGE_EXT
VIDEO_EXT = mr.VIDEO_EXT


def die(msg):
    sys.exit(f"ERROR: {msg}")


def resolve(path):
    """Timeline paths may be relative to the repo root."""
    if not path:
        return path
    return path if os.path.isabs(path) else os.path.join(ROOT, path)


def ffmpeg(args, label, cwd=None):
    r = subprocess.run([mr.FF, "-y", *args], capture_output=True, text=True,
                       cwd=cwd)
    if r.returncode != 0:
        print(f"\nFFmpeg failed [{label}]:\n{r.stderr[-2500:]}", file=sys.stderr)
        sys.exit(1)


# --------------------------------------------------------------------------- #
# Filter-graph construction
# --------------------------------------------------------------------------- #
def scale_expr(ov):
    """The scale/crop chain that sizes an overlay before compositing."""
    wf, hf = ov.get("width"), ov.get("height")
    if wf and hf:  # cover-crop into the box (full-width band etc.)
        ow, oh = round(W * wf / 2) * 2, round(H * hf / 2) * 2
        return (f"scale={ow}:{oh}:force_original_aspect_ratio=increase,"
                f"crop={ow}:{oh}")
    if wf:
        return f"scale={round(W * wf / 2) * 2}:-2"
    if hf:
        return f"scale=-2:{round(H * hf / 2) * 2}"
    return "scale=iw:ih"  # natural size (chips)


def pos_fractions(ov):
    if "pos" in ov:
        if ov["pos"] not in POS:
            die(f"unknown pos '{ov['pos']}' (use {'/'.join(POS)} or x/y).")
        xf, yf = POS[ov["pos"]]
    else:
        xf, yf = 0.5, 0.5
    xf = ov.get("x", xf)
    yf = ov.get("y", yf)
    return float(xf), float(yf)


def overlay_xy(ov, start):
    """x/y expressions for the overlay filter, including the slide-in ease."""
    xf, yf = pos_fractions(ov)
    x = f"(main_w-overlay_w)*{xf:.4f}"
    y = f"(main_h-overlay_h)*{yf:.4f}"
    slide = ov.get("slide")
    if slide:
        # progress 0->1 over SLIDE_SECS with an ease-out curve
        p = f"min(max((t-{start:.3f})/{SLIDE_SECS},0),1)"
        off = f"{SLIDE_PX}*pow(1-{p},2)"
        if slide == "top":
            y = f"{y}-{off}"
        elif slide == "bottom":
            y = f"{y}+{off}"
        elif slide == "left":
            x = f"{x}-{off}"
        elif slide == "right":
            x = f"{x}+{off}"
        else:
            die(f"unknown slide '{slide}' (top/bottom/left/right).")
    return x, y


def build(timeline, srt=None, out_name=None):
    t0 = time.time()
    os.makedirs(FINAL_DIR, exist_ok=True)
    if os.path.isdir(TMP_DIR):
        shutil.rmtree(TMP_DIR)
    os.makedirs(TMP_DIR)

    aroll = resolve(timeline.get("aroll"))
    if not aroll or not os.path.exists(aroll):
        die(f"timeline needs an existing \"aroll\" video (got: {aroll}).")
    dur = mr.duration_of(aroll)
    if dur <= 0:
        die(f"could not read duration of {aroll}.")
    print(f"A-roll: {os.path.basename(aroll)}  ({dur:.1f}s)")

    # ---- inputs & video filter graph ---------------------------------- #
    inputs = ["-i", aroll]
    n_in = 1
    base = mr._FIT if timeline.get("fit") else mr._COVER
    chains = [f"[0:v]{base}[v0]"]
    prev = "v0"
    schedule = []

    for k, ov in enumerate(timeline.get("overlays", [])):
        start = mr.parse_duration(ov.get("start", 0))
        end = min(mr.parse_duration(ov.get("end", dur)), dur)
        if end <= start:
            print(f"  skipping overlay {k + 1}: window {start}-{end}s is "
                  f"empty (reel is {dur:.1f}s).")
            continue
        length = end - start
        fade = float(ov.get("fade", 0.25))
        fade = min(fade, length / 2)
        typ = ov.get("type") or (
            "chip" if "text" in ov else
            "image" if os.path.splitext(ov.get("file", ""))[1].lower()
            in IMAGE_EXT else "video")

        if typ == "chip":
            png = os.path.join(TMP_DIR, f"chip_{k}.png")
            render_chip(ov["text"], fontsize=int(ov.get("fontsize", 58)),
                        style=ov.get("style", "dark")).save(png, "PNG")
            src, is_image = png, True
            label = f'chip "{ov["text"][:40]}"'
        else:
            src = resolve(ov.get("file"))
            if not src or not os.path.exists(src):
                die(f"overlay {k + 1}: file not found: {src}")
            is_image = typ == "image"
            label = f"{typ} {os.path.basename(src)}"

        if is_image:
            inputs += ["-loop", "1", "-t", f"{length:.3f}", "-i", src]
            fmt = "format=rgba"
        else:
            seek = float(ov.get("from", 0))
            inputs += ["-ss", f"{seek:.3f}", "-t", f"{length:.3f}", "-i", src]
            fmt = f"fps={FPS},format=yuva420p"

        fades = ""
        if fade > 0:
            fades = (f",fade=t=in:st=0:d={fade:.3f}:alpha=1"
                     f",fade=t=out:st={length - fade:.3f}:d={fade:.3f}:alpha=1")
        chains.append(
            f"[{n_in}:v]{scale_expr(ov)},{fmt}{fades},"
            f"setpts=PTS-STARTPTS+{start:.3f}/TB[ov{k}]")

        x, y = overlay_xy(ov, start)
        chains.append(
            f"[{prev}][ov{k}]overlay=x='{x}':y='{y}'"
            f":enable='between(t,{start:.3f},{end:.3f})'[v{k + 1}]")
        prev = f"v{k + 1}"
        n_in += 1
        schedule.append((start, end, label, ov.get("pos", "x/y")))

    # ---- audio graph --------------------------------------------------- #
    voice_src = None
    if timeline.get("voice"):
        vpath = resolve(timeline["voice"])
        if not os.path.exists(vpath):
            die(f"voice file not found: {vpath}")
        inputs += ["-i", vpath]
        voice_src = f"{n_in}:a"
        n_in += 1
        print(f"Voice:  {os.path.basename(vpath)} (replaces a-roll audio)")
    elif mr.has_audio(aroll):
        voice_src = "0:a"

    music = timeline.get("music")
    music_src = None
    if music and music.get("file"):
        mpath = resolve(music["file"])
        if not os.path.exists(mpath):
            die(f"music file not found: {mpath}")
        inputs += ["-stream_loop", "-1", "-i", mpath]
        music_src = f"{n_in}:a"
        n_in += 1

    audio_maps = []
    if voice_src:
        vf = "loudnorm=I=-16:TP=-1.5:LRA=11" \
            if timeline.get("loudnorm", True) else "anull"
        chains.append(f"[{voice_src}]{vf},aresample=48000[voice]")
        if music_src:
            gain = float(music.get("gain_db", -18))
            chains.append(f"[{music_src}]volume={gain}dB,"
                          f"atrim=0:{dur:.3f},aresample=48000[mus]")
            if music.get("duck", True):
                chains.append("[voice]asplit=2[vo1][vo2]")
                chains.append("[mus][vo2]sidechaincompress=threshold=0.02:"
                              "ratio=8:attack=20:release=500[musd]")
                chains.append("[vo1][musd]amix=inputs=2:duration=first:"
                              "normalize=0[aout]")
            else:
                chains.append("[voice][mus]amix=inputs=2:duration=first:"
                              "normalize=0[aout]")
        else:
            chains.append("[voice]anull[aout]")
        audio_maps = ["-map", "[aout]", "-c:a", "aac", "-b:a", "256k",
                      "-ar", "48000"]
    elif music_src:
        gain = float(music.get("gain_db", -18))
        chains.append(f"[{music_src}]volume={gain}dB,atrim=0:{dur:.3f},"
                      f"aresample=48000[aout]")
        audio_maps = ["-map", "[aout]", "-c:a", "aac", "-b:a", "256k",
                      "-ar", "48000"]
    else:
        audio_maps = ["-an"]
        print("No audio track (a-roll is silent, no voice/music given).")

    # ---- render --------------------------------------------------------- #
    print(f"\nOverlay schedule ({len(schedule)}):")
    for s, e, lab, pos in schedule:
        print(f"  {s:7.2f}s - {e:7.2f}s  {lab}  ({pos})")

    composed = os.path.join(TMP_DIR, "composed.mp4")
    ffmpeg([*inputs, "-filter_complex", ";".join(chains),
            "-map", f"[{prev}]", *audio_maps,
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-t", f"{dur:.3f}", "-movflags", "+faststart", composed],
           "compose")
    current = composed

    # ---- optional caption burn (same style as make_reel) ---------------- #
    if srt:
        if not os.path.exists(srt):
            die(f"--srt file not found: {srt}")
        shutil.copyfile(srt, os.path.join(TMP_DIR, "subs.srt"))
        withsubs = os.path.join(TMP_DIR, "withsubs.mp4")
        audio_args = ["-c:a", "copy"] if mr.has_audio(current) else ["-an"]
        # cwd=TMP_DIR so the filter gets a bare filename (avoids Windows
        # drive-colon escaping problems), same trick as make_reel.burn_subs.
        ffmpeg(["-i", os.path.abspath(current), "-vf",
                f"subtitles=subs.srt:force_style='{mr.SUB_STYLE}'",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
                *audio_args, os.path.abspath(withsubs)], "captions",
               cwd=TMP_DIR)
        current = withsubs
        print("Captions burned in.")

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    final_path = os.path.join(
        FINAL_DIR, out_name or f"composed_{stamp}.mp4")
    shutil.copyfile(current, final_path)
    shutil.rmtree(TMP_DIR, ignore_errors=True)

    print("\n" + "=" * 60)
    print("COMPOSED REEL READY")
    print("=" * 60)
    print(f"File:     {final_path}")
    print(f"Length:   {mr.duration_of(final_path):.1f}s   "
          f"Format: {W}x{H} (9:16)")
    print(f"Built in: {time.time() - t0:.2f}s")
    print("=" * 60)
    return final_path


def main():
    ap = argparse.ArgumentParser(
        description="Composite overlays over a talking-head A-roll.")
    ap.add_argument("timeline", help="Path to the timeline .json file.")
    ap.add_argument("--srt", default=None,
                    help="Burn this .srt caption file over the composite.")
    ap.add_argument("--out", default=None,
                    help="Output filename inside final/ (default "
                         "composed_<datetime>.mp4).")
    args = ap.parse_args()

    tl_path = resolve(args.timeline)
    if not os.path.exists(tl_path):
        die(f"timeline not found: {tl_path}")
    try:
        timeline = json.loads(open(tl_path, encoding="utf-8").read())
    except json.JSONDecodeError as e:
        die(f"timeline is not valid JSON: {e}")
    build(timeline, srt=resolve(args.srt) if args.srt else None,
          out_name=args.out)


if __name__ == "__main__":
    main()
