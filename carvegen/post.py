"""Post-processing: conform each Kling segment to the target 9:16 frame and
stitch the segments into one reel with crossfades and audio.

Audio policy (matches "recreate the sounds, no music"):
  - output.music set        -> use that track as the bed (trimmed to length)
  - keep_source_audio True   -> keep each segment's own generated foley,
                               crossfaded in sync with the video
  - otherwise                -> silent

Kling clips for 9:16 already come near 1080x1920, so this is a light
cover-crop + fps conform, not an aspect hack.
"""

import logging
import os
import shutil
import subprocess
import sys
import tempfile

log = logging.getLogger(__name__)


def _find(binary):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    local = os.path.join(root, "tools", binary + ".exe")
    if os.path.exists(local):
        return local
    onpath = shutil.which(binary)
    if onpath:
        return onpath
    raise SystemExit(f"ERROR: could not find {binary}; put {binary}.exe in ./tools/.")


FF = _find("ffmpeg")
FFPROBE = _find("ffprobe")
SAMPLE_RATE = 44100


def _run(args, label=""):
    r = subprocess.run([FF, "-y", *args], capture_output=True, text=True)
    if r.returncode != 0:
        log.error("ffmpeg failed [%s]:\n%s", label, r.stderr[-1500:])
        sys.exit(1)


def _has_audio(path):
    r = subprocess.run(
        [FFPROBE, "-v", "error", "-select_streams", "a", "-show_entries",
         "stream=index", "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True)
    return bool(r.stdout.strip())


def _cover(w, h):
    return (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h},setsar=1")


def _conform_video(src, dst, seconds, w, h, fps):
    _run(["-stream_loop", "-1", "-i", src, "-t", f"{seconds:.3f}",
          "-vf", f"{_cover(w, h)},fps={fps},format=yuv420p",
          "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", dst], f"conform {src}")


def _conform_audio(src, dst, seconds, keep):
    if keep and _has_audio(src):
        _run(["-stream_loop", "-1", "-i", src, "-t", f"{seconds:.3f}",
              "-vn", "-ac", "2", "-ar", str(SAMPLE_RATE), dst], "audio")
    else:
        _run(["-f", "lavfi", "-i", f"anullsrc=r={SAMPLE_RATE}:cl=stereo",
              "-t", f"{seconds:.3f}", dst], "silence")


def _xfade_chain(n, durs, cf):
    if n == 1:
        return None, "0:v", durs[0]
    parts, run_dur, prev = [], durs[0], "[0:v]"
    for i in range(1, n):
        off = max(0.0, run_dur - cf)
        out = f"v{i}" if i < n - 1 else "vout"
        parts.append(f"{prev}[{i}:v]xfade=transition=fade:duration={cf:.3f}:"
                     f"offset={off:.3f}[{out}]")
        run_dur += durs[i] - cf
        prev = f"[{out}]"
    return ";".join(parts), "vout", run_dur


def _acrossfade_chain(n, cf):
    if n == 1:
        return None, "0:a"
    parts, prev = [], "[0:a]"
    for i in range(1, n):
        out = f"a{i}" if i < n - 1 else "aout"
        parts.append(f"{prev}[{i}:a]acrossfade=d={cf:.3f}[{out}]")
        prev = f"[{out}]"
    return ";".join(parts), "aout"


def stitch(segment_files, seconds_list, out_path, *, width, height, fps,
           crossfade, keep_source_audio, music=None):
    """segment_files/seconds_list are parallel lists (in order). Writes the
    finished reel to out_path and returns it."""
    n = len(segment_files)
    cf = crossfade if n > 1 else 0.0
    # pad each rendered clip by one crossfade so the chain has overlap material
    render_secs = [s + (cf if n > 1 else 0) for s in seconds_list]
    total = sum(seconds_list)

    with tempfile.TemporaryDirectory(prefix="carvegen_") as tmp:
        vclips, aclips = [], []
        for i, (src, secs) in enumerate(zip(segment_files, render_secs)):
            v = os.path.join(tmp, f"v{i:02d}.mp4")
            _conform_video(src, v, secs, width, height, fps)
            vclips.append(v)
            if not music:
                a = os.path.join(tmp, f"a{i:02d}.wav")
                _conform_audio(src, a, secs, keep_source_audio)
                aclips.append(a)

        vf, vlabel, _ = _xfade_chain(n, render_secs, cf)
        video_only = os.path.join(tmp, "video.mp4")
        args = []
        for v in vclips:
            args += ["-i", v]
        if vf:
            args += ["-filter_complex", vf, "-map", f"[{vlabel}]"]
        else:
            args += ["-map", "0:v"]
        args += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(fps), video_only]
        _run(args, "video stitch")

        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        if music:
            _run(["-i", video_only, "-i", music, "-map", "0:v", "-map", "1:a:0",
                  "-t", f"{total:.3f}", "-c:v", "copy", "-c:a", "aac",
                  "-b:a", "192k", "-shortest", out_path], "mux music")
        else:
            af, alabel = _acrossfade_chain(n, cf)
            audio_only = os.path.join(tmp, "audio.wav")
            aargs = []
            for a in aclips:
                aargs += ["-i", a]
            if af:
                aargs += ["-filter_complex", af, "-map", f"[{alabel}]"]
            else:
                aargs += ["-map", "0:a"]
            aargs += [audio_only]
            _run(aargs, "audio stitch")
            _run(["-i", video_only, "-i", audio_only, "-map", "0:v", "-map", "1:a",
                  "-t", f"{total:.3f}", "-c:v", "copy", "-c:a", "aac",
                  "-b:a", "192k", out_path], "mux")
    log.info("stitched %d segment(s) -> %s (%.1fs)", n, out_path, total)
    return out_path
