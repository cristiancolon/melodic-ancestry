"""End to end: a file path in, provenance cards out."""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from . import audio, beats as beats_mod, f0 as f0_mod, notes as notes_mod, phrases as phrases_mod, separate as separate_mod
from .encode import estimate_key
from .index import Index
from .verdict import analyse_figure

NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def select_window(notes, lengths: list[int]) -> tuple[int, int] | None:
    """Pick the figure to count: the highest-confidence window at the longest indexed
    length that fits. Longest first because a longer figure is a more specific claim."""
    usable = [n for n in lengths if n <= len(notes)]
    if not usable:
        return None
    n = max(usable)
    best_lo, best_score = 0, -1.0
    for lo in range(len(notes) - n + 1):
        score = sum(x.confidence for x in notes[lo : lo + n]) / n
        if score > best_score:
            best_score, best_lo = score, lo
    return best_lo, n


BASS_DOMINATED_MEDIAN = 55      # MIDI; below this the tracker is following a bass line
BASS_DOMINATED_FRACTION = 0.70  # share of notes under C4


def _lead_signal(x, sr, stem, fmin):
    """Decide whether to separate, and return the signal to transcribe.

    "auto" separates only when a cheap pass over the raw mix looks bass-dominated. That
    matters in both directions: on a real track separation moved the median from MIDI 43
    to 59, but on clean synthesised monophonic audio Demucs has no real timbre to work
    with and made the transcription WORSE. Separating unconditionally would fix the first
    case by breaking the second.
    """
    info = {"requested": stem, "separated": False, "reason": ""}
    if stem in (None, "none", "off"):
        info["reason"] = "separation not requested"
        return x, info
    if not separate_mod.available():
        info["reason"] = "demucs not installed — transcribing the raw mix"
        return x, info

    stems = ("vocals",) if stem in ("auto", "vocals") else tuple(stem.split("+"))
    if stem == "auto":
        probe = notes_mod.extract(f0_mod.track(x[: int(30 * sr)], sr, fmin=fmin))
        if not probe:
            info["reason"] = "no pitched material in the probe pass"
            return x, info
        pitches = [n.pitch for n in probe]
        median = float(np.median(pitches))
        low = sum(1 for p in pitches if p < 60) / len(pitches)
        info["probe"] = {"median_pitch": median, "fraction_below_c4": round(low, 3)}
        if median >= BASS_DOMINATED_MEDIAN and low < BASS_DOMINATED_FRACTION:
            info["reason"] = (
                f"raw mix already sits in melodic register (median MIDI {median:.0f}, "
                f"{low:.0%} below C4) — separation would only add error"
            )
            return x, info
        info["reason"] = (
            f"raw mix looks bass-dominated (median MIDI {median:.0f}, {low:.0%} below C4)"
        )

    lead, sep = separate_mod.separate(x, sr, stems=stems)
    probe_reason = info.get("reason", "")
    info.update(sep)
    info["stems_used"] = list(stems)
    # keep the probe's explanation; separate() clears `reason` on success
    if sep.get("separated") and probe_reason:
        info["reason"] = probe_reason
    return (lead if sep.get("separated") else x), info


