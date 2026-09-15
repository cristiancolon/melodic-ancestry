"""Tempo, beat grid and metric stress.

This exists because of a specific gap the plan identifies: MCIC's symbolic files had
rests removed in 97.34% of transitions, so score position is unrecoverable from them and
Savage's stressed/unstressed levels cannot be reconstructed. Audio still carries it. The
stress weights produced here are what make a rhythm-weighted edit distance possible at
all, and they are only available on the audio path.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Relative weight by metric function, following the plan's ordering:
# final > stressed > unstressed > ornamental.
STRESS_WEIGHTS = {"final": 1.0, "downbeat": 0.9, "beat": 0.7, "offbeat": 0.4, "ornamental": 0.2}


@dataclass
class Beats:
    tempo_bpm: float
    beat_times: np.ndarray
    onset_env: np.ndarray
    env_times: np.ndarray
    confidence: float


def onset_envelope(x: np.ndarray, sr: int, hop: int = 256, n_fft: int = 1024) -> tuple[np.ndarray, np.ndarray]:
    """Spectral flux: half-wave-rectified positive change in magnitude across bins."""
    if len(x) < n_fft:
        x = np.pad(x, (0, n_fft - len(x)))
    n = 1 + (len(x) - n_fft) // hop
    strides = (x.strides[0] * hop, x.strides[0])
    frames = np.lib.stride_tricks.as_strided(x, shape=(n, n_fft), strides=strides)
    win = np.hanning(n_fft)
    mag = np.abs(np.fft.rfft(frames * win, axis=1))
    flux = np.maximum(np.diff(mag, axis=0, prepend=mag[:1]), 0).sum(axis=1)
    if flux.max() > 0:
        flux = flux / flux.max()
    return flux, (np.arange(n) * hop + n_fft / 2) / sr


def onset_times(
    x: np.ndarray, sr: int, hop: int = 256, sensitivity: float = 1.8, min_gap_s: float = 0.07
) -> np.ndarray:
    """Peak-picked onsets from the spectral flux.

    Needed because pitch stability alone cannot separate two consecutive notes at the
    SAME pitch -- they merge into one long note, and the resulting note sequence is a
    deletion that no amount of pitch re-ranking can repair.

    The default sensitivity sits in the middle of a plateau (1.0-2.5) measured on
    synthesised corpus melodies, where it recovers 40/40 note counts against 3/40 without
    onsets. That calibration is on CLEAN SYNTHETIC audio: a real mix has percussive flux
    everywhere and this parameter will need re-measuring there, which is what gate 2 is.
    """
    env, times = onset_envelope(x, sr, hop)
    if len(env) < 3:
        return np.zeros(0)
    # adaptive threshold: local mean over ~0.3s plus a fraction of the global spread
    win = max(int(0.3 * sr / hop), 3)
    kernel = np.ones(win) / win
    local = np.convolve(env, kernel, mode="same")
    thresh = local + sensitivity * env.std()
    peaks = [
        i for i in range(1, len(env) - 1)
        if env[i] > thresh[i] and env[i] >= env[i - 1] and env[i] > env[i + 1]
    ]
    picked, last = [], -1e9
    for i in peaks:
        if times[i] - last >= min_gap_s:
            picked.append(i)
            last = times[i]
    return times[picked] if picked else np.zeros(0)


def estimate(x: np.ndarray, sr: int, hop: int = 256, bpm_range: tuple[float, float] = (50.0, 200.0)) -> Beats:
    """Tempo by autocorrelation of the onset envelope; phase by best-aligned comb."""
    env, times = onset_envelope(x, sr, hop)
    if len(env) < 8:
        return Beats(0.0, np.zeros(0), env, times, 0.0)

    centred = env - env.mean()
    acf = np.correlate(centred, centred, mode="full")[len(centred) - 1 :]
    frame_rate = sr / hop
    lag_lo = max(1, int(frame_rate * 60.0 / bpm_range[1]))
    lag_hi = min(len(acf) - 1, int(frame_rate * 60.0 / bpm_range[0]))
    if lag_hi <= lag_lo:
        return Beats(0.0, np.zeros(0), env, times, 0.0)

    window = acf[lag_lo:lag_hi]
    lag = int(np.argmax(window)) + lag_lo
    peak = float(window.max())
    confidence = float(np.clip(peak / (acf[0] + 1e-9), 0.0, 1.0))
    tempo = 60.0 * frame_rate / lag

    # phase: the offset whose comb collects the most onset energy
    best_phase, best_score = 0, -np.inf
    for phase in range(lag):
        score = env[phase::lag].sum()
        if score > best_score:
            best_score, best_phase = score, phase
    beat_frames = np.arange(best_phase, len(env), lag)
    return Beats(tempo, times[beat_frames], env, times, confidence)


def stress(onsets: np.ndarray | list[float], beats: Beats, beats_per_bar: int = 4) -> list[str]:
    """Label each onset by metric function against the estimated grid."""
    if beats.beat_times.size < 2:
        return ["ornamental"] * len(onsets)
    period = float(np.median(np.diff(beats.beat_times)))
    tol = period * 0.18
    labels = []
    for t in onsets:
        idx = int(np.argmin(np.abs(beats.beat_times - t)))
        delta = abs(beats.beat_times[idx] - t)
        if delta > tol:
            labels.append("ornamental")
        elif idx % beats_per_bar == 0:
            labels.append("downbeat")
        elif idx % 2 == 0:
            labels.append("beat")
        else:
            labels.append("offbeat")
    return labels


def weights(labels: list[str], mark_final: bool = True) -> list[float]:
    out = [STRESS_WEIGHTS.get(l, 0.2) for l in labels]
    if mark_final and out:
        out[-1] = STRESS_WEIGHTS["final"]
    return out
