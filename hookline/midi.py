"""Extract a single melodic line from a MIDI file.

Folk corpora ship one monophonic melody per file. Popular-music MIDI does not: it is a
full arrangement, and picking the wrong track indexes a bass line or a pad as if it were
the tune. That is the same failure the audio front end had, arriving from a different
direction, and it is worth as much care.

Track selection is scored rather than guessed, then the winning track is forced
monophonic by a skyline pass -- at any instant, the highest sounding note is the melody.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DRUM_CHANNEL = 9
MELODY_NAMES = ("melody", "lead", "vocal", "voice", "sing", "tune", "solo", "theme")
AVOID_NAMES = ("bass", "drum", "perc", "kick", "chord", "pad", "string", "harmony", "accomp")


@dataclass
class MidiNote:
    pitch: int
    start: float   # beats
    end: float
    track: int


def _events(path: Path) -> tuple[list[list[MidiNote]], list[str]]:
    import mido

    mid = mido.MidiFile(str(path))
    tpb = mid.ticks_per_beat or 480
    tracks: list[list[MidiNote]] = []
    names: list[str] = []

    for ti, track in enumerate(mid.tracks):
        now = 0
        pending: dict[tuple[int, int], int] = {}
        notes: list[MidiNote] = []
        name = ""
        for msg in track:
            now += msg.time
            if msg.type == "track_name":
                name = str(msg.name).lower()
            elif msg.type == "note_on" and msg.velocity > 0:
                if getattr(msg, "channel", 0) == DRUM_CHANNEL:
                    continue
                pending[(msg.channel, msg.note)] = now
            elif msg.type in ("note_off",) or (msg.type == "note_on" and msg.velocity == 0):
                if getattr(msg, "channel", 0) == DRUM_CHANNEL:
                    continue
                key = (msg.channel, msg.note)
                if key in pending:
                    start = pending.pop(key)
                    if now > start:
                        notes.append(MidiNote(msg.note, start / tpb, now / tpb, ti))
        tracks.append(sorted(notes, key=lambda n: (n.start, -n.pitch)))
        names.append(name)
    return tracks, names


def _polyphony(notes: list[MidiNote]) -> float:
    """Mean number of notes sounding at each onset. 1.0 is a true single line."""
    if not notes:
        return 0.0
    overlaps = 0
    for i, n in enumerate(notes):
        for m in notes[i + 1 : i + 12]:
            if m.start >= n.end:
                break
            overlaps += 1
    return 1.0 + overlaps / len(notes)


def score_track(notes: list[MidiNote], name: str) -> float:
    """How much this track looks like the tune.

    Deliberately not just "highest average pitch": a piccolo counter-line would win that.
    Name evidence dominates when present, because a human labelled it.
    """
    if len(notes) < 12:
        return float("-inf")
    mean_pitch = sum(n.pitch for n in notes) / len(notes)
    poly = _polyphony(notes)

    score = 0.0
    score += 40.0 if any(k in name for k in MELODY_NAMES) else 0.0
    score -= 40.0 if any(k in name for k in AVOID_NAMES) else 0.0
    # melodies sit in a singable band; punish bass register hard
    score += 18.0 - abs(mean_pitch - 70.0) * 0.9
    score -= (poly - 1.0) * 14.0           # chords are accompaniment
    score += min(len(notes), 400) / 100.0  # prefer tracks with real content
    return score


def skyline(notes: list[MidiNote]) -> list[MidiNote]:
    """Force monophony: at any instant keep only the highest sounding note."""
    out: list[MidiNote] = []
    for n in sorted(notes, key=lambda x: (x.start, -x.pitch)):
        if out and n.start < out[-1].end - 1e-6:
            if n.pitch <= out[-1].pitch:
                continue          # lower voice under a sounding melody note
            out[-1].end = n.start  # melody moved up; truncate the previous note
            if out[-1].end - out[-1].start < 1e-6:
                out.pop()
        out.append(MidiNote(n.pitch, n.start, n.end, n.track))
    return out


# A track scoring below this does not look like a tune at all. Chord-only and bass-only
# files exist in real corpora (Nottingham ships a whole `chords/` directory), and without
# a floor they are indexed as melodies: 1,005 of 3,073 Nottingham "melodies" were
# accompaniment before this check existed.
MIN_MELODY_SCORE = 0.0


def melody(path: str | Path, min_notes: int = 12,
           min_score: float = MIN_MELODY_SCORE) -> list[int]:
    """The melodic line of a MIDI file as a pitch sequence, or [] if none is credible."""
    try:
        tracks, names = _events(Path(path))
    except Exception:
        return []
    if not tracks:
        return []

    scored = [(score_track(t, n), t) for t, n in zip(tracks, names)]
    best_score, best = max(scored, key=lambda s: s[0])
    if best_score == float("-inf"):
        # single-track file with everything on one channel: skyline the lot
        merged = [n for t in tracks for n in t]
        if len(merged) < min_notes:
            return []
        best, best_score = merged, score_track(merged, "")
    if best_score < min_score:
        return []  # no track here looks like a tune — an accompaniment-only file

    line = skyline(best)
    return [n.pitch for n in line] if len(line) >= min_notes else []
