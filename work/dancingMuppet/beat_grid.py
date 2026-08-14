"""song -> BPM, beat times, bar times as JSON. No librosa; ffmpeg decode + scipy STFT."""
import sys
import json
import subprocess
import numpy as np
from scipy.signal import stft

FFMPEG = r"C:\Users\DKYLE\Desktop\scripts\quickVid\tools\ffmpeg.exe"
SR = 22050


def decode_pcm(path):
    cmd = [FFMPEG, "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"]
    out = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype=np.float32)


def onset_envelope(y, sr):
    f, t, Z = stft(y, fs=sr, nperseg=1024, noverlap=768)
    mag = np.abs(Z)
    flux = np.diff(mag, axis=1)
    flux[flux < 0] = 0
    env = flux.sum(axis=0)
    env = env / (env.max() + 1e-9)
    hop_dt = t[1] - t[0]
    return env, hop_dt


def estimate_tempo(env, hop_dt, bpm_lo=80, bpm_hi=160):
    env = env - env.mean()
    ac = np.correlate(env, env, mode="full")
    ac = ac[len(ac) // 2:]
    lag_lo = int(round(60.0 / bpm_hi / hop_dt))
    lag_hi = int(round(60.0 / bpm_lo / hop_dt))
    lag_hi = min(lag_hi, len(ac) - 1)
    if lag_hi <= lag_lo:
        raise ValueError("tempo search window empty; check hop_dt/bpm range")
    window = ac[lag_lo:lag_hi + 1]
    best_lag = lag_lo + int(np.argmax(window))
    period_s = best_lag * hop_dt
    bpm = 60.0 / period_s
    return bpm, period_s


def best_phase(env, hop_dt, period_s, duration_s):
    period_frames = period_s / hop_dt
    n_frames = len(env)
    best_score, best_offset = -1, 0.0
    for offset_s in np.arange(0, period_s, hop_dt):
        offset_frames = offset_s / hop_dt
        idx = offset_frames
        score = 0.0
        while idx < n_frames:
            i0 = int(round(idx))
            if i0 < n_frames:
                score += env[i0]
            idx += period_frames
        if score > best_score:
            best_score, best_offset = score, offset_s
    return best_offset


def main():
    if len(sys.argv) < 2:
        print("usage: beat_grid.py <audio_path> [out_json]", file=sys.stderr)
        sys.exit(1)
    path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else None

    y = decode_pcm(path)
    duration_s = len(y) / SR
    env, hop_dt = onset_envelope(y, SR)
    bpm, period_s = estimate_tempo(env, hop_dt)
    phase_s = best_phase(env, hop_dt, period_s, duration_s)

    beat_times = list(np.arange(phase_s, duration_s, period_s))
    bar_times = beat_times[0::4]

    result = {
        "path": path,
        "duration_s": round(duration_s, 3),
        "bpm": round(bpm, 2),
        "beat_period_s": round(period_s, 4),
        "phase_s": round(phase_s, 4),
        "beat_times": [round(x, 3) for x in beat_times],
        "bar_times": [round(x, 3) for x in bar_times],
    }
    js = json.dumps(result, indent=2)
    if out_path:
        with open(out_path, "w") as f:
            f.write(js)
    print(js)


if __name__ == "__main__":
    main()
