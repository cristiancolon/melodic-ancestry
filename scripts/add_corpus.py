"""Add a stratum to the index from a directory of MIDI files.

    python3 scripts/add_corpus.py <name> <dir> [--limit N]

Strata are never pooled, so adding one is additive: existing counts are untouched and
the new corpus is reported alongside them with its own licence and provenance.
"""
import sys, pathlib, time, argparse
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from hookline.corpus import STRATA, load_midi_dir
from hookline.index import Index

ap = argparse.ArgumentParser()
ap.add_argument("name")
ap.add_argument("directory")
ap.add_argument("--limit", type=int, default=None)
ap.add_argument("--db", default="data/hookline.db")
ap.add_argument("--tradition", default="popular")
ap.add_argument("--pattern", default="**/*.mid*")
ap.add_argument("--artist-from-parent", action="store_true")
ap.add_argument("--dedupe", action="store_true",
                help="collapse repeat transcriptions of the same song")
ap.add_argument("--max-notes", type=int, default=None,
                help="cap melody length; arrangements are long and the hook recurs early")
args = ap.parse_args()

if args.name not in STRATA:
    sys.exit(f"unknown stratum {args.name!r}. Register it in hookline/corpus.py STRATA first "
             f"— a corpus without a stated licence and provenance is not indexable.")

idx = Index(args.db)
idx.register_stratum(STRATA[args.name])
t0 = time.time()
n = idx.add_documents(
    args.name,
    load_midi_dir(args.directory, args.name, limit=args.limit, tradition=args.tradition,
                  pattern=args.pattern, artist_from_parent=args.artist_from_parent, dedupe=args.dedupe, max_notes=args.max_notes),
    progress=lambda k: print(f"  {k} melodies ({time.time()-t0:.0f}s)", flush=True),
)
print(f"{args.name}: indexed {n} melodies in {time.time()-t0:.0f}s")
print("finalising...")
idx.finalise()
for s in idx.stats()["strata"]:
    print(f"  {s['name']:16} {s['n_docs']:>6} works   {s['license'][:44]}")