def diagnostics(note_list, hooks, skipped: int, lengths: list[int]) -> dict:
    """Say why nothing came back, when nothing comes back.

    A pipeline that returns an empty result silently is worse than one that fails: the
    reader cannot tell "this figure is not prior art" from "no figure was ever formed".
    """
    raw = phrases_mod.segment(note_list)
    flat = sum(1 for p in raw if not phrases_mod.is_melodic(p))
    gaps = [
        note_list[i].onset - note_list[i - 1].offset for i in range(1, len(note_list))
    ]
    median_gap = float(sorted(gaps)[len(gaps) // 2]) if gaps else 0.0
    fragmented = sum(1 for g in gaps if g > phrases_mod.REST_GAP_S)
    note = ""
    if not hooks:
        note = (
            "No phrase of at least "
            f"{phrases_mod.MIN_PHRASE_NOTES} notes was found. The pitch track is too "
            "fragmented to form a melodic line."
        )
    elif skipped and not any(True for _ in ()):
        note = ""
    return {
        "n_notes": len(note_list),
        "phrases_found": len(hooks),
        "phrases_too_short": skipped,
        "phrases_rejected_as_flat": flat,
        "shortest_indexed_length": min(lengths) if lengths else None,
        "median_note_gap_s": round(median_gap, 3),
        "fragmented_gaps": f"{fragmented}/{len(gaps)}" if gaps else "0/0",
        "note": note,
    }


def analyse(
    path: str | Path,
    index: Index,
    reference_year: int | None = None,
    top_hooks: int = 4,
    encoding: str = "interval",
    max_seconds: float = 90.0,
    fmin: float = 65.0,
    stem: str | None = "auto",
    keep_audio: bool = False,
) -> dict:
    """Decode, transcribe, find hooks, and count each one against every stratum.

    `fmin` is the floor of the pitch search, and on a full mix it is the single most
    consequential setting. With no source separation available, YIN locks onto the
    strongest periodicity in the signal, which in commercial pop is the bass: on a real
    track it put 89% of detected notes below C4. Raising the floor is a crude stand-in
    for separating the lead, and it is crude -- it cannot distinguish the vocal from a
    bass harmonic in the same register, so a confident reading here is not evidence that
    the melody was recovered.
    """
    t0 = time.time()
    x, sr = audio.load(path)
    truncated = False
    if len(x) > max_seconds * sr:
        x, truncated = x[: int(max_seconds * sr)], True

    signal, sep_info = _lead_signal(x, sr, stem, fmin)
    track = f0_mod.track(signal, sr, fmin=fmin)
    onsets = beats_mod.onset_times(signal, sr)
    note_list = notes_mod.extract(track, onset_times=onsets)
    beat = beats_mod.estimate(signal, sr)

    if not note_list:
        return {
            "file": Path(path).name,
            "duration": round(len(x) / sr, 2),
            "error": "no pitched material was detected in this file",
            "notes": [],
            "cards": [],
            "elapsed": round(time.time() - t0, 2),
        }

    onsets = [n.onset for n in note_list]
    stress_labels = beats_mod.stress(onsets, beat)
    tonic, is_major = estimate_key(notes_mod.pitches(note_list))

    lengths = index.indexed_lengths()
    hooks = phrases_mod.find_hooks(note_list, top=top_hooks)
    cards = []
    skipped = 0
    for rank, ph in enumerate(hooks, 1):
        ph.stress = stress_labels[ph.start : ph.end]
        window = select_window(ph.notes, lengths)
        if window is None:
            skipped += 1
            continue
        lo, n = window
        sub = ph.notes[lo : lo + n]
        card = analyse_figure(
            index,
            [nt.candidates for nt in sub],
            encoding=encoding,
            reference_year=reference_year,
            label=f"Hook {rank} — {n} notes from {sub[0].onset:.1f}s",
            onset=sub[0].onset,
            offset=sub[-1].offset,
            stress=ph.stress[lo : lo + n],
        )
        d = card.to_dict()
        d["repetitions"] = ph.repetitions
        d["hook_score"] = round(ph.hook_score, 3)
        d["phrase_notes"] = len(ph.notes)
        d["pitch_names"] = [f"{NOTE_NAMES[p.pitch % 12]}{p.pitch // 12 - 1}" for p in sub]
        cards.append(d)

    result = {
        "file": Path(path).name,
        "duration": round(len(x) / sr, 2),
        "truncated": truncated,
        "sample_rate": sr,
        "tempo_bpm": round(beat.tempo_bpm, 1),
        "tempo_confidence": round(beat.confidence, 3),
        "key": f"{NOTE_NAMES[tonic]} {'major' if is_major else 'minor'}",
        "n_notes": len(note_list),
        "mean_confidence": round(notes_mod.mean_confidence(note_list), 4),
        "reference_year": reference_year,
        "fmin": fmin,
        "separation": sep_info,
        "notes": [
            {
                "onset": round(n.onset, 3),
                "duration": round(n.duration, 3),
                "pitch": n.pitch,
                "name": f"{NOTE_NAMES[n.pitch % 12]}{n.pitch // 12 - 1}",
                "confidence": round(n.confidence, 3),
                "candidates": [[int(p), round(w, 3)] for p, w in n.candidates],
                "stress": stress_labels[i] if i < len(stress_labels) else "ornamental",
            }
            for i, n in enumerate(note_list)
        ],
        "cards": cards,
        "diagnostics": diagnostics(note_list, hooks, skipped, lengths),
        "index": {"strata": index.strata()},
        "elapsed": round(time.time() - t0, 2),
    }
    if keep_audio:
        # underscore keys are stripped before serialisation; they carry raw arrays
        result["_mix"] = x
        result["_lead"] = signal
        result["_sr"] = sr
    return result


def analyse_pitches(
    pitches: list[int],
    index: Index,
    reference_year: int | None = None,
    encoding: str = "interval",
    label: str = "symbolic query",
) -> dict:
    """The symbolic path: no transcription, so every note posterior is 1.0.

    This is the high-confidence stratum of input, and the honest fallback whenever the
    audio path abstains for lack of confidence.
    """
    candidates = [[(int(p), 1.0)] for p in pitches]
    card = analyse_figure(
        index, candidates, encoding=encoding, reference_year=reference_year, label=label
    )
    d = card.to_dict()
    d["pitch_names"] = [f"{NOTE_NAMES[p % 12]}{p // 12 - 1}" for p in pitches]
    return {
        "file": label,
        "symbolic": True,
        "n_notes": len(pitches),
        "mean_confidence": 1.0,
        "reference_year": reference_year,
        "cards": [d],
        "index": {"strata": index.strata()},
    }
