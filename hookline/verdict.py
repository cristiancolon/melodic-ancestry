"""Turning counts into a verdict -- and, more often, into an abstention.

Three of the four possible verdicts decline to name anything. That is the design. The
rules below are the plan's never-ship list expressed as code rather than as prose:

  * no similarity score is ever emitted as a conclusion
  * no direction is ever claimed from the audio
  * no originator is named when the earliest matches are folk or undated
  * no count is emitted without its denominator and its interval
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Sequence

from .encode import encode, figure_key
from .index import Index
from .lattice import Estimate, enumerate_paths, estimate_count, path_entropy, top1_path

DISTINCTIVE_MAX_PERCENTILE = 40.0
COMMONPLACE_MIN_PERCENTILE = 60.0
MIN_MEAN_CONFIDENCE = 0.45
MIN_PATH_MASS = 0.40
MIN_MODAL_PROB = 0.12

VERDICTS = ("distinctive", "commonplace", "no_single_originator", "insufficient_confidence")


@dataclass
class StratumCount:
    stratum: str
    license: str
    provenance: str
    n_docs: int
    n: dict                       # works containing the figure, with interval
    m: dict | None                # of those, predating the reference year
    rarity_percentile: float | None
    earliest: int | None
    undated_in_stratum: int
    matches: list[dict] = field(default_factory=list)


@dataclass
class Card:
    label: str
    onset: float
    offset: float
    n_notes: int
    encoding: str
    top1_pitches: list[int]
    mean_confidence: float
    entropy_bits: float
    reading_probability: float
    reference_year: int | None
    strata: list[StratumCount]
    verdict: str
    reasons: list[str]
    stress: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["strata"] = [asdict(s) if not isinstance(s, dict) else s for s in self.strata]
        return d


def analyse_figure(
    index: Index,
    candidates: Sequence[Sequence[tuple[int, float]]],
    *,
    encoding: str = "interval",
    reference_year: int | None = None,
    label: str = "figure",
    onset: float = 0.0,
    offset: float = 0.0,
    beam: int = 64,
    match_limit: int = 8,
    stress: Sequence[str] | None = None,
) -> Card:
    """Count one figure across every stratum, with the interval its transcription earns."""
    n_notes = len(candidates)
    paths = enumerate_paths(candidates, beam=beam)
    top1 = top1_path(candidates)
    mean_conf = (
        sum(slot[0][1] for slot in candidates if slot) / n_notes if n_notes else 0.0
    )

    results: list[StratumCount] = []
    for meta in index.strata():
        name = meta["name"]

        def key_for(pitches: tuple[int, ...]) -> str:
            return figure_key(encoding, len(pitches), encode(list(pitches), encoding))

        n_est = estimate_count(paths, lambda p: index.count(key_for(p), name))
        m_est = None
        if reference_year is not None:
            m_est = estimate_count(
                paths, lambda p: index.count_before(key_for(p), name, reference_year)
            )

        top_key = key_for(top1)
        results.append(
            StratumCount(
                stratum=name,
                license=meta["license"],
                provenance=meta["provenance"],
                n_docs=meta["n_docs"],
                n=n_est.as_dict(),
                m=m_est.as_dict() if m_est else None,
                rarity_percentile=index.rarity_percentile(top_key, name),
                earliest=(index.lookup(top_key, name) or {}).get("earliest"),
                undated_in_stratum=index.undated_count(name),
                matches=index.matches(top_key, name, limit=match_limit),
            )
        )

    verdict, reasons = decide(results, mean_conf, paths)
    return Card(
        label=label,
        onset=onset,
        offset=offset,
        n_notes=n_notes,
        encoding=encoding,
        top1_pitches=list(top1),
        mean_confidence=round(mean_conf, 4),
        entropy_bits=round(path_entropy(candidates), 3),
        reading_probability=round(
            max((r.n.get("modal_prob", 0.0) for r in results), default=0.0), 4
        ),
        reference_year=reference_year,
        strata=results,
        verdict=verdict,
        reasons=reasons,
        stress=list(stress or []),
    )


def _denominator_caveat(results: Sequence[StratumCount]) -> str:
    """Describe what the corpus actually covers, rather than asserting it from memory.

    This was hardcoded to "both strata are folk collections" and silently became false
    the moment a popular-music corpus was added. A claim about the denominator has to be
    computed from the denominator.
    """
    total = sum(r.n_docs for r in results)
    folk = [r for r in results if any(
        m.get("tradition", "") in ("folk", "traditional") for m in r.matches
    )] if any(r.matches for r in results) else []
    names = ", ".join(f"{r.stratum} ({r.n_docs:,})" for r in results)
    tail = (
        " Coverage of commercial popular music is thin, so absence here is weak evidence."
        if total < 1_000_000 else ""
    )
    return (
        f"the corpus is {names} — {total:,} works in total."
        + tail
        + " This is the denominator problem, stated rather than hidden."
    )


def decide(results: Sequence[StratumCount], mean_confidence: float, paths) -> tuple[str, list[str]]:
    """Apply the abstention ladder. Order matters: confidence gates everything, because a
    count computed from a reading we do not trust is not evidence of anything."""
    reasons: list[str] = []
    mass = sum(p.prob for p in paths) if paths else 0.0

    if mean_confidence < MIN_MEAN_CONFIDENCE:
        reasons.append(
            f"mean note confidence {mean_confidence:.2f} is below the {MIN_MEAN_CONFIDENCE} floor"
        )
        return "insufficient_confidence", reasons
    if paths and mass < MIN_PATH_MASS:
        reasons.append(f"the beam retained only {mass:.0%} of the reading probability")
        return "insufficient_confidence", reasons

    # A wide interval is NOT grounds to abstain. It is the honest price of carrying
    # transcription uncertainty, and the plan's position is that it gets reported rather
    # than hidden. What does gate the verdict is whether the reading itself is credible.
    modal = max((r.n.get("modal_prob", 0.0) for r in results), default=0.0)
    if modal and modal < MIN_MODAL_PROB:
        reasons.append(
            f"the single best reading carries only {modal:.0%} of the probability, so the "
            "figure itself is not established well enough to count against"
        )
        return "insufficient_confidence", reasons
    for r in results:
        exp, lo, hi = r.n["expected"], r.n["low"], r.n["high"]
        if exp > 0 and (hi - lo) > 2.0 * exp:
            reasons.append(
                f"the interval on N in {r.stratum} ({lo}-{hi}) is wide relative to the "
                "estimate — compounded transcription uncertainty, reported not hidden"
            )
            break

    hits = [r for r in results if r.n["expected"] > 0]
    if not hits:
        reasons.append(
            "the figure appears in none of the indexed works — which is rarity evidence "
            "only to the extent the corpus covers the repertoire in question"
        )
        reasons.append(_denominator_caveat(results))
        return "distinctive", reasons

    # Folk / undated concentration -> the plan's explicit refusal to name an originator.
    folk_traditions = {"folk", "traditional", ""}
    all_folk = all(
        all(m.get("tradition", "") in folk_traditions for m in r.matches) for r in hits if r.matches
    )
    undated_earliest = all(r.earliest is None for r in hits)
    if all_folk and hits:
        reasons.append(
            "every match sits in folk or traditional repertoire, where 'the original' is "
            "not a well-posed question"
        )
        if undated_earliest:
            reasons.append("no matching work in any stratum carries a date")
        return "no_single_originator", reasons

    percentiles = [r.rarity_percentile for r in hits if r.rarity_percentile is not None]
    if percentiles:
        worst = max(percentiles)
        if worst >= COMMONPLACE_MIN_PERCENTILE:
            reasons.append(
                f"at the {worst:.0f}th percentile of figure frequency this is a building "
                "block, not a distinctive figure"
            )
            return "commonplace", reasons
        if worst <= DISTINCTIVE_MAX_PERCENTILE:
            reasons.append(f"sits at the {worst:.0f}th percentile — rarer than most figures of its length")
            return "distinctive", reasons

    reasons.append("frequency sits between the distinctive and commonplace thresholds")
    return "commonplace", reasons
