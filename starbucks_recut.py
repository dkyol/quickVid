"""starbucks_recut.py — varied-rhythm assembly of all 7 shots.

v2: replaced a uniform frame-centered punch-in crop with per-clip SUBJECT-
centered crops for the 3 wide shots (01_open/03_crown/07_hero), since each is
an independent Veo generation with no shared camera lock and drifted in
scale/position otherwise. See carvingSkill.MD Step 5/7.

v3: added 04_face and 06_border back in (first+last-frame interpolation
fixed both — see conversation), bringing the shot count to 7.

v4: an independent cold review caught two defects v3 missed: (1) 02_star_macro
was seeded from a since-corrected, over-carved ladder rung, so it showed the
face/hair already finished, then shot 3 showed them flat again — a visible
"carve runs backwards" regression; (2) stage_B_crown_star had the crown's
background crescent INVERTED (cream where it should be dark green, matching
the master), which poisoned every shot sourced from it (02, 03, 04). Fixed by
rebuilding stage_B_crown_star and its dependent crops, then regenerating
02/03/04. Also adds loudnorm — the review measured the source audio at
-43.5 LUFS (near-silent, esp. the hero's last 4s at -71 LUFS) against a -14
LUFS social target.

v5: 05_hair_macro dropped entirely. Its seed (crop_hair_wave, cut from
stage_D_hair) turned out to have captured the crown's zigzag bottom teeth
plus a stray shadow wedge, not clean hair waves -- stage_D_hair was one of
the over-carved/broken rungs identified in v4's cleanup and never rebuilt.
A same-region crop from the CORRECTED stage_B_crown_star was tried as a
replacement, but revealed stage_B's hair is ALSO already fully carved (a
third instance of this rung over-delivering beyond "crown+star only", after
the border and the crescent color) -- there is no verified-clean "hair
partially carved" seed anywhere in this ladder. Rather than risk a third
edit attempt at building one, the beat is dropped: 03_crown already shows
hair fully carved (confirmed on the actual regenerated clip), so the jump
from 01_open (0%) to 03_crown (~65%, hair included) already implies the
hair got carved off-camera, consistent with how this reel already treats
the face/border beats.
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
    ("veo_02_star_macro", 3.2, 1.3, None),
    ("veo_03_crown",      1.8, 2.5, None),
    ("veo_04_face",       1.8, 1.8, None),
    ("veo_06_border",     3.3, 1.8, None),
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
fc.append(f"{streams}concat=n={len(PLAN)}:v=1:a=1[vcat][acat]")
# source audio measured at -43.5 LUFS (near-silent); normalize to a social
# target instead of shipping near-silence with a stray loud transient.
fc.append("[acat]loudnorm=I=-14:TP=-1.5:LRA=11[a]")

args += ["-filter_complex", ";".join(fc), "-map", "[vcat]", "-map", "[a]",
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
