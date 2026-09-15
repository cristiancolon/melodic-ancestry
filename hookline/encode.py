"""Melodic encodings and n-gram extraction.

Five encodings, following the Themefinder convention the plan specifies. A figure is a
run of consecutive notes; each encoding turns it into a token tuple that can be looked up
in an inverted index.

The encodings differ in *specificity*, which is the point: a figure can be rare as an
interval sequence and utterly commonplace as a gross contour. Rarity is therefore always
reported per encoding, never pooled across them.
"""
from __future__ import annotations

from typing import Iterable, Sequence

# Encoding names, ordered most to least specific.
ENCODINGS = ("pitch", "interval", "scale_degree", "contour_refined", "contour_gross")

# n is a count of NOTES. An n-note figure yields n-1 interval tokens.
MIN_N = 4
MAX_N = 12

# Huron's refined-contour threshold: a move of more than a whole tone is a leap.
_LEAP = 2

# Major/minor profiles for key estimation (Krumhansl-Schmuckler).
_MAJOR = (6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88)
_MINOR = (6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17)


def estimate_key(pitches: Sequence[int], durations: Sequence[float] | None = None) -> tuple[int, bool]:
    """Return (tonic_pitch_class, is_major) by correlating the duration-weighted pitch-class
    histogram against the Krumhansl-Schmuckler profiles."""
    if not pitches:
        return 0, True
    weights = list(durations) if durations is not None else [1.0] * len(pitches)
    hist = [0.0] * 12
    for p, w in zip(pitches, weights):
        hist[int(p) % 12] += float(w)
    total = sum(hist) or 1.0
    hist = [h / total for h in hist]

    best, best_score = (0, True), float("-inf")
    for tonic in range(12):
        for profile, is_major in ((_MAJOR, True), (_MINOR, False)):
            score = sum(hist[(tonic + i) % 12] * profile[i] for i in range(12))
            if score > best_score:
                best_score, best = score, (tonic, is_major)
    return best


def encode(pitches: Sequence[int], encoding: str, key: tuple[int, bool] | None = None) -> tuple:
    """Turn a pitch sequence into tokens under one encoding."""
    if encoding == "pitch":
        return tuple(int(p) % 12 for p in pitches)

    if encoding == "interval":
        return tuple(int(b) - int(a) for a, b in zip(pitches, pitches[1:]))

    if encoding == "scale_degree":
        tonic, _ = key if key is not None else estimate_key(pitches)
        return tuple((int(p) - tonic) % 12 for p in pitches)

    if encoding in ("contour_gross", "contour_refined"):
        toks = []
        for a, b in zip(pitches, pitches[1:]):
            d = int(b) - int(a)
            if encoding == "contour_gross":
                toks.append("U" if d > 0 else "D" if d < 0 else "S")
            else:
                if d == 0:
                    toks.append("S")
                elif d > _LEAP:
                    toks.append("U")
                elif d > 0:
                    toks.append("u")
                elif d < -_LEAP:
                    toks.append("D")
                else:
                    toks.append("d")
        return tuple(toks)

    raise ValueError(f"unknown encoding: {encoding!r}")


def figure_key(encoding: str, n: int, tokens: Iterable) -> str:
    """Canonical index key for one figure. n is the note count, so that figures from
    different encodings are never confused even when their token counts coincide."""
    body = ",".join(str(t) for t in tokens)
    return f"{encoding}:{n}:{body}"


def ngrams(
    pitches: Sequence[int],
    n_range: Iterable[int] = range(MIN_N, MAX_N + 1),
    encodings: Iterable[str] = ENCODINGS,
    key: tuple[int, bool] | None = None,
) -> dict[str, list[int]]:
    """All figure keys in a melody, mapped to the note offsets where they start.

    Offsets are kept so a match can be localized back to a position in the source, which
    is what lets the UI highlight the matching bars rather than just asserting a count.
    """
    if key is None:
        key = estimate_key(pitches)
    out: dict[str, list[int]] = {}
    for n in n_range:
        if n > len(pitches):
            break
        for start in range(len(pitches) - n + 1):
            window = pitches[start : start + n]
            for enc in encodings:
                out.setdefault(figure_key(enc, n, encode(window, enc, key)), []).append(start)
    return out
