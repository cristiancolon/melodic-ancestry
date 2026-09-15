"""Pitch tracking that emits ranked candidates, not one answer.

This is the reason the front end is written here rather than pulled off the shelf.
Basic Pitch and friends emit top-1 note events; the lattice in `lattice.py` needs a
ranked candidate list with posteriors at every position, because the whole design bet
is that the correct note is often *present* but not *first*.

The estimator is YIN (de Cheveigne & Kawahara 2002) with one deliberate change: instead
of taking the first dip below the absolute threshold, every local minimum of the
cumulative mean normalised difference is kept and ranked. Those minima are where octave
errors and neighbouring-semitone confusions live, which is exactly the error structure
the lattice is meant to survive.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

FRAME = 2048
HOP = 256
FMIN = 65.0    # C2
FMAX = 1050.0  # ~C6
MAX_CANDIDATES = 3


@dataclass
class F0Track:
    times: np.ndarray          # (F,) seconds
    candidates: np.ndarray     # (F, K) f0 in Hz, 0 where absent
    posteriors: np.ndarray     # (F, K) normalised, rows sum to 1 (or 0 if unvoiced)
    voiced: np.ndarray         # (F,) bool
    sr: int
    hop: int

    @property
    def best(self) -> np.ndarray:
        return self.candidates[:, 0]

    @property
    def confidence(self) -> np.ndarray:
        return self.posteriors[:, 0]


def _frame(x: np.ndarray, frame: int, hop: int) -> np.ndarray:
    if len(x) < frame:
        x = np.pad(x, (0, frame - len(x)))
    n = 1 + (len(x) - frame) // hop
    strides = (x.strides[0] * hop, x.strides[0])
    return np.lib.stride_tricks.as_strided(x, shape=(n, frame), strides=strides)


def _cmndf(frames: np.ndarray, tau_max: int) -> np.ndarray:
    """Cumulative mean normalised difference function, vectorised over frames.

    d(tau) is expanded as power terms minus twice the autocorrelation so the whole
    thing is one FFT per block rather than a loop over lags.
    """
    n_frames, w = frames.shape
    size = int(2 ** np.ceil(np.log2(2 * w)))
    spec = np.fft.rfft(frames, size, axis=1)
    acf = np.fft.irfft(spec * np.conj(spec), size, axis=1)[:, :tau_max]

    power = np.concatenate([np.zeros((n_frames, 1)), np.cumsum(frames**2, axis=1)], axis=1)
    taus = np.arange(tau_max)
    # sum of x[j]^2 over the overlap, and of x[j+tau]^2 over the same span
    left = power[:, w - taus]
    right = power[:, w][:, None] - power[:, taus]
    d = left + right - 2 * acf

    d = np.maximum(d, 0.0)
    cum = np.cumsum(d[:, 1:], axis=1)
    denom = cum / np.maximum(taus[1:][None, :], 1)
    out = np.ones_like(d)
    np.divide(d[:, 1:], np.where(denom == 0, np.inf, denom), out=out[:, 1:])
    return out


def _parabolic(d: np.ndarray, idx: np.ndarray) -> np.ndarray:
    """Sub-sample refinement of a minimum by fitting a parabola to its neighbours."""
    idx = np.clip(idx, 1, d.shape[1] - 2)
    rows = np.arange(d.shape[0])[:, None]
    a, b, c = d[rows, idx - 1], d[rows, idx], d[rows, idx + 1]
    denom = a - 2 * b + c
    shift = np.where(np.abs(denom) < 1e-12, 0.0, 0.5 * (a - c) / np.where(denom == 0, 1, denom))
    return idx + np.clip(shift, -1.0, 1.0)


def track(
    x: np.ndarray,
    sr: int,
    hop: int = HOP,
    frame: int = FRAME,
    fmin: float = FMIN,
    fmax: float = FMAX,
    k: int = MAX_CANDIDATES,
    voiced_threshold: float = 0.45,
    absolute_threshold: float = 0.15,
) -> F0Track:
    """Estimate f0 candidates per frame.

    `voiced_threshold` is on the YIN aperiodicity: a frame is voiced when its best
    minimum sits below it. Frames failing it get zero posterior mass and are treated as
    rests, which is what phrase segmentation keys on. `absolute_threshold` is YIN's own
    dip threshold, used to pick the primary candidate by period rather than by depth.
    """
    tau_min = max(2, int(sr / fmax))
    tau_max = min(int(sr / fmin) + 1, frame // 2)
    frames = _frame(np.asarray(x, dtype=np.float64), frame, hop)
    n_frames = frames.shape[0]

    cands = np.zeros((n_frames, k), dtype=np.float32)
    posts = np.zeros((n_frames, k), dtype=np.float32)
    voiced = np.zeros(n_frames, dtype=bool)

    block = 512  # bounds peak memory on long files
    pool = max(k, 6)  # gather more minima than we keep, then re-rank
    for lo in range(0, n_frames, block):
        hi = min(lo + block, n_frames)
        d = _cmndf(frames[lo:hi], tau_max)
        rows = np.arange(hi - lo)[:, None]

        window = d[:, tau_min:tau_max]
        interior = window[:, 1:-1]
        is_min = (interior < window[:, :-2]) & (interior <= window[:, 2:])
        depth = np.where(is_min, 1.0 - interior, -np.inf)

        # --- YIN's own rule picks the primary: the SMALLEST tau below the absolute
        # threshold, not the deepest dip. Ranking by depth alone lands on the
        # subharmonic and produces systematic octave-down errors.
        below = is_min & (interior < absolute_threshold)
        has_below = below.any(axis=1)
        first_below = np.argmax(below, axis=1)
        deepest = np.argmax(depth, axis=1)
        primary = np.where(has_below, first_below, deepest)

        take = min(pool, depth.shape[1])
        order = np.argsort(-depth, axis=1)[:, :take]
        # put the YIN primary first, keeping the rest in depth order
        order = np.concatenate([primary[:, None], order], axis=1)
        keep = np.ones(order.shape, dtype=bool)
        keep[:, 1:] = order[:, 1:] != primary[:, None]
        ranked = np.where(keep, order, -1)

        tau_idx = ranked + tau_min + 1
        refined = _parabolic(d, np.maximum(tau_idx, 0))
        f0 = np.where(refined > 0, sr / np.maximum(refined, 1e-9), 0.0)
        cand_depth = np.where(ranked >= 0, depth[rows, np.maximum(ranked, 0)], -np.inf)

        valid = (ranked >= 0) & np.isfinite(cand_depth) & (f0 >= fmin) & (f0 <= fmax)
        weight = np.where(valid, np.maximum(cand_depth, 0.0), 0.0)

        # --- Subharmonic penalty. A dip at an integer multiple of the primary period is
        # an octave/twelfth error, not a rival reading, and its dip is often marginally
        # DEEPER than the true one -- which is precisely how depth-ranking goes wrong.
        tau_primary = np.maximum(refined[:, :1], 1e-9)
        ratio = refined / tau_primary
        nearest = np.round(ratio)
        subharmonic = (nearest >= 2) & (np.abs(ratio - nearest) < 0.05)
        harmonic = (np.abs(ratio * np.round(1.0 / np.maximum(ratio, 1e-9)) - 1.0) < 0.05) & (ratio < 0.95)
        weight = np.where(subharmonic, weight * 0.30, weight)
        weight = np.where(harmonic, weight * 0.55, weight)
        weight = weight**2

        # The primary is pinned at slot 0: YIN selects it by period, and re-sorting the
        # whole set by depth is what reintroduced the octave error.
        rest = weight[:, 1:]
        rest_order = np.argsort(-rest, axis=1) + 1
        keep_k = min(k, weight.shape[1])
        sel = np.concatenate([np.zeros((hi - lo, 1), dtype=int), rest_order], axis=1)[:, :keep_k]

        w_k = weight[rows, sel]
        f_k = np.where(valid[rows, sel], f0[rows, sel], 0.0)
        w_k = np.where(valid[rows, sel], w_k, 0.0)

        total = w_k.sum(axis=1, keepdims=True)
        norm = np.divide(w_k, total, out=np.zeros_like(w_k), where=total > 0)

        frame_voiced = (cand_depth[:, 0] >= voiced_threshold) & valid[:, 0]
        cands[lo:hi, :keep_k] = np.where(frame_voiced[:, None], f_k, 0.0)
        posts[lo:hi, :keep_k] = np.where(frame_voiced[:, None], norm, 0.0)
        voiced[lo:hi] = frame_voiced

    times = (np.arange(n_frames) * hop + frame / 2) / sr
    return F0Track(times, cands, posts, voiced, sr, hop)


def hz_to_midi(f: np.ndarray | float) -> np.ndarray | float:
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(np.asarray(f) > 0, 69.0 + 12.0 * np.log2(np.asarray(f, dtype=float) / 440.0), 0.0)
