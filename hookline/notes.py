"""Frame-level f0 candidates -> note events that keep their alternatives.

The output type is the contract with `lattice.py`: every note carries a ranked list of
pitch hypotheses with posteriors summing to 1, not a single value. Collapsing to top-1
happens only where a caller explicitly asks for it, so the comparison between the two is
always available -- that comparison is the project's central claim.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .f0 import F0Track, hz_to_midi

MIN_NOTE_S = 0.06      # shorter than this is an artefact, not a note
MAX_STEP_SEMITONES = 0.85  # pitch movement within one note


@dataclass
class Note:
    onset: float
    duration: float
    pitch: int                      # top-1, rounded to the nearest semitone
    confidence: float               # posterior mass on `pitch`
    candidates: list[tuple[int, float]] = field(default_factory=list)

    @property
    def offset(self) -> float:
        return self.onset + self.duration


def _segment(
    track: F0Track,
    onset_times: np.ndarray | None = None,
    min_split_s: float = 0.11,
) -> list[tuple[int, int]]:
    """Split the voiced frames into runs of roughly stable pitch.

    Three things end a note: it stops being voiced, the pitch moves by more than about a
    semitone, or an onset is detected. The third matters more than it looks -- without it
    two consecutive notes at the same pitch merge into one, which measured out as a note
    deletion in 92% of test melodies and dominated every other error mode combined.
    """
    midi = np.asarray(hz_to_midi(track.best), dtype=float)
    hop_s = track.hop / track.sr
    onset_frames: set[int] = set()
    if onset_times is not None and len(onset_times):
        # Map onset TIMES onto the f0 track's own frame centres. The two stages use
        # different window sizes, so their frame centres differ by (frame-n_fft)/2 --
        # converting with a bare t/hop lands four frames late, which splits the middle
        # of the following note instead of its attack.
        onset_frames = {
            int(np.clip(np.searchsorted(track.times, t), 0, len(midi) - 1))
            for t in onset_times
        }

    spans, start = [], None
    for i in range(len(midi)):
        voiced = track.voiced[i]
        if voiced and start is None:
            start = i
        elif start is not None:
            broke = not voiced
            if not broke and i > start:
                broke = abs(midi[i] - np.median(midi[start:i])) > MAX_STEP_SEMITONES
            # An onset only ends a note that has actually been running: otherwise the
            # pitch-change break and the onset break fire a few frames apart and cut one
            # note into two.
            if not broke and i in onset_frames and (i - start) * hop_s >= min_split_s:
                broke = True
            if broke:
                spans.append((start, i))
                start = i if voiced else None
    if start is not None:
        spans.append((start, len(midi)))
    return spans


def extract(
    track: F0Track,
    k: int = 3,
    min_note_s: float = MIN_NOTE_S,
    onset_times: np.ndarray | None = None,
) -> list[Note]:
    """Aggregate frame candidates into notes, pooling posterior mass per semitone.

    A note's candidate list is the posterior-weighted histogram of every candidate
    pitch seen in its frames. That is what lets an octave error that was the top-1
    reading in half the frames survive as a ranked alternative rather than vanish.
    """
    hop_s = track.hop / track.sr
    notes: list[Note] = []

    for lo, hi in _segment(track, onset_times):
        dur = (hi - lo) * hop_s
        if dur < min_note_s:
            continue

        pitches = np.asarray(hz_to_midi(track.candidates[lo:hi]), dtype=float)
        weights = track.posteriors[lo:hi]
        mask = (track.candidates[lo:hi] > 0) & (weights > 0)
        if not mask.any():
            continue

        pooled: dict[int, float] = {}
        for p, w in zip(np.round(pitches[mask]).astype(int), weights[mask]):
            pooled[int(p)] = pooled.get(int(p), 0.0) + float(w)
        total = sum(pooled.values())
        if total <= 0:
            continue

        ranked = sorted(((p, w / total) for p, w in pooled.items()), key=lambda kv: -kv[1])[:k]
        # renormalise over the retained candidates so posteriors are a distribution
        kept = sum(w for _, w in ranked) or 1.0
        ranked = [(p, w / kept) for p, w in ranked]

        notes.append(
            Note(
                onset=lo * hop_s,
                duration=dur,
                pitch=ranked[0][0],
                confidence=ranked[0][1],
                candidates=ranked,
            )
        )
    return notes


def pitches(notes: list[Note]) -> list[int]:
    return [n.pitch for n in notes]


def mean_confidence(notes: list[Note]) -> float:
    return float(np.mean([n.confidence for n in notes])) if notes else 0.0
