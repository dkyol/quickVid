"""starbucks_recut_v2.py — varied-rhythm assembly of the v2 Starbucks carve.

Structure: the free stills+crossfade progression (blank -> fully carved,
built by build_reel.py from the audited ladder rungs) opens as a fast
reveal, then three refinement macros show the knife adding finishing
touches to different regions, then the one true flat-to-carved transition
(the flower) plays as the money shot, then a static hands-free hero hold
closes on the calm, finished reference look.

Trim windows chosen from the Step 6 full-clip scrubs: each refinement
shot's action peaks mid-clip, never at the very start or tail. The flower
shot is `last_frame` interpolation, so per carvingSkill.MD Step 7 its
window stays clear of the final ~1s where Veo hard-snaps to the pinned end
frame (that snap reads as a jump cut if trimmed into).
"""
import subprocess, sys, os
import numpy as np

os.chdir(r"C:\Users\DKYLE\Desktop\scripts\quickVid")
M = "starbucks_watermelon_v2/media"
OUT = sys.argv[1] if len(sys.argv) > 1 else "starbucks_watermelon_v2/final/recut.mp4"
os.makedirs(os.path.dirname(OUT), exist_ok=True)

# (source path, start, dur) in the SOURCE 1080x1920 frame. All shots are
# already tight macros/wides with no cross-shot drift to correct (see v1's
# PLAN for why wide shots would otherwise need per-clip subject-centered
# crops) so none need a crop box here.
#
# v3: the knife-less stills+crossfade progression is GONE, replaced by 5
# real Veo interpolation shots (prog_ab..prog_ef), each a hand+knife
# carving one bounded region on camera -- per user feedback (2026-08-01)
# the stills sequence read as the melon carving itself with no visible
# mechanism. Trim windows stay in the early-mid range of each 8s clip,
# never the tail (Step 7: last_frame interpolation hard-snaps to the pinned
# end frame in the final ~1s, which reads as a jump cut if trimmed into).
#
# The progression still ends on stage_F (flowers still flat outline), NOT
# the finished master -- ending finished made the later flower_transition
# shot read as the carving running BACKWARD (flower already carved, then
# shown reverting to outline and re-carving), the "narrative regression"
# defect class v1's independent review caught. Flower completion happens
# exactly once, as the reel's actual final completion beat, right before
# the finished hero hold.
#
# v4: dropped the three "deepening" macros (crown/hair/face) entirely. Per
# user feedback (2026-08-01): even though each cut was technically correct
# (real dark rind converted to pale), it landed in a tiny gap between
# already-finished elements, so the REGION as a whole looked 100% done
# before and after -- "the knife does nothing" at the scale a viewer
# actually judges. The rule this establishes: a shot only reads as real
# carving if the cut converts a VISIBLY LARGE dark area to pale, not just
# technically-correct pixels in a small gap. The wide progression shots
# already show every one of these regions transforming for real, so the
# macros were pure redundant risk with no payoff -- cut, not replaced.
PLAN = [
    (f"{M}/veo_prog_ab.mp4",            0.8, 2.2),   # crown + star carved (canary shot, wide)
    (f"{M}/veo_prog_bc.mp4",             1.0, 1.8),   # face carved
    (f"{M}/veo_prog_cd.mp4",             1.0, 1.8),   # hair carved
    (f"{M}/veo_prog_de.mp4",             1.0, 1.6),   # medallion ring carved
    (f"{M}/veo_prog_ef.mp4",             1.0, 2.2),   # vines/leaves carved, flowers still outline
    (f"{M}/veo_04_flower_transition.mp4", 0.9, 4.5),  # completion beat: outline->carved
    (f"{M}/veo_05_hero_hold.mp4",       2.8, 3.0),    # calm hands-free close, now truly finished
]

GRADE = "eq=saturation=1.45,unsharp=5:5:0.5"

args = ["./tools/ffmpeg.exe", "-y", "-loglevel", "error"]
for src, ss, t in PLAN:
    args += ["-ss", str(ss), "-t", str(t), "-i", src]

fc = []
for i in range(len(PLAN)):
    fc.append(f"[{i}:v]scale=1080:1920,{GRADE},fps=30,setsar=1[v{i}]")
streams = "".join(f"[v{i}][{i}:a]" for i in range(len(PLAN)))
fc.append(f"{streams}concat=n={len(PLAN)}:v=1:a=1[vcat][acat]")
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
for _, _, t in PLAN[:-1]:
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
