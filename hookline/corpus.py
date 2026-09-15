"""Corpus loaders, and the provenance that travels with them.

Every stratum carries its licence and a one-line statement of what it was drawn from,
because the count this system produces is only evidence if that question has an answer.
The loaders deliberately keep `year=None` distinct from `year=0`: an undated work is not
an old work, and the two must never merge.
"""
from __future__ import annotations

import gzip
import json
import re
from pathlib import Path
from typing import Callable, Iterator

from .index import Document, Stratum

# Registered corpora. `url` and `license` are as stated by the source and were verified
# to resolve on 2026-09-07; see docs/plans/unified-plan.md for the licence caveats.
STRATA = {
    "mtc-fs-inst": Stratum(
        name="mtc-fs-inst",
        description="Meertens Tune Collections FS-INST 2.0 — Dutch folk song and instrumental melodies",
        license="CC BY-NC-SA 3.0",
        provenance=(
            "18,618 monophonic melodies from the Dutch Song Database, dated by source "
            "publication. Skews Dutch folk and instrumental repertoire; NOT commercial pop. "
            "Carries tune-family labels, which serve as known-item retrieval ground truth."
        ),
        url="https://zenodo.org/records/3551003",
    ),
    "essen": Stratum(
        name="essen",
        description="Essen Folksong Collection — European (mostly German) folk melodies",
        license="CC BY-NC-SA 3.0 as published on Zenodo; derived from CCARH kern files "
                "whose own terms are more restrictive. Licence provenance is muddled — do "
                "not redistribute without resolving it.",
        provenance=(
            "European folk melodies, essentially all UNDATED in this release. Undated works "
            "are counted separately and never contribute to a 'predates' figure."
        ),
        url="https://zenodo.org/records/3551003",
    ),
    "pop909": Stratum(
        name="pop909",
        description="POP909 — 909 popular songs with human-annotated melody tracks",
        license="MIT (Music X Lab, 2020). The annotations are MIT; the underlying "
                "compositions remain in copyright, so counts may be published but the "
                "melodies themselves may not be redistributed.",
        provenance=(
            "909 songs of CHINESE popular music, each with a musician-annotated MELODY "
            "track — so the melodic line is human-identified rather than inferred. "
            "UNDATED: the release carries no per-song years, so these works contribute to "
            "N but never to a 'predates' count. This is popular repertoire but NOT Western "
            "commercial pop; treat coverage claims accordingly."
        ),
        url="https://github.com/music-x-lab/POP909-Dataset",
    ),
    "lakh-clean": Stratum(
        name="lakh-clean",
        description="Lakh MIDI 'clean_midi' subset — Western commercial popular music",
        license=(
            "CC BY 4.0 covers Raffel's AGGREGATION and metadata only. The files are "
            "user-made transcriptions of copyrighted commercial recordings scraped from "
            "MIDI-sharing sites; the compositions remain in copyright. Counts and "
            "statistics may be published; the melodies may NOT be redistributed."
        ),
        provenance=(
            "MIDI transcriptions of Western commercial popular music, artist and title "
            "carried in the filenames. These are amateur transcriptions of varying "
            "fidelity, not authoritative scores, and the melodic line is chosen by this "
            "system's own track scoring rather than annotated by a human. UNDATED in this "
            "subset: per-track years require the lmd_matched join to the Million Song "
            "Dataset, whose year field is sparse and unaudited."
        ),
        url="http://hog.ee.columbia.edu/craffel/lmd/",
    ),
    "nottingham": Stratum(
        name="nottingham",
        description="Nottingham Music Database — British and Irish folk-dance tunes",
        license="GPL-3.0 (per the repository's own LICENSE.md)",
        provenance=(
            "1,000+ monophonic folk-dance melodies with chord annotations, distributed as "
            "ABC and MIDI. UNDATED. A third folk tradition — it widens coverage but does "
            "NOT make the denominator representative of commercial popular music."
        ),
        url="https://github.com/jukedeck/nottingham-dataset",
    ),
}


