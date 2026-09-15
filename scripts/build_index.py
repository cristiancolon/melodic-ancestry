import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
"""Build the Hookline index from the downloaded corpora."""
import sys, time
from hookline.corpus import STRATA, load_jsonl
from hookline.index import Index

limit = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
idx = Index("data/hookline.db")
t0 = time.time()
for name, src in (("mtc-fs-inst", "data/mtc.jsonl.gz"), ("essen", "data/essen.jsonl.gz")):
    idx.register_stratum(STRATA[name])
    n = idx.add_documents(
        name, load_jsonl(src, name, limit=limit),
        progress=lambda k, s=name: print(f"  {s}: {k} docs  ({time.time()-t0:.0f}s)", flush=True),
    )
    print(f"{name}: indexed {n} documents", flush=True)
print("finalising (df + earliest)...", flush=True)
idx.finalise()
st = idx.stats()
print(f"DONE in {time.time()-t0:.0f}s: {st['documents']} docs, {st['figures']} figures, {st['postings']} postings")
for s in st["strata"]:
    print(f"  {s['name']:14} {s['n_docs']:6} docs   {s['license'][:40]}")
