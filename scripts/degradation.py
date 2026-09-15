"""The compounding curve: retrieval accuracy as the audio degrades.

A single clean-audio number cannot settle whether carrying transcription uncertainty
buys anything, because on clean audio the top-1 reading is already right and there is
nothing to recover. The question is what happens as the signal gets worse -- which is
the shape the literature does not report for commercial pop.

Degradation here is additive noise and vibrato on a synthesised monophonic line. That is
still not a real mix: no percussion, no competing instruments, no reverb. Read these as
the kind end of the range.
"""
import sys, pathlib, json, gzip, collections, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from hookline import beats as B, f0 as F, notes as N, synth, phrases as P
from hookline.encode import encode, figure_key
from hookline.index import Index
from hookline.lattice import enumerate_paths, top1_path
from hookline.pipeline import select_window

TRIALS = int(sys.argv[1]) if len(sys.argv) > 1 else 100
STRATUM, ENCODING = "mtc-fs-inst", "interval"
idx = Index("data/hookline.db")
LENGTHS = idx.indexed_lengths(STRATUM)

indexed = {r[0] for r in idx.conn.execute(
    "SELECT ext_id FROM documents WHERE stratum=?", (STRATUM,)).fetchall()}
fam_of, members = {}, collections.defaultdict(list)
with gzip.open("data/mtc.jsonl.gz", "rt", encoding="utf-8") as fh:
    for line in fh:
        r = json.loads(line)
        rid, fam = str(r.get("id")), r.get("tunefamily")
        if fam and rid in indexed:
            fam_of[rid] = fam
            members[fam].append((rid, [p for p in r["features"]["midipitch"] if isinstance(p, int)],
                                 r["features"]["duration"]))
pool = [(f, m) for f, m in sorted(members.items()) if len(m) >= 2][:TRIALS]


def hits(fkey, src, fam):
    ids = {r[0] for r in idx.conn.execute(
        "SELECT d.ext_id FROM postings p JOIN documents d ON d.doc_id=p.doc_id "
        "JOIN figures f ON f.figure_id=p.figure_id WHERE f.fkey=? AND f.stratum=?",
        (fkey, STRATUM)).fetchall()}
    return (src in ids), any(fam_of.get(i) == fam and i != src for i in ids)


def key_of(p):
    return figure_key(ENCODING, len(p), encode(list(p), ENCODING))


CONDITIONS = [(0.0, 0.0), (0.15, 0.0), (0.35, 0.0), (0.35, 45.0), (0.6, 45.0), (0.9, 60.0)]
print(f"{'noise':>6} {'vib¢':>5} {'meanConf':>9} {'top1 self':>10} {'latt self':>10} "
      f"{'top1 fam':>9} {'latt fam':>9} {'gain':>6}")
rows = []
for noise, vib in CONDITIONS:
    t0 = time.time()
    s1 = collections.Counter(); confs = []
    for fam, ms in pool:
        src, pitches, durs = ms[0]
        if len(pitches) < max(LENGTHS) + 2:
            continue
        x = synth.render(pitches[:40], [min(max(float(d) * 0.34, 0.16), 0.7) for d in durs[:40]],
                         noise=noise, vibrato_cents=vib, seed=hash(src) % 9999)
        ns = N.extract(F.track(x, synth.SR), onset_times=B.onset_times(x, synth.SR))
        if not ns:
            s1["n"] += 1
            continue
        confs.append(N.mean_confidence(ns))
        a1s = a1f = als = alf = False
        for ph in P.find_hooks(ns, top=3):
            win = select_window(ph.notes, LENGTHS)
            if win is None:
                continue
            lo, nn = win
            cands = [q.candidates for q in ph.notes[lo:lo + nn]]
            s, f = hits(key_of(top1_path(cands)), src, fam)
            a1s, a1f = a1s or s, a1f or f
            for path in enumerate_paths(cands, beam=48):
                s, f = hits(key_of(path.pitches), src, fam)
                als, alf = als or s, alf or f
                if als and alf:
                    break
        s1["n"] += 1
        s1["a1s"] += a1s; s1["a1f"] += a1f; s1["als"] += als; s1["alf"] += alf
    n = s1["n"] or 1
    mc = sum(confs) / len(confs) if confs else 0.0
    gain = (s1["als"] - s1["a1s"]) / n
    print(f"{noise:6.2f} {vib:5.0f} {mc:9.3f} {s1['a1s']/n:9.1%} {s1['als']/n:9.1%} "
          f"{s1['a1f']/n:8.1%} {s1['alf']/n:8.1%} {gain:+6.1%}  ({time.time()-t0:.0f}s)", flush=True)
    rows.append({"noise": noise, "vibrato": vib, "mean_conf": round(mc, 4), "n": n,
                 "top1_self": s1["a1s"], "lattice_self": s1["als"],
                 "top1_family": s1["a1f"], "lattice_family": s1["alf"]})
json.dump(rows, open("data/degradation.json", "w"), indent=2)
print("\nwritten to data/degradation.json")
