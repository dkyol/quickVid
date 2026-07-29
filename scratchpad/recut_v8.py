"""Recut v8: varied rhythm, punch-in on wides, one flash cut, 08_mouth split
into approach+reveal. Trim windows were chosen by scrubbing all 9 promoted
clips frame-by-frame (see conversation) — three clips (01_open, 03_ears,
06_nose_macro) drift into an unbounded red-flesh mouth reveal late in their
8s duration despite a bounded prompt; windows below stay inside the verified
clean range for each.
"""
import subprocess, sys, os
import numpy as np

os.chdir(r"C:\Users\DKYLE\Desktop\scripts\quickVid")
M = "wolf_watermelon/media"
OUT = sys.argv[1] if len(sys.argv) > 1 else "wolf_watermelon/final/v8_recut.mp4"

# name, start, dur, punch-in zoom (1.0 = full frame, macros already tight)
PLAN = [
    ("veo_01_open",        4.0, 1.8, 1.40),   # ends later: more pale exposed at cut
    ("veo_02_ear_macro",   4.6, 0.4, 1.00),   # flash — absorbs wide->macro jump
    ("veo_03_ears",        4.3, 1.6, 1.35),   # ends later: more pale before cut
    ("veo_04_eye_macro",   4.7, 0.45, 1.00),  # 2nd flash — same treatment as 02
    ("veo_05_midface",     4.6, 1.6, 1.35),
    ("veo_06_nose_macro",  4.0, 0.85, 1.00),  # verified clean only to 6.0s
    ("veo_07_ruff",        3.6, 1.5, 1.35),
    ("veo_08_mouth",       1.2, 0.9, 1.35),   # approach: knife at closed mouth
    # reveal: NOT 3.4-5.2 — verified 2026-07-29 that the knife sits directly
    # over the nose from ~3.7s to past 6s, obscuring/removing it from frame;
    # cutting from there to 09_hero (nose intact) reads as the nose magically
    # reappearing. Landing on 6.6-7.6s instead — knife has cleared the face,
    # mouth fully open and red, nose and fangs visible — matches 09_hero's
    # start frame almost exactly. The excavation itself is implied across
    # the 08a->08b cut rather than shown, same technique the reference uses.
    ("veo_08_mouth",       6.6, 1.0, 1.35),
    ("veo_09_hero",        4.6, 1.3, 1.25),   # after the turn-to-bare-side beat
]

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

print(f"total {n/15:.2f}s, {len(PLAN)} clips, {len(bounds)} cuts")
print("cut jumps: " + ", ".join(f"{j:.0f}" for j in jumps))
print(f"OURS  cut mean={np.mean(jumps):5.1f}  max={np.max(jumps):5.1f}   "
      f"in-shot mean={inshot.mean():5.2f}  p95={np.percentile(inshot,95):5.2f}")

REF = r"C:\Users\DKYLE\Downloads\ScreenRecording_07-25-2026 19-01-22_1.MP4"
REF_CUTS = [1.633, 2.467, 2.717, 3.383, 5.218, 7.052, 8.718, 10.068]
if os.path.isfile(REF):
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
else:
    print(f"(reference file not found at {REF}, skipping comparison)")
