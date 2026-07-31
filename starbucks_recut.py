"""starbucks_recut.py — varied-rhythm assembly of the 5 clips that survived
full-length QC (see conversation): 01_open and 02_star_macro both drift late
in their 8s (01 runs away to a finished carve ~4-5s in; 02 punches a stray
hole in the star tip ~7s in) so both are trimmed to an EARLY clean window,
never the tail. 03_crown, 05_hair_macro, 07_hero are clean throughout. 04_face
and 06_border failed QC on every take generated and are dropped — the border/
hair-completion work they would have shown is implied across the cut into
07_hero, same technique the reference reel itself uses.

v2: the first cut of this recut used ONE fixed punch-in zoom centered on the
FRAME for every wide shot, which does nothing to fix (and can worsen) subject
drift when the three wide shots — 01_open, 03_crown, 07_hero — are each an
independent Veo generation with no shared camera lock (see carvingSkill.MD
Step 5/7). Measured their actual subject bounding boxes: 03_crown frames the
melon largest (bbox height 1555px of 1920), 01_open next (1374px), 07_hero
smallest (1315px). Since a crop can only zoom IN (magnify), not out, 03_crown
— the largest — is the achievable common target; 01_open and 07_hero are each
given their OWN zoom + SUBJECT-centered crop origin (not frame-centered) so
their subject lands at the same size and frame-relative position 03_crown's
does natively.
"""
import subprocess, sys, os
import numpy as np

os.chdir(r"C:\Users\DKYLE\Desktop\scripts\quickVid")
M = "starbucks_watermelon/media"
OUT = sys.argv[1] if len(sys.argv) > 1 else "starbucks_watermelon/final/recut.mp4"
os.makedirs(os.path.dirname(OUT), exist_ok=True)

# name, start, dur, crop window as (w,h,x,y) in the SOURCE 1080x1920 frame
# (None = no crop, use full frame). Computed from each clip's measured
# subject bbox so all three wide shots land at 03_crown's native scale/
# position; macros are left uncropped (already tight, different scale is
# expected when cutting wide->macro).
PLAN = [
    ("veo_01_open",       0.3, 2.0, (954, 1696, 82, 179)),
    ("veo_02_star_macro", 3.2, 1.2, None),
    ("veo_03_crown",      1.8, 2.3, None),
    ("veo_05_hair_macro", 3.5, 1.2, None),
    ("veo_07_hero",       2.8, 4.5, (914, 1624, 121, 260)),
]

GRADE = "eq=saturation=1.45,unsharp=5:5:0.5"

args = ["./tools/ffmpeg.exe", "-y", "-loglevel", "error"]
for name, ss, t, _ in PLAN:
    args += ["-ss", str(ss), "-t", str(t), "-i", f"{M}/{name}.mp4"]

fc = []
for i, (_, _, _, crop_box) in enumerate(PLAN):
    if crop_box:
        w, h, x, y = crop_box
        crop = f"crop={w}:{h}:{x}:{y},scale=1080:1920:flags=lanczos"
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

# ---- measure cut jumps ----
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

print(f"total {n/15:.2f}s, {len(PLAN)} clips, {len(bounds)} cuts")
print("cut jumps: " + ", ".join(f"{j:.0f}" for j in jumps))
print(f"cut mean={np.mean(jumps):5.1f}  max={np.max(jumps):5.1f}   "
      f"in-shot mean={inshot.mean():5.2f}  p95={np.percentile(inshot,95):5.2f}")
print(f"\n-> {OUT}")
