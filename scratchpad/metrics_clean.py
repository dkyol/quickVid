"""One consistent method applied to BOTH videos.

Cuts are found the same way in each (ffmpeg scene detection), not assumed
from the N largest diffs — that shortcut discarded in-shot spikes as if they
were cuts and flattered whichever video had the worst in-shot behaviour.
"""
import subprocess, re, os
import numpy as np

os.chdir(r"C:\Users\DKYLE\Desktop\scripts\quickVid")
FF = "./tools/ffmpeg.exe"
REF = r"C:\Users\DKYLE\Downloads\ScreenRecording_07-25-2026 19-01-22_1.MP4"
MINE = r"wolf_watermelon\final\wolf_watermelon_v7.mp4"


def cuts(path, thresh=0.15):
    r = subprocess.run([FF, "-i", path, "-filter:v",
                        f"select='gt(scene,{thresh})',showinfo", "-f", "null", "-"],
                       capture_output=True, text=True)
    return [float(m) for m in re.findall(r"pts_time:([0-9.]+)", r.stderr)]


def frames(path, fps=15, w=96, h=170):
    r = subprocess.run([FF, "-v", "error", "-i", path, "-vf",
                        f"fps={fps},scale={w}:{h},format=gray",
                        "-f", "rawvideo", "-"], capture_output=True)
    a = np.frombuffer(r.stdout, dtype=np.uint8)
    n = len(a) // (w * h)
    return a[:n * w * h].reshape(n, h, w).astype(float), fps


def measure(path, label):
    a, fps = frames(path)
    d = np.abs(np.diff(a, axis=0)).mean(axis=(1, 2))
    cb = [int(c * fps) for c in cuts(path)]
    is_cut = np.zeros(len(d), bool)
    for b in cb:
        for i in (b - 1, b):
            if 0 <= i < len(d):
                is_cut[i] = True
    cutvals = d[is_cut]
    inshot = d[~is_cut]
    print(f"{label:26s} cuts={len(cb):2d}  "
          f"in-shot mean={inshot.mean():5.2f}  p95={np.percentile(inshot,95):6.2f}  "
          f"| cut mean={cutvals.mean():5.1f}  max={cutvals.max():5.1f}")


measure(REF, "REFERENCE")
measure(MINE, "MINE (v7)")
