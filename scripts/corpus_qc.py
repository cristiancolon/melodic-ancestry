"""Quality check on an indexed stratum's melodies.

Track selection on multi-track MIDI is a heuristic, and a heuristic that quietly picks
the bass line produces a corpus that looks fine in aggregate and is wrong in detail —
the same failure as the audio front end, arriving through the MIDI path. This measures
how often the extracted line sits where a melody actually sits.

Not ground truth: a low median pitch can be a genuine low melody. It is a smell test,
and the number belongs next to any count drawn from the stratum.
"""
import sys, pathlib, json, argparse, statistics
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from hookline.index import Index

ap = argparse.ArgumentParser()
ap.add_argument("stratum", nargs="?")
ap.add_argument("--db", default="data/hookline.db")
args = ap.parse_args()

idx = Index(args.db)
names = [args.stratum] if args.stratum else [s["name"] for s in idx.strata()]
MELODIC_LO, MELODIC_HI = 55, 84   # roughly G3..C6, where sung and lead lines live

report = {}
for name in names:
    rows = idx.conn.execute(
        "SELECT pitches FROM documents WHERE stratum=? AND pitches IS NOT NULL", (name,)
    ).fetchall()
    medians, ranges, flat = [], [], 0
    for (blob,) in rows:
        ps = [int(p) for p in blob.split(",") if p.strip()]
        if len(ps) < 8:
            continue
        medians.append(statistics.median(ps))
        ranges.append(max(ps) - min(ps))
        if len(set(ps)) < 4:
            flat += 1
    if not medians:
        continue
    in_band = sum(1 for m in medians if MELODIC_LO <= m <= MELODIC_HI) / len(medians)
    low = sum(1 for m in medians if m < MELODIC_LO) / len(medians)
    report[name] = {
        "works": len(medians),
        "median_pitch": round(statistics.median(medians), 1),
        "in_melodic_band": round(in_band, 3),
        "below_band_likely_bass": round(low, 3),
        "median_range_semitones": round(statistics.median(ranges), 1),
        "near_flat_lines": flat,
    }
    print(f"{name:14} {len(medians):>6} works | median pitch {statistics.median(medians):5.1f} | "
          f"in melodic band {in_band:5.1%} | likely bass {low:5.1%} | "
          f"median range {statistics.median(ranges):4.1f} st | flat lines {flat}")

json.dump(report, open("data/corpus_qc.json", "w"), indent=2)
print("\nwritten to data/corpus_qc.json — a stratum with a high 'likely bass' share is "
      "reporting counts over the wrong voice.")
