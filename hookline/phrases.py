"""Phrase segmentation and hook ranking.

A hook is the figure a listener recognises, and what makes it recognisable is that it
comes back. So phrases are ranked by how often a similar phrase recurs in the same
piece, which needs no query from the user -- the difference between a tool you can enjoy
and one you must already know how to drive.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .encode import encode
from .notes import Note

REST_GAP_S = 0.18       # silence longer than this ends a phrase
MAX_PHRASE_NOTES = 16
MIN_PHRASE_NOTES = 4
SIMILAR_THRESHOLD = 0.72
MIN_DISTINCT_PITCHES = 3   # a flat line is not a melodic figure


@dataclass
class Phrase:
    start: int
    end: int                       # exclusive
    notes: list[Note]
    hook_score: float = 0.0
    repetitions: int = 0
    stress: list[str] = field(default_factory=list)

    @property
    def pitches(self) -> list[int]:
        return [n.pitch for n in self.notes]

    @property
    def onset(self) -> float:
        return self.notes[0].onset if self.notes else 0.0

    @property
    def offset(self) -> float:
        return self.notes[-1].offset if self.notes else 0.0

    def candidates(self) -> list[list[tuple[int, float]]]:
        return [n.candidates for n in self.notes]


def segment(notes: list[Note], rest_gap: float = REST_GAP_S) -> list[Phrase]:
    """Split at rests, then at a hard length cap so a legato run still yields figures."""
    if not notes:
        return []
    bounds, start = [], 0
    for i in range(1, len(notes)):
        gap = notes[i].onset - notes[i - 1].offset
        if gap > rest_gap or (i - start) >= MAX_PHRASE_NOTES:
            bounds.append((start, i))
            start = i
    bounds.append((start, len(notes)))
    return [Phrase(a, b, notes[a:b]) for a, b in bounds if b - a >= MIN_PHRASE_NOTES]


def _similarity(a: list[int], b: list[int]) -> float:
    """Normalised similarity of two interval sequences, by longest common subsequence.

    Intervals rather than pitches, so a phrase repeated at a different pitch level still
    counts as a repetition -- which is how hooks actually recur.
    """
    ia, ib = list(encode(a, "interval")), list(encode(b, "interval"))
    if not ia or not ib:
        return 0.0
    prev = [0] * (len(ib) + 1)
    for x in ia:
        cur = [0] * (len(ib) + 1)
        for j, y in enumerate(ib, 1):
            cur[j] = prev[j - 1] + 1 if x == y else max(prev[j], cur[j - 1])
        prev = cur
    return prev[len(ib)] / max(len(ia), len(ib))


def is_melodic(phrase: "Phrase", min_distinct: int = MIN_DISTINCT_PITCHES) -> bool:
    """Reject figures that carry no melodic information.

    A sustained note tracked across several onsets encodes as (0, 0, 0, 0), which is the
    single most common interval n-gram in any corpus -- on a real mix it matched over a
    thousand works at the 100th percentile. Counting it is technically correct and
    entirely useless, so it does not become a card.
    """
    return len(set(phrase.pitches)) >= min_distinct


def rank(phrases: list[Phrase], threshold: float = SIMILAR_THRESHOLD) -> list[Phrase]:
    """Score each phrase by recurrence, weighted slightly toward longer phrases."""
    for i, ph in enumerate(phrases):
        reps = sum(
            1 for j, other in enumerate(phrases)
            if i != j and _similarity(ph.pitches, other.pitches) >= threshold
        )
        ph.repetitions = reps
        length_bonus = min(len(ph.notes), 12) / 12.0
        confidence = float(np.mean([n.confidence for n in ph.notes])) if ph.notes else 0.0
        ph.hook_score = (1.0 + reps) * (0.55 + 0.25 * length_bonus + 0.20 * confidence)
    return sorted(phrases, key=lambda p: -p.hook_score)


def find_hooks(notes: list[Note], top: int = 5) -> list[Phrase]:
    return rank([p for p in segment(notes) if is_melodic(p)])[:top]
