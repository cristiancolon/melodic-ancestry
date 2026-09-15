"""Known-item retrieval over tune families — the evaluation protocol the plan argues for.

No litigation labels. The ground truth is the Meertens tune-family assignment: melodies
in one family are established variants of each other, decided by musicologists and
entirely independent of any court record. The metric is whether a query recovers a
family sibling, and at what rank.

Three conditions isolate where accuracy is lost:
  symbolic     the true notes, no transcription  -- the ceiling
  audio top-1  synthesised, transcribed, single best reading
  audio lattice  same audio, posterior-weighted over readings

symbolic minus audio is the compounding cost. lattice minus top-1 is what carrying the
uncertainty buys back. Synthetic audio is the kind end of the range, so every number
here is an upper bound on real-mix performance and must be read as one.
"""
import sys, pathlib, json, gzip, time, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from hookline import beats as beats_mod, f0 as f0_mod, notes as notes_mod, synth, phrases as phrases_mod
from hookline.encode import encode, figure_key
from hookline.index import Index
from hookline.lattice import enumerate_paths, top1_path
from hookline.pipeline import select_window

N_TRIALS = int(sys.argv[1]) if len(sys.argv) > 1 else 120
STRATUM, ENCODING = "mtc-fs-inst", "interval"
idx = Index("data/hookline.db")
LENGTHS = idx.indexed_lengths(STRATUM)

# ext_id -> family, restricted to the ids actually indexed
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

candidates = [(fam, ms) for fam, ms in members.items() if len(ms) >= 2]
candidates.sort(key=lambda kv: kv[0])
print(f"{len(indexed)} indexed works, {len(candidates)} tune families with 2+ indexed members")


def sibling_hit(fkey, source_id, family):
    """Does the posting list contain a DIFFERENT member of the same family?"""
    rows = idx.conn.execute(
        "SELECT d.ext_id FROM postings p JOIN documents d ON d.doc_id=p.doc_id "
        "JOIN figures f ON f.figure_id=p.figure_id WHERE f.fkey=? AND f.stratum=?",
        (fkey, STRATUM)).fetchall()
    ids = {r[0] for r in rows}
    return (source_id in ids), any(fam_of.get(i) == family and i != source_id for i in ids)


def key_of(pitches):
    return figure_key(ENCODING, len(pitches), encode(list(pitches), ENCODING))


score = collections.Counter()
attempted = 0
t0 = time.time()
for fam, ms in candidates:
    if attempted >= N_TRIALS:
        break
    src_id, pitches, durs = ms[0]
    if len(pitches) < max(LENGTHS) + 2:
        continue
    attempted += 1

    n = max(LENGTHS)
    # --- symbolic ceiling: the true notes, best window by nothing but position
    sym_self = sym_fam = False
    for lo in range(min(len(pitches) - n + 1, 8)):
        s, f = sibling_hit(key_of(pitches[lo:lo + n]), src_id, fam)
        sym_self, sym_fam = sym_self or s, sym_fam or f
    score["sym_self"] += sym_self; score["sym_fam"] += sym_fam

    # --- audio conditions
    x = synth.render(pitches[:40], [min(max(float(d) * 0.34, 0.16), 0.7) for d in durs[:40]])
    tracked = f0_mod.track(x, synth.SR)
    ns = notes_mod.extract(tracked, onset_times=beats_mod.onset_times(x, synth.SR))
    hooks = phrases_mod.find_hooks(ns, top=3)
    a1_self = a1_fam = al_self = al_fam = False
    for ph in hooks:
        win = select_window(ph.notes, LENGTHS)
        if win is None:
            continue
        lo, nn = win
        sub = ph.notes[lo:lo + nn]
        cands = [q.candidates for q in sub]
        s, f = sibling_hit(key_of(top1_path(cands)), src_id, fam)
        a1_self, a1_fam = a1_self or s, a1_fam or f
        for path in enumerate_paths(cands, beam=48):
            s, f = sibling_hit(key_of(path.pitches), src_id, fam)
            al_self, al_fam = al_self or s, al_fam or f
            if al_self and al_fam:
                break
    score["a1_self"] += a1_self; score["a1_fam"] += a1_fam
    score["al_self"] += al_self; score["al_fam"] += al_fam

    if attempted % 20 == 0:
        print(f"  {attempted} trials ({time.time()-t0:.0f}s)", flush=True)

n = attempted or 1
print(f"\n=== known-item retrieval, n={n} queries, {time.time()-t0:.0f}s ===")
print(f"{'condition':22} {'self-retrieval':>15} {'family sibling':>16}")
for key, name in (("sym", "symbolic (ceiling)"), ("a1", "audio, top-1"), ("al", "audio, lattice")):
    print(f"{name:22} {score[key+'_self']/n:14.1%} {score[key+'_fam']/n:15.1%}"
          f"   ({score[key+'_self']}/{n}, {score[key+'_fam']}/{n})")
drop = (score["sym_self"] - score["a1_self"]) / n
gain = (score["al_self"] - score["a1_self"]) / n
print(f"\ncompounding cost, symbolic -> audio top-1 : {drop:+.1%}")
print(f"recovered by the lattice                 : {gain:+.1%}")
json.dump({"n": n, "counts": dict(score)}, open("data/eval_results.json", "w"), indent=2)
