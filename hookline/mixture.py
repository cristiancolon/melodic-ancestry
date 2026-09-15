"""Controlled polyphonic mixtures, for measuring melody extraction against known truth.

The degradation sweep in `scripts/degradation.py` degrades the *signal* -- noise and
vibrato -- while leaving the melody monophonic and dominant. That is not how a real mix
defeats a pitch tracker. A real mix never touches the melody; it buries it under a bass
line, chords and drums, and the tracker locks onto whichever source is loudest and most
periodic. On a real commercial track that was the bass: 89% of detected notes fell below
C4.

This module reproduces that failure with ground truth attached, so a fix can be measured
rather than asserted.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

SR = 22050


@dataclass
class Mix:
    audio: np.ndarray
    melody_pitches: list[int]
    melody_only: np.ndarray
    sr: int = SR


def _tone(pitch: float, dur: float, sr: int, harmonics=(1.0, 0.4, 0.18, 0.08), attack=0.012) -> np.ndarray:
    n = max(int(dur * sr), 32)
    t = np.arange(n) / sr
    hz = 440.0 * 2 ** ((pitch - 69) / 12.0)
    wave = sum(a * np.sin(2 * np.pi * hz * (i + 1) * t) for i, a in enumerate(harmonics))
    env = np.ones(n)
    a = max(int(attack * sr), 1)
    r = max(int(0.05 * sr), 1)
    env[:a] = np.linspace(0, 1, a)
    env[-r:] = np.linspace(1, 0, r)
    return wave * env


def _drums(n: int, sr: int, bpm: float, rng) -> np.ndarray:
    """Four-on-the-floor kick, backbeat snare, eighth-note hats."""
    out = np.zeros(n)
    beat = 60.0 / bpm
    t_kick = np.arange(0, n / sr, beat)
    for i, start in enumerate(t_kick):
        s = int(start * sr)
        # kick: fast downward pitch sweep, this is what a bass tracker latches onto
        d = int(0.12 * sr)
        if s + d > n:
            break
        tt = np.arange(d) / sr
        f = 110 * np.exp(-tt * 32) + 42
        out[s:s + d] += 0.9 * np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-tt * 14)
        if i % 2 == 1:  # snare on 2 and 4
            d2 = int(0.09 * sr)
            if s + d2 <= n:
                out[s:s + d2] += 0.5 * rng.normal(0, 1, d2) * np.exp(-np.arange(d2) / sr * 30)
    for start in np.arange(0, n / sr, beat / 2):  # hats
        s = int(start * sr)
        d = int(0.03 * sr)
        if s + d > n:
            break
        out[s:s + d] += 0.16 * rng.normal(0, 1, d) * np.exp(-np.arange(d) / sr * 90)
    return out


def render(
    melody: list[int],
    durations: list[float] | None = None,
    sr: int = SR,
    bass_level: float = 0.9,
    chord_level: float = 0.5,
    drum_level: float = 0.7,
    melody_level: float = 1.0,
    bpm: float = 120.0,
    seed: int = 0,
) -> Mix:
    """Melody over bass, chords and drums, each at a controllable level.

    Levels are relative amplitudes before normalisation. `bass_level=0` with
    `drum_level=0` reduces to the monophonic case the earlier sweep measured.
    """
    rng = np.random.default_rng(seed)
    durs = durations or [0.42] * len(melody)

    mel = np.concatenate([_tone(p, d, sr) for p, d in zip(melody, durs)])
    n = len(mel)

    # bass: root of the melody note, two octaves down, held over pairs of notes
    bass = np.zeros(n)
    pos = 0
    for i, (p, d) in enumerate(zip(melody, durs)):
        length = int(d * sr)
        if i % 2 == 0:
            root = p - 24
            seg = _tone(root, min(2 * d, (n - pos) / sr), sr, harmonics=(1.0, 0.5, 0.25), attack=0.02)
            end = min(pos + len(seg), n)
            bass[pos:end] += seg[: end - pos]
        pos += length

    # chords: a sustained triad in the middle register
    chords = np.zeros(n)
    pos = 0
    for i, (p, d) in enumerate(zip(melody, durs)):
        length = int(d * sr)
        if i % 4 == 0:
            for interval in (0, 4, 7):
                seg = _tone(p - 12 + interval, min(4 * d, (n - pos) / sr), sr,
                            harmonics=(0.6, 0.3, 0.1), attack=0.06)
                end = min(pos + len(seg), n)
                chords[pos:end] += seg[: end - pos] * 0.5
        pos += length

    drums = _drums(n, sr, bpm, rng) if drum_level > 0 else np.zeros(n)

    def norm(a):
        peak = np.max(np.abs(a))
        return a / peak if peak > 0 else a

    mix = (melody_level * norm(mel) + bass_level * norm(bass)
           + chord_level * norm(chords) + drum_level * norm(drums))
    return Mix(norm(mix).astype(np.float32), list(melody), norm(mel).astype(np.float32), sr)
