"""Tests for the invariants that carry the project's claims.

These are not coverage tests. Each one pins a property that, if it broke silently, would
make the output dishonest rather than merely wrong.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import numpy as np

from hookline import beats, encode, f0, notes, phrases, synth
from hookline.index import Document, Index, Stratum
from hookline.lattice import enumerate_paths, estimate_count, path_entropy, top1_path
from hookline.verdict import analyse_figure

FAIL = []


def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  — {detail}" if detail and not cond else ""))
    if not cond:
        FAIL.append(name)


print("encodings")
p = [60, 62, 64, 62, 60]
check("interval is transposition invariant",
      encode.encode(p, "interval") == encode.encode([x + 7 for x in p], "interval"))
check("contour is transposition invariant",
      encode.encode(p, "contour_gross") == encode.encode([x + 7 for x in p], "contour_gross"))
check("pitch encoding is NOT transposition invariant",
      encode.encode(p, "pitch") != encode.encode([x + 7 for x in p], "pitch"))
check("n counts notes, intervals are n-1",
      len(encode.encode(p, "interval")) == len(p) - 1)
check("figure keys separate encodings",
      encode.figure_key("interval", 5, (1, 2)) != encode.figure_key("pitch", 5, (1, 2)))

print("\nlattice")
c = [[(60, 0.6), (48, 0.4)], [(62, 1.0)], [(64, 0.5), (63, 0.5)]]
paths = enumerate_paths(c)
check("paths enumerate the product space", len(paths) == 4, f"got {len(paths)}")
check("path probabilities sum to 1", abs(sum(x.prob for x in paths) - 1.0) < 1e-9)
check("top1 takes the leading candidate", top1_path(c) == (60, 62, 64))
est = estimate_count(paths, lambda q: {(60, 62, 64): 10}.get(q, 0))
check("E[N] marginalises over readings", abs(est.expected - 3.0) < 1e-6, f"{est.expected}")
check("top-1 is reported alongside E[N]", est.top1 == 10)
check("variance is non-negative", est.variance >= 0)
certain = enumerate_paths([[(60, 1.0)], [(62, 1.0)]])
e2 = estimate_count(certain, lambda q: 7)
check("a certain reading has zero variance", e2.variance == 0 and e2.expected == 7)
check("entropy is zero when certain", path_entropy([[(60, 1.0)]]) == 0)
check("beam caps the path count", len(enumerate_paths([[(i, 1 / 3) for i in range(3)]] * 8, beam=16)) <= 16)

print("\naudio front end")
truth = [64, 60, 57, 55, 60, 60, 62, 60, 64, 65]
x = synth.render(truth, [0.34] * len(truth))
tr = f0.track(x, synth.SR)
ns = notes.extract(tr, onset_times=beats.onset_times(x, synth.SR))
check("note count recovered", len(ns) == len(truth), f"{len(ns)} vs {len(truth)}")
check("pitch sequence recovered", notes.pitches(ns) == truth, str(notes.pitches(ns)))
check("repeated pitches are not merged", notes.pitches(ns).count(60) == truth.count(60))
check("every note carries ranked candidates", all(len(n.candidates) >= 1 for n in ns))
check("candidate posteriors normalise",
      all(abs(sum(w for _, w in n.candidates) - 1.0) < 1e-6 for n in ns))
check("candidates are rank ordered",
      all(all(n.candidates[i][1] >= n.candidates[i + 1][1] for i in range(len(n.candidates) - 1))
          for n in ns))
b = beats.estimate(x, synth.SR)
check("tempo is in a sane range", 40 < b.tempo_bpm < 260, f"{b.tempo_bpm}")
check("hooks are found", len(phrases.find_hooks(ns)) >= 1)

print("\nMIDI melody extraction")
import tempfile
from hookline.midi import MidiNote, melody, skyline, score_track


def _write_midi(path, spec):
    import mido
    mid = mido.MidiFile(ticks_per_beat=480)
    for name, pitches, chan, chord in spec:
        tr = mido.MidiTrack()
        tr.append(mido.MetaMessage("track_name", name=name))
        for p in pitches:
            group = [p, p + 4, p + 7] if chord else [p]
            for q in group:
                tr.append(mido.Message("note_on", note=q, velocity=80, channel=chan, time=0))
            tr.append(mido.Message("note_off", note=group[0], velocity=0, channel=chan, time=240))
            for q in group[1:]:
                tr.append(mido.Message("note_off", note=q, velocity=0, channel=chan, time=0))
        mid.tracks.append(tr)
    mid.save(str(path))


tune = [72, 74, 76, 74, 72, 71, 69, 71, 72, 76, 74, 72, 71, 69]
tmpdir = pathlib.Path(tempfile.mkdtemp())
_write_midi(tmpdir / "a.mid", [("Bass", [p - 24 for p in tune], 1, False),
                               ("Chords", [p - 12 for p in tune], 2, True),
                               ("Melody", tune, 0, False)])
check("melody track beats bass and chords", melody(tmpdir / "a.mid") == tune)

# no helpful names: register and monophony must carry the decision
_write_midi(tmpdir / "b.mid", [("", [p - 24 for p in tune], 1, False),
                               ("", tune, 0, False)])
check("unnamed tracks resolved by register", melody(tmpdir / "b.mid") == tune)

check("skyline keeps the top voice",
      [n.pitch for n in skyline([MidiNote(60, 0, 2, 0), MidiNote(64, 0, 2, 0)])] == [64])
check("skyline truncates on an upward move",
      [n.pitch for n in skyline([MidiNote(60, 0, 4, 0), MidiNote(67, 1, 3, 0)])] == [60, 67])
check("a bass-register track is penalised",
      score_track([MidiNote(40, i, i + 1, 0) for i in range(20)], "") <
      score_track([MidiNote(72, i, i + 1, 0) for i in range(20)], ""))
check("a named bass track loses to an unnamed one",
      score_track([MidiNote(70, i, i + 1, 0) for i in range(20)], "bass") <
      score_track([MidiNote(70, i, i + 1, 0) for i in range(20)], ""))
check("too few notes is not a melody", melody(tmpdir / "missing.mid") == [])

# An accompaniment-only file must be rejected, not indexed as if it were a tune.
# Nottingham ships a chords/ directory; 1,005 of its files were indexed as melodies
# before this guard existed.
_write_midi(tmpdir / "chords.mid", [("", [40, 45, 47, 40, 45, 47, 40, 45, 47,
                                          40, 45, 47, 40, 45], 0, True)])
check("an accompaniment-only file is rejected", melody(tmpdir / "chords.mid") == [],
      str(melody(tmpdir / "chords.mid"))[:60])

print("\nindex and stratification")
db = pathlib.Path("data/_test_index.db")
db.unlink(missing_ok=True)
idx = Index(db)
idx.register_stratum(Stratum("alpha", "test", "CC0", "synthetic"))
idx.register_stratum(Stratum("beta", "test", "CC0", "synthetic"))
idx.add_documents("alpha", [
    Document("a1", "Dated work", [60, 62, 64, 65, 67, 69, 71, 72, 74], year=1900, tradition="pop"),
    Document("a2", "Undated work", [60, 62, 64, 65, 67, 69, 71, 72, 74], year=None, tradition="pop"),
], n_range=(5,), encodings=("interval",))
idx.add_documents("beta", [
    Document("b1", "Other stratum", [60, 62, 64, 65, 67, 69, 71, 72, 74], year=1800, tradition="folk"),
], n_range=(5,), encodings=("interval",))
idx.finalise()

fk = encode.figure_key("interval", 5, encode.encode([60, 62, 64, 65, 67], "interval"))
check("counts are per stratum, not pooled",
      idx.count(fk, "alpha") == 2 and idx.count(fk, "beta") == 1)
check("undated works never enter a predates count", idx.count_before(fk, "alpha", 1950) == 1)
check("undated works are reported separately", idx.undated_count("alpha") == 1)
check("earliest year ignores undated", (idx.lookup(fk, "alpha") or {})["earliest"] == 1900)
check("indexed lengths are reported", idx.indexed_lengths() == [5])
check("absent figures count zero, not error",
      idx.count(encode.figure_key("interval", 5, (99, 99, 99, 99)), "alpha") == 0)
again = idx.add_documents("alpha", [
    Document("a1", "Dated work", [60, 62, 64, 65, 67, 69, 71, 72, 74], year=1900, tradition="pop"),
], n_range=(5,), encodings=("interval",))
idx.finalise()
check("re-indexing a work does not count it twice",
      again == 0 and idx.count(fk, "alpha") == 2
      and next(s["n_docs"] for s in idx.strata() if s["name"] == "alpha") == 2,
      f"added {again}, N={idx.count(fk, 'alpha')}")

print("\nverdicts and abstention")
card = analyse_figure(idx, [[(p, 1.0)] for p in [60, 62, 64, 65, 67]],
                      reference_year=1950, encoding="interval")
check("every stratum appears in the card", len(card.strata) == 2)
check("each stratum states its licence", all(s.license for s in card.strata))
check("each stratum states its denominator", all(s.provenance for s in card.strata))
check("verdict is one of the four", card.verdict in
      ("distinctive", "commonplace", "no_single_originator", "insufficient_confidence"))
check("a verdict always carries reasons", len(card.reasons) >= 1)
low = analyse_figure(idx, [[(60, 0.2), (61, 0.4), (62, 0.4)]] * 5, encoding="interval")
check("low confidence abstains", low.verdict == "insufficient_confidence", low.verdict)
check("no similarity score is ever emitted",
      not any("similarity" in k for k in card.to_dict()))
idx.close()
db.unlink(missing_ok=True)
for suffix in ("-wal", "-shm"):
    pathlib.Path(str(db) + suffix).unlink(missing_ok=True)

print(f"\n{'ALL PASS' if not FAIL else str(len(FAIL)) + ' FAILED: ' + ', '.join(FAIL)}")
sys.exit(1 if FAIL else 0)