def load_midi_dir(
    root: str | Path,
    stratum: str,
    limit: int | None = None,
    min_notes: int = 16,
    year_for: Callable[[Path], int | None] | None = None,
    title_for: Callable[[Path], str] | None = None,
    artist_from_parent: bool = False,
    tradition: str = "popular",
    pattern: str = "**/*.mid*",
    dedupe: bool = False,
    max_notes: int | None = None,
) -> Iterator[Document]:
    """Walk a directory of MIDI files, taking one melodic line from each.

    `dedupe` collapses multiple transcriptions of the same song, which is essential for
    any corpus of scraped MIDI: without it a popular song contributes as many "works" as
    people happened to transcribe it.

    `year_for` is deliberately a callback rather than a field: dating is where these
    corpora differ most, and a corpus with no dates must yield None rather than a
    plausible-looking guess. An undated work is counted separately and never contributes
    to a 'predates' figure.
    """
    from .midi import melody

    root = Path(root)
    seen = 0
    taken: set[tuple[str, str]] = set()
    for path in sorted(root.glob(pattern)):
        if limit is not None and seen >= limit:
            break
        if dedupe:
            # "Take A Bow.mid", "Take A Bow.3.mid" and "Take A Bow (1995).7.mid" are
            # different transcriptions of ONE song. Counting each as a separate work
            # inflates every N by the transcription count, which is not a fact about
            # the repertoire.
            stem = re.sub(r"\.\d+$", "", path.stem)
            stem = re.sub(r"\((19|20)\d{2}\)", "", stem)
            key = (path.parent.name.lower(), re.sub(r"[^a-z0-9]", "", stem.lower()))
            if key in taken:
                continue
            taken.add(key)

        pitches = melody(path, min_notes=min_notes)
        if len(pitches) < min_notes:
            continue
        if max_notes:
            pitches = pitches[:max_notes]
        seen += 1
        rel = path.relative_to(root)
        yield Document(
            ext_id=str(rel),
            title=(title_for(path) if title_for else path.stem.replace("_", " ")),
            artist=(rel.parts[0] if artist_from_parent and len(rel.parts) > 1 else ""),
            pitches=pitches,
            year=(year_for(path) if year_for else None),
            tradition=tradition,
        )


def load_jsonl(
    path: str | Path,
    stratum: str,
    limit: int | None = None,
    min_notes: int = 12,
) -> Iterator[Document]:
    """Read the MTCFeatures JSONL format (gzipped) into Documents.

    `midipitch` is the field used; `year` of -1 means unknown in this release and is
    mapped to None rather than to a number.
    """
    path = Path(path)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if limit is not None and i >= limit:
                break
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            feats = rec.get("features") or {}
            pitches = [p for p in (feats.get("midipitch") or []) if isinstance(p, int)]
            if len(pitches) < min_notes:
                continue
            year = rec.get("year")
            year = int(year) if isinstance(year, int) and year > 0 else None
            family = rec.get("tunefamily_full") or rec.get("tunefamily") or ""
            yield Document(
                ext_id=str(rec.get("id", f"{stratum}-{i}")),
                title=family or str(rec.get("id", "")),
                artist=rec.get("origin", "") or "",
                pitches=pitches,
                year=year,
                tradition="folk",
            )


def tune_families(path: str | Path, limit: int | None = None) -> dict[str, list[str]]:
    """Map tune-family id -> member ids. This is the evaluation ground truth: members of
    a family are known melodic variants of one another, established by musicologists and
    entirely independent of any litigation record."""
    path = Path(path)
    opener = gzip.open if path.suffix == ".gz" else open
    fams: dict[str, list[str]] = {}
    with opener(path, "rt", encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if limit is not None and i >= limit:
                break
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            fam = rec.get("tunefamily")
            if fam:
                fams.setdefault(str(fam), []).append(str(rec.get("id")))
    return {k: v for k, v in fams.items() if len(v) > 1}
