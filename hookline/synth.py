"""Melody synthesis, for demos and for measuring the audio path against known input.

Rendering a melody whose symbolic form is already in the index is the only way to ask
the question gate 2 asks: how much of a known melodic relationship survives the trip
through audio and back? Synthetic audio is the easy end of that -- a clean monophonic
tone is far kinder than a real mix -- so results here are an upper bound, and are
labelled as such wherever they are reported.
"""
from __future__ import annotations

import numpy as np

SR = 22050


def render(
    pitches: list[int],
    durations: list[float] | None = None,
    sr: int = SR,
    harmonics: tuple[float, ...] = (1.0, 0.42, 0.19, 0.08),
    gap: float = 0.045,
    vibrato_cents: float = 0.0,
    noise: float = 0.0,
    seed: int = 0,
) -> np.ndarray:
    """Render a note sequence as an additive-synthesis line.

    `noise` and `vibrato_cents` exist to degrade the signal deliberately: the interesting
    measurement is not whether transcription works on a clean tone, it is where it breaks.
    """
    rng = np.random.default_rng(seed)
    durs = durations or [0.38] * len(pitches)
    out = []
    for pitch, dur in zip(pitches, durs):
        n = max(int(dur * sr), 32)
        t = np.arange(n) / sr
        hz = 440.0 * 2 ** ((pitch - 69) / 12.0)
        if vibrato_cents:
            hz = hz * 2 ** ((vibrato_cents / 1200.0) * np.sin(2 * np.pi * 5.2 * t))
        phase = 2 * np.pi * np.cumsum(np.full(n, hz)) / sr
        wave = sum(a * np.sin((i + 1) * phase) for i, a in enumerate(harmonics))
        attack = max(int(0.012 * sr), 1)
        release = max(int(0.05 * sr), 1)
        env = np.ones(n)
        env[:attack] = np.linspace(0, 1, attack)
        env[-release:] = np.linspace(1, 0, release)
        out.append(wave * env)
        if gap > 0:
            out.append(np.zeros(int(gap * sr)))
    x = np.concatenate(out) if out else np.zeros(sr // 2)
    if noise > 0:
        x = x + rng.normal(0, noise * np.abs(x).mean(), len(x))
    peak = np.max(np.abs(x)) or 1.0
    return (x / peak * 0.92).astype(np.float32)
