"""Gate 3: does rarity separate meaningful melodic figures from arbitrary ones?

A prior-art count is only evidence if figures differ in how common they are. If every
figure a court would ask about turns out to be a building block, the count is still an
honest denominator but the wider ambition is dead.

Ground truth here is tune-family membership again: a figure that recurs across
independent members of the SAME family is musicologically meaningful material, not an
artefact. The comparison is against figures drawn from the corpus at random.
"""
import sys, pathlib, json, gzip, collections, random
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from hookline.encode import encode, figure_key
from hookline.index import Index

ENCODING, N = "interval", 9
idx = Index("data/hookline.db")
random.seed(7)


def df(fkey, stratum):
    row = idx.lookup(fkey, stratum)
    return row["df"] if row else 0


def pct(values, q):
    if not values:
        return 0
    s = sorted(values)
    return s[min(int(q * len(s)), len(s) - 1)]


print(f"figure length {N} notes, {ENCODING} encoding\n")
for stratum in [s["name"] for s in idx.strata()]:
    # every figure type in this stratum, with its document frequency
    rows = idx.conn.execute(
        "SELECT df FROM figures WHERE stratum=? AND encoding=? AND n=?",
        (stratum, ENCODING, N)).fetchall()
    dfs = [r[0] for r in rows]
    if not dfs:
        print(f"{stratum}: no figures at n={N}")
        continue
    singles = sum(1 for d in dfs if d == 1)
    print(f"{stratum}  ({len(dfs):,} distinct figures)")
    print(f"   appear in exactly one work : {singles/len(dfs):6.1%}")
    print(f"   median / p90 / p99 / max df: {pct(dfs,.5)} / {pct(dfs,.9)} / {pct(dfs,.99)} / {max(dfs)}")

# --- the separation test, on the corpus that carries family labels
STRAT = "mtc-fs-inst"
indexed = {r[0] for r in idx.conn.execute(
    "SELECT ext_id FROM documents WHERE stratum=?", (STRAT,)).fetchall()}
fams = collections.defaultdict(list)
with gzip.open("data/mtc.jsonl.gz", "rt", encoding="utf-8") as fh:
    for line in fh:
        r = json.loads(line)
        rid, fam = str(r.get("id")), r.get("tunefamily")
        if fam and rid in indexed:
            fams[fam].append([p for p in r["features"]["midipitch"] if isinstance(p, int)])

shared, arbitrary = [], []
for fam, members in fams.items():
    if len(members) < 2:
        continue
    a, b = members[0], members[1]
    grams_b = {tuple(encode(b[i:i + N], ENCODING)) for i in range(max(len(b) - N + 1, 0))}
    for i in range(max(len(a) - N + 1, 0)):
        g = tuple(encode(a[i:i + N], ENCODING))
        if g in grams_b:                       # this figure survives across the family
            shared.append(df(figure_key(ENCODING, N, g), STRAT))
    if len(shared) > 4000:
        break

all_docs = [m for ms in fams.values() for m in ms]
for _ in range(min(len(shared), 4000)):
    mel = random.choice(all_docs)
    if len(mel) < N + 1:
        continue
    i = random.randrange(len(mel) - N + 1)
    arbitrary.append(df(figure_key(ENCODING, N, tuple(encode(mel[i:i + N], ENCODING))), STRAT))

print(f"\n--- separation test on {STRAT} ---")
print(f"{'':28} {'n':>6} {'median':>7} {'p90':>6} {'mean':>7}")
for label, vals in (("shared across a tune family", shared), ("drawn at random", arbitrary)):
    if vals:
        print(f"{label:28} {len(vals):6} {pct(vals,.5):7} {pct(vals,.9):6} {sum(vals)/len(vals):7.1f}")
if shared and arbitrary:
    ms, ma = pct(shared, .5), pct(arbitrary, .5)
    print(f"\nfamily-shared figures are {'MORE' if ms > ma else 'LESS'} common than arbitrary ones "
          f"(median {ms} vs {ma})")
    print("Read carefully: this measures whether *recurring* material is distinguishable by "
          "frequency, not whether a court's disputed figure would be.")
json.dump({"shared_median": pct(shared,.5), "arbitrary_median": pct(arbitrary,.5),
           "n_shared": len(shared), "n_arbitrary": len(arbitrary)},
          open("data/rarity_gate3.json","w"), indent=2)
