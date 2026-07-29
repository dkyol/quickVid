"""Recut v6 with smaller framing deltas + rhythm variation, then MEASURE the
cut jumps so the change is verified rather than assumed.

Framing delta is reduced by punching in on the WIDE shots (the macros are
already tight), so consecutive shots share more visual mass across each cut.
Rhythm gets one deliberate flash cut, matching the reference's 0.25s shot.
"""
import subprocess, sys, os
import numpy as np

os.chdir(r"C:\Users\DKYLE\Desktop\scripts\quickVid")
M = "wolf_watermelon/media"
OUT = sys.argv[1] if len(sys.argv) > 1 else "wolf_watermelon/final/v6_recut.mp4"

# name, start, dur, punch-in zoom (1.0 = full frame)
# Rhythm mirrors the reference: a fast burst early (it cuts 0.83 / 0.25 / 0.67)
# then longer shots. Putting the unavoidable wide->macro jump inside a FLASH
# means the discontinuity is over before the eye resolves it — the standard
# way an edit absorbs a hard scale change.
PLAN = [
    # shot 1 starts later so pale carved rind is already on screen when we cut
    # to the all-pale macro — a content match, not just a scale match
    ("veo_01_first_cuts",  2.6, 1.8, 1.45),
    ("veo_02_ear_macro",   1.6, 0.45, 1.00),   # flash
    ("veo_03_upper_face",  1.6, 0.95, 1.40),
    ("veo_04_eye_macro",   3.9, 0.35, 1.00),   # flash
    # 05: the v8 bounded-i2v replacement. The old veo_05_muzzle removed HALF
    # THE FACE in one implausible sweep at 2.3-2.9s; this clip holds the
    # carved/drawn boundary for the full 8s (validated 2026-07-28).
    ("veo_05_midface",     1.5, 1.6, 1.40),
    ("veo_06_nose_macro",  3.6, 0.9, 1.00),   # take1: window on the clean curl
    # 07_border is DROPPED, not trimmed. Its wolf has no leaf border, a wider
    # face and radial fur — a different design from every other shot, at ANY
    # timestamp, so no window saves it. Regenerate as bounded i2v (07_ruff).
    #
    # 08 is SPLIT INTO TWO CUTS from one clip. The middle of that clip (3.5-6s)
    # is where Veo carves the NOSE off, then the nose reappears intact at the
    # next shot — the artefact that reads as magic. Taking an early window
    # (knife at the closed mouth) and a late one (mouth open, red, nose intact)
    # and cutting between them puts the excavation ACROSS the cut, which is how
    # the reference implies removal, and never shows the damage.
    ("veo_08_mouth",       0.6, 1.2, 1.45),   # approach: closed mouth, nose OK
    ("veo_08_mouth",       6.5, 1.5, 1.45),   # reveal: open red mouth, nose OK
    ("veo_09_hero",        0.5, 1.4, 1.30),
]

# Ported from the 07-27 Grok/hybrid reel, which reads better in secs 3-8.
# Measured cause was NOT contrast (ours is already higher) but saturation —
# theirs 40 vs our 26 on wides — plus FRAMING, hence the heavy punch above:
# their carving fills ~90% of frame, ours filled ~55% with grey and hands.
GRADE = "eq=saturation=1.45,unsharp=5:5:0.5"

args = ["./tools/ffmpeg.exe", "-y", "-loglevel", "error"]
for name, ss, t, _ in PLAN:
    args += ["-ss", str(ss), "-t", str(t), "-i", f"{M}/{name}.mp4"]

fc = []
for i, (_, _, _, z) in enumerate(PLAN):
    if z > 1.001:
        crop = (f"crop=iw/{z}:ih/{z}:(iw-iw/{z})/2:(ih-ih/{z})/2,"
                f"scale=1080:1920:flags=lanczos")
    else:
        crop = "scale=1080:1920"
    fc.append(f"[{i}:v]{crop},{GRADE},fps=30,setsar=1[v{i}]")
streams = "".join(f"[v{i}][{i}:a]" for i in range(len(PLAN)))
fc.append(f"{streams}concat=n={len(PLAN)}:v=1:a=1[v][a]")

args += ["-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]",
         "-c:v", "libx264", "-crf", "16", "-preset", "medium",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", OUT]
r = subprocess.run(args, capture_output=True, text=True)
if r.returncode:
    sys.exit("ffmpeg failed:\n" + r.stderr[-1500:])

# ---- measure cut jumps at the known boundaries ----
p = subprocess.run(["./tools/ffmpeg.exe", "-v", "error", "-i", OUT,
                    "-vf", "fps=15,scale=96:170,format=gray",
                    "-f", "rawvideo", "-"], capture_output=True)
a = np.frombuffer(p.stdout, dtype=np.uint8)
px = 96 * 170
n = len(a) // px
a = a[:n * px].reshape(n, 170, 96).astype(float)
d = np.abs(np.diff(a, axis=0)).mean(axis=(1, 2))

bounds, acc = [], 0.0
for _, _, t, _ in PLAN[:-1]:
    acc += t
    bounds.append(int(acc * 15))
jumps = [d[max(0, b - 1):b + 1].max() for b in bounds]
inshot = np.array([v for i, v in enumerate(d)
                   if not any(abs(i - b) <= 1 for b in bounds)])

print(f"total {n/15:.2f}s")
print("cut jumps: " + ", ".join(f"{j:.0f}" for j in jumps))
print(f"OURS  cut mean={np.mean(jumps):5.1f}  max={np.max(jumps):5.1f}   "
      f"in-shot mean={inshot.mean():5.2f}  p95={np.percentile(inshot,95):5.2f}")

# same metric on the reference, using ITS measured cut list, so the two
# numbers are actually comparable (the earlier 4.89 used a different exclusion)
REF = r"C:\Users\DKYLE\Downloads\ScreenRecording_07-25-2026 19-01-22_1.MP4"
REF_CUTS = [1.633, 2.467, 2.717, 3.383, 5.218, 7.052, 8.718, 10.068]
p = subprocess.run(["./tools/ffmpeg.exe", "-v", "error", "-i", REF,
                    "-vf", "fps=15,scale=96:170,format=gray",
                    "-f", "rawvideo", "-"], capture_output=True)
ra = np.frombuffer(p.stdout, dtype=np.uint8)
rn = len(ra) // px
ra = ra[:rn * px].reshape(rn, 170, 96).astype(float)
rd = np.abs(np.diff(ra, axis=0)).mean(axis=(1, 2))
rb = [int(c * 15) for c in REF_CUTS]
rj = [rd[max(0, b - 1):b + 1].max() for b in rb]
rin = np.array([v for i, v in enumerate(rd)
                if not any(abs(i - b) <= 1 for b in rb)])
print(f"REF   cut mean={np.mean(rj):5.1f}  max={np.max(rj):5.1f}   "
      f"in-shot mean={rin.mean():5.2f}  p95={np.percentile(rin,95):5.2f}")
