"""Query expansion over a transcription lattice.

The claim this module implements: a prior-art count taken from a single top-1
transcription is a point estimate off one possibly-wrong reading, and at the note-level
accuracies real transcribers achieve that estimate is unreliable in a way nobody
reports. Carrying the full candidate set forward instead turns N into a random variable
with a computable distribution.

Given per-note candidates with posteriors, the set of readings is the product space.
Each reading `p` has probability P(p) and yields an exact match count N_p, so

    E[N]   = sum_p P(p) * N_p
    Var[N] = sum_p P(p) * N_p^2  -  E[N]^2

is exact given the path distribution -- no independence assumption between works is
needed, which matters because matches are heavily correlated across readings.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Sequence

DEFAULT_BEAM = 64
MIN_PATH_PROB = 1e-4


@dataclass
class Path:
    pitches: tuple[int, ...]
    prob: float


@dataclass
class Estimate:
    """A count with the uncertainty the transcription actually carries."""
    expected: float
    variance: float
    top1: int                 # what a single best-reading query would have returned
    n_paths: int
    path_mass: float          # probability mass retained by the beam
    modal_prob: float = 0.0   # probability the single best reading is the right one

    @property
    def sd(self) -> float:
        return math.sqrt(max(self.variance, 0.0))

    def interval(self, z: float = 1.96) -> tuple[int, int]:
        lo = max(0, int(round(self.expected - z * self.sd)))
        return lo, int(round(self.expected + z * self.sd))

    def as_dict(self) -> dict:
        lo, hi = self.interval()
        return {
            "expected": round(self.expected, 2),
            "sd": round(self.sd, 2),
            "low": lo,
            "high": hi,
            "top1": self.top1,
            "paths": self.n_paths,
            "path_mass": round(self.path_mass, 4),
            "modal_prob": round(self.modal_prob, 4),
        }


def enumerate_paths(
    candidates: Sequence[Sequence[tuple[int, float]]],
    beam: int = DEFAULT_BEAM,
    min_prob: float = MIN_PATH_PROB,
) -> list[Path]:
    """Beam search over the reading space, widest-probability-first.

    The beam is what keeps this tractable: k candidates over n notes is k**n readings,
    which for a 12-note figure at k=3 is over half a million. Retained mass is reported
    so a caller can tell how much of the distribution the beam actually covers.
    """
    if not candidates:
        return []
    paths: list[tuple[tuple[int, ...], float]] = [((), 1.0)]
    for slot in candidates:
        usable = [(int(p), float(w)) for p, w in slot if w > 0]
        if not usable:
            continue
        nxt = [(prefix + (p,), prob * w) for prefix, prob in paths for p, w in usable]
        nxt.sort(key=lambda pw: -pw[1])
        paths = [pw for pw in nxt[:beam] if pw[1] >= min_prob] or nxt[:1]
    return [Path(p, w) for p, w in paths]


def estimate_count(
    paths: Sequence[Path],
    count_fn: Callable[[tuple[int, ...]], int],
    renormalise: bool = True,
) -> Estimate:
    """Push each retained reading through `count_fn` and combine into E[N] and Var[N]."""
    if not paths:
        return Estimate(0.0, 0.0, 0, 0, 0.0, 0.0)

    mass = sum(p.prob for p in paths)
    scale = (1.0 / mass) if (renormalise and mass > 0) else 1.0

    cache: dict[tuple[int, ...], int] = {}
    exp = exp_sq = 0.0
    for path in paths:
        if path.pitches not in cache:
            cache[path.pitches] = int(count_fn(path.pitches))
        n = cache[path.pitches]
        w = path.prob * scale
        exp += w * n
        exp_sq += w * n * n

    top1 = cache.get(paths[0].pitches, 0)
    modal = paths[0].prob * scale
    return Estimate(exp, max(exp_sq - exp * exp, 0.0), top1, len(paths), mass, modal)


def top1_path(candidates: Sequence[Sequence[tuple[int, float]]]) -> tuple[int, ...]:
    """The single best reading -- what a conventional pipeline would hand downstream."""
    return tuple(int(slot[0][0]) for slot in candidates if slot)


def path_entropy(candidates: Sequence[Sequence[tuple[int, float]]]) -> float:
    """Total uncertainty in the reading, in bits. Reported so a wide interval can be
    attributed to a genuinely ambiguous transcription rather than to a thin corpus."""
    total = 0.0
    for slot in candidates:
        for _, w in slot:
            if w > 0:
                total -= w * math.log2(w)
    return total
