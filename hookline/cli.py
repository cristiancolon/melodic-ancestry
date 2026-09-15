"""Command line entry points."""
from __future__ import annotations

import argparse
import json
import sys

from .index import Index
from .pipeline import analyse, analyse_pitches


def phrases_min(_d) -> int:
    from .phrases import MIN_PHRASE_NOTES
    return MIN_PHRASE_NOTES


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="hookline", description="Melodic prior-art counting")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("analyse", help="analyse an audio file")
    a.add_argument("path")
    a.add_argument("--year", type=int, default=None, help="reference year for the M count")
    a.add_argument("--db", default="data/hookline.db")
    a.add_argument("--fmin", type=float, default=65.0,
                   help="pitch search floor in Hz; raise toward 220 on a full mix to skip the bass")
    a.add_argument("--stem", default="auto",
                   help="source separation: auto (default), vocals, vocals+other, or none")
    a.add_argument("--json", action="store_true")

    s = sub.add_parser("symbolic", help="analyse a note sequence")
    s.add_argument("pitches", nargs="+")
    s.add_argument("--year", type=int, default=None)
    s.add_argument("--db", default="data/hookline.db")

    v = sub.add_parser("serve", help="run the local GUI")
    v.add_argument("--port", type=int, default=8765)
    v.add_argument("--db", default="data/hookline.db")

    sub.add_parser("stats", help="index statistics").add_argument("--db", default="data/hookline.db")

    args = ap.parse_args(argv)

    if args.cmd == "serve":
        from .server import serve
        serve(port=args.port, db=args.db)
        return 0

    idx = Index(args.db)
    if args.cmd == "stats":
        print(json.dumps(idx.stats(), indent=2))
        return 0

    if args.cmd == "analyse":
        result = analyse(args.path, idx, reference_year=args.year, fmin=args.fmin, stem=args.stem)
    else:
        from .server import parse_pitches
        result = analyse_pitches(parse_pitches(" ".join(args.pitches)), idx, reference_year=args.year)

    if getattr(args, "json", False):
        print(json.dumps(result, indent=2))
        return 0

    print(f"{result['file']}  —  {result.get('n_notes', 0)} notes, "
          f"confidence {result.get('mean_confidence', 0):.2f}")
    sep = result.get("separation") or {}
    if sep.get("separated"):
        print(f"  separated: {'+'.join(sep.get('stems_used', []))} stem — {sep.get('reason', '')}")
    elif sep.get("reason"):
        print(f"  no separation: {sep['reason']}")
    d = result.get("diagnostics")
    if d and not result["cards"]:
        print("\n  NO FIGURE COUNTED — nothing was measured, which is not the same as "
              "finding no prior art:")
        print(f"    notes transcribed        {d['n_notes']}")
        print(f"    phrases >= {phrases_min(d)} notes        {d['phrases_found']}")
        print(f"    phrases too short to index  {d['phrases_too_short']} "
              f"(shortest indexed figure is {d['shortest_indexed_length']} notes)")
        print(f"    phrases rejected as flat {d.get('phrases_rejected_as_flat', 0)} "
              f"(no melodic movement)")
        print(f"    median gap between notes {d['median_note_gap_s']}s   "
              f"gaps beyond the rest threshold {d['fragmented_gaps']}")
        if d["note"]:
            print(f"    {d['note']}")
    for card in result["cards"]:
        print(f"\n  {card['label']}  [{card['verdict'].replace('_', ' ')}]")
        print(f"    notes {card['pitch_names'] if 'pitch_names' in card else card['top1_pitches']}")
        for st in card["strata"]:
            n, m = st["n"], st["m"]
            line = f"    {st['stratum']:14} N={n['expected']:.1f} [{n['low']}-{n['high']}] (top-1 {n['top1']})"
            if m:
                line += f"   M={m['expected']:.1f} [{m['low']}-{m['high']}]"
            if st["rarity_percentile"] is not None:
                line += f"   {st['rarity_percentile']:.0f}th pct"
            print(line)
        for r in card["reasons"]:
            print(f"      · {r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
