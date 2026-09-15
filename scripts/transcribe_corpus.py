"""Build a stratum by transcribing audio — the plan's S2.

This is the honest route to a pop-weighted denominator: rather than indexing scraped
MIDI of copyrighted songs, run our own transcription over audio we are licensed to hold,
and carry the resulting error as a property of the stratum.

The output is NOT comparable to a clean symbolic corpus and must never be pooled with
one. Every melody here has been through a pipeline whose measured note-level behaviour
is: exact pitch sequences on clean monophonic synthesis, and a bass-lock failure on full
mixes that separation only partly repairs. That is why the stratum records its own
transcription statistics alongside the counts.

    python3 scripts/transcribe_corpus.py <stratum> <audio_dir> [--limit N]
"""
import sys, pathlib, time, json, argparse
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import numpy as np

from hookline import audio as audio_mod, beats, f0, notes as notes_mod, separate
from hookline.corpus import STRATA
from hookline.index import Document, Index

ap = argparse.ArgumentParser()
ap.add_argument("name")
ap.add_argument("directory")
ap.add_argument("--limit", type=int, default=None)
ap.add_argument("--db", default="data/hookline.db")
ap.add_argument("--fmin", type=float, default=150.0)
ap.add_argument("--seconds", type=float, default=60.0)
ap.add_argument("--metadata", default=None,
                help="JSON mapping filename -> {title, artist, year}; without it works are UNDATED")
args = ap.parse_args()

if args.name not in STRATA:
    sys.exit(f"unknown stratum {args.name!r}; register it in hookline/corpus.py first")

meta = json.load(open(args.metadata)) if args.metadata else {}
root = pathlib.Path(args.directory)
paths = sorted(p for p in root.glob("**/*") if p.suffix.lower() in
               (".mp3", ".wav", ".flac", ".ogg", ".m4a"))
if args.limit:
    paths = paths[: args.limit]
print(f"{len(paths)} audio files under {root}")

stats = {"attempted": 0, "transcribed": 0, "too_short": 0, "failed": 0,
         "confidences": [], "separated": 0}


def melodies():
    for path in paths:
        stats["attempted"] += 1
        try:
            x, sr = audio_mod.load(path)
            x = x[: int(args.seconds * sr)]
            probe = notes_mod.extract(f0.track(x[: int(20 * sr)], sr, fmin=args.fmin))
            signal = x
            if probe:
                ps = [n.pitch for n in probe]
                if float(np.median(ps)) < 55 or sum(1 for p in ps if p < 60) / len(ps) > 0.7:
                    signal, info = separate.separate(x, sr, stems=("vocals",))
                    stats["separated"] += int(bool(info.get("separated")))
            ns = notes_mod.extract(f0.track(signal, sr, fmin=args.fmin),
                                   onset_times=beats.onset_times(signal, sr))
        except Exception:
            stats["failed"] += 1
            continue
        if len(ns) < 16:
            stats["too_short"] += 1
            continue
        stats["transcribed"] += 1
        stats["confidences"].append(notes_mod.mean_confidence(ns))
        info = meta.get(path.name) or meta.get(str(path.relative_to(root))) or {}
        year = info.get("year")
        yield Document(
            ext_id=str(path.relative_to(root)),
            title=info.get("title") or path.stem,
            artist=info.get("artist", ""),
            pitches=[n.pitch for n in ns],
            year=int(year) if isinstance(year, int) and year > 0 else None,
            tradition="popular",
        )
        if stats["attempted"] % 20 == 0:
            print(f"  {stats['transcribed']}/{stats['attempted']} transcribed", flush=True)


idx = Index(args.db)
idx.register_stratum(STRATA[args.name])
t0 = time.time()
n = idx.add_documents(args.name, melodies())
idx.finalise()

conf = stats["confidences"]
summary = {
    "stratum": args.name, "indexed": n, "seconds": round(time.time() - t0, 1),
    "attempted": stats["attempted"], "failed": stats["failed"],
    "too_short_to_index": stats["too_short"], "separated": stats["separated"],
    "mean_confidence": round(float(np.mean(conf)), 4) if conf else None,
    "median_confidence": round(float(np.median(conf)), 4) if conf else None,
}
print(json.dumps(summary, indent=2))
pathlib.Path("data").mkdir(exist_ok=True)
json.dump(summary, open(f"data/transcription_{args.name}.json", "w"), indent=2)
print(f"\nTranscription statistics written to data/transcription_{args.name}.json — "
      f"these belong with any count drawn from this stratum.")
