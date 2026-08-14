"""clip -> dominant motion period, for the retime. ffmpeg rawvideo -> numpy frame-diff -> autocorrelate."""
import sys
import json
import subprocess
import numpy as np

FFMPEG = r"C:\Users\DKYLE\Desktop\scripts\quickVid\tools\ffmpeg.exe"
FFPROBE = r"C:\Users\DKYLE\Desktop\scripts\quickVid\tools\ffprobe.exe"
OUT_W, OUT_H = 90, 160  # small grayscale for speed


def probe_fps(path):
    cmd = [FFPROBE, "-v", "error", "-select_streams", "v:0",
           "-show_entries", "stream=avg_frame_rate", "-of", "csv=p=0", path]
    out = subprocess.run(cmd, capture_output=True, check=True).stdout.decode().strip()
    num, den = out.split("/")
    return float(num) / float(den)


def decode_gray_frames(path, w=OUT_W, h=OUT_H):
    cmd = [FFMPEG, "-v", "error", "-i", path,
           "-vf", f"scale={w}:{h},format=gray",
           "-f", "rawvideo", "-"]
    out = subprocess.run(cmd, capture_output=True, check=True).stdout
    frame_bytes = w * h
    n_frames = len(out) // frame_bytes
    arr = np.frombuffer(out[:n_frames * frame_bytes], dtype=np.uint8)
    return arr.reshape(n_frames, h, w).astype(np.float32)


def motion_signal(frames):
    diffs = np.abs(np.diff(frames, axis=0)).mean(axis=(1, 2))
    return diffs


def dominant_period(signal, fps, period_lo_s=0.3, period_hi_s=4.0):
    signal = signal - signal.mean()
    ac = np.correlate(signal, signal, mode="full")
    ac = ac[len(ac) // 2:]
    lag_lo = max(1, int(round(period_lo_s * fps)))
    lag_hi = min(len(ac) - 1, int(round(period_hi_s * fps)))
    if lag_hi <= lag_lo:
        return None
    window = ac[lag_lo:lag_hi + 1]
    best_lag = lag_lo + int(np.argmax(window))
    return best_lag / fps


def main():
    if len(sys.argv) < 2:
        print("usage: motion_period.py <video_path> [out_json]", file=sys.stderr)
        sys.exit(1)
    path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else None

    fps = probe_fps(path)
    frames = decode_gray_frames(path)
    signal = motion_signal(frames)
    period_s = dominant_period(signal, fps)

    result = {
        "path": path,
        "fps": round(fps, 3),
        "n_frames": int(frames.shape[0]),
        "mean_abs_frame_diff": round(float(signal.mean()), 4),
        "max_abs_frame_diff": round(float(signal.max()), 4),
        "dominant_motion_period_s": round(period_s, 4) if period_s else None,
    }
    js = json.dumps(result, indent=2)
    if out_path:
        with open(out_path, "w") as f:
            f.write(js)
    print(js)


if __name__ == "__main__":
    main()
