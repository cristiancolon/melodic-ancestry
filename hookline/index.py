"""Stratified inverted n-gram index over SQLite.

The one rule the schema enforces rather than documents: **counts are per stratum and are
never pooled.** A clean symbolic corpus and a machine-transcribed pop corpus have
different error characteristics, and averaging them produces a number that cannot answer
the only question that matters about a prior-art count -- what was it drawn from.

Dates get the same treatment. A work with no known year is counted in `undated`, never
folded into either side of a "predates" comparison.
"""
from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from .encode import ENCODINGS, encode, estimate_key, figure_key

SCHEMA = """
CREATE TABLE IF NOT EXISTS strata (
    name TEXT PRIMARY KEY, description TEXT, license TEXT,
    provenance TEXT, url TEXT, n_docs INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS documents (
    doc_id INTEGER PRIMARY KEY AUTOINCREMENT,
    stratum TEXT NOT NULL, ext_id TEXT, title TEXT, artist TEXT,
    year INTEGER, tradition TEXT, n_notes INTEGER, pitches TEXT
);
CREATE TABLE IF NOT EXISTS figures (
    figure_id INTEGER PRIMARY KEY AUTOINCREMENT,
    fkey TEXT NOT NULL, stratum TEXT NOT NULL,
    encoding TEXT NOT NULL, n INTEGER NOT NULL,
    df INTEGER DEFAULT 0, df_dated INTEGER DEFAULT 0,
    earliest INTEGER
);
CREATE TABLE IF NOT EXISTS postings (
    figure_id INTEGER NOT NULL, doc_id INTEGER NOT NULL, first_pos INTEGER
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_fig ON figures(fkey, stratum);
CREATE INDEX IF NOT EXISTS ix_fig_dist ON figures(stratum, encoding, n, df);
CREATE INDEX IF NOT EXISTS ix_post ON postings(figure_id);
CREATE INDEX IF NOT EXISTS ix_doc_stratum ON documents(stratum);
CREATE INDEX IF NOT EXISTS ix_doc_ext ON documents(stratum, ext_id);
"""


@dataclass
class Stratum:
    name: str
    description: str
    license: str
    provenance: str
    url: str = ""


@dataclass
class Document:
    ext_id: str
    title: str
    pitches: Sequence[int]
    artist: str = ""
    year: int | None = None
    tradition: str = ""


class Index:
    def __init__(self, path: str | Path = "data/hookline.db"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self.conn.executescript(SCHEMA)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")

    @property
    def conn(self) -> sqlite3.Connection:
        """One connection per thread. SQLite objects are thread-bound, and the server
        handles each request on its own thread; WAL mode lets the readers overlap."""
        existing = getattr(self._local, "conn", None)
        if existing is None:
            existing = sqlite3.connect(str(self.path))
            existing.execute("PRAGMA journal_mode=WAL")
            self._local.conn = existing
        return existing

    # ---------- build ----------

    def register_stratum(self, s: Stratum) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO strata(name,description,license,provenance,url,n_docs) "
            "VALUES(?,?,?,?,?,COALESCE((SELECT n_docs FROM strata WHERE name=?),0))",
            (s.name, s.description, s.license, s.provenance, s.url, s.name),
        )
        self.conn.commit()

    def add_documents(
        self,
        stratum: str,
        docs: Iterable[Document],
        n_range: Sequence[int] = (5, 7, 9),
        encodings: Sequence[str] = ("interval", "scale_degree", "contour_refined"),
        batch: int = 500,
        progress=None,
    ) -> int:
        """Index a batch of melodies. Defaults index three lengths across three
        encodings -- enough for the rarity distribution to be meaningful without
        multiplying the posting table by the full 5x9 grid.

        A work already in the stratum (same ext_id) is skipped, so re-running a build
        adds nothing. Indexing it again would count one melody twice in every N it
        touches. Returns the number of works newly added."""
        cur = self.conn.cursor()
        added = 0
        pending: list[tuple] = []

        for doc in docs:
            pitches = [int(p) for p in doc.pitches]
            if len(pitches) < min(n_range):
                continue
            if cur.execute(
                "SELECT 1 FROM documents WHERE stratum=? AND ext_id=?", (stratum, doc.ext_id)
            ).fetchone():
                continue
            cur.execute(
                "INSERT INTO documents(stratum,ext_id,title,artist,year,tradition,n_notes,pitches)"
                " VALUES(?,?,?,?,?,?,?,?)",
                (stratum, doc.ext_id, doc.title, doc.artist, doc.year, doc.tradition,
                 len(pitches), ",".join(str(p) for p in pitches)),
            )
            doc_id = cur.lastrowid
            key = estimate_key(pitches)

            seen: dict[str, int] = {}
            for n in n_range:
                if n > len(pitches):
                    continue
                for start in range(len(pitches) - n + 1):
                    window = pitches[start : start + n]
                    for enc in encodings:
                        fk = figure_key(enc, n, encode(window, enc, key))
                        seen.setdefault(fk, start)

            for fk, pos in seen.items():
                enc, n_s, _ = fk.split(":", 2)
                pending.append((fk, stratum, enc, int(n_s), doc_id, pos, doc.year))
            added += 1

            if len(pending) >= batch * 200:
                self._flush(cur, pending)
                pending.clear()
                if progress:
                    progress(added)

        self._flush(cur, pending)
        cur.execute(
            "UPDATE strata SET n_docs=(SELECT COUNT(*) FROM documents WHERE stratum=?) WHERE name=?",
            (stratum, stratum),
        )
        self.conn.commit()
        if progress:
            progress(added)
        return added

    def _flush(self, cur, pending: list[tuple]) -> None:
        if not pending:
            return
        cur.executemany(
            "INSERT OR IGNORE INTO figures(fkey,stratum,encoding,n) VALUES(?,?,?,?)",
            [(fk, st, enc, n) for fk, st, enc, n, _, _, _ in pending],
        )
        keys = {(fk, st) for fk, st, _, _, _, _, _ in pending}
        lookup = {}
        for fk, st in keys:
            row = cur.execute(
                "SELECT figure_id FROM figures WHERE fkey=? AND stratum=?", (fk, st)
            ).fetchone()
            if row:
                lookup[(fk, st)] = row[0]
        cur.executemany(
            "INSERT INTO postings(figure_id,doc_id,first_pos) VALUES(?,?,?)",
            [(lookup[(fk, st)], doc_id, pos) for fk, st, _, _, doc_id, pos, _ in pending if (fk, st) in lookup],
        )
        self.conn.commit()

    def finalise(self) -> None:
        """Recompute document frequencies and earliest dates. Run once after loading."""
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE figures SET
              df = (SELECT COUNT(DISTINCT p.doc_id) FROM postings p WHERE p.figure_id = figures.figure_id),
              df_dated = (SELECT COUNT(DISTINCT p.doc_id) FROM postings p
                          JOIN documents d ON d.doc_id = p.doc_id
                          WHERE p.figure_id = figures.figure_id AND d.year IS NOT NULL),
              earliest = (SELECT MIN(d.year) FROM postings p
                          JOIN documents d ON d.doc_id = p.doc_id
                          WHERE p.figure_id = figures.figure_id AND d.year IS NOT NULL)
        """)
        self.conn.commit()
        cur.execute("ANALYZE")
        self.conn.commit()

    # ---------- query ----------

    def strata(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT name,description,license,provenance,url,n_docs FROM strata ORDER BY name"
        ).fetchall()
        return [
            dict(zip(("name", "description", "license", "provenance", "url", "n_docs"), r))
            for r in rows
        ]

    def lookup(self, fkey: str, stratum: str) -> dict | None:
        row = self.conn.execute(
            "SELECT figure_id,df,df_dated,earliest FROM figures WHERE fkey=? AND stratum=?",
            (fkey, stratum),
        ).fetchone()
        if not row:
            return None
        return {"figure_id": row[0], "df": row[1], "df_dated": row[2], "earliest": row[3]}

    def count(self, fkey: str, stratum: str) -> int:
        row = self.lookup(fkey, stratum)
        return row["df"] if row else 0

    def count_before(self, fkey: str, stratum: str, year: int) -> int:
        row = self.conn.execute(
            "SELECT COUNT(DISTINCT p.doc_id) FROM postings p "
            "JOIN documents d ON d.doc_id=p.doc_id "
            "JOIN figures f ON f.figure_id=p.figure_id "
            "WHERE f.fkey=? AND f.stratum=? AND d.year IS NOT NULL AND d.year < ?",
            (fkey, stratum, int(year)),
        ).fetchone()
        return int(row[0]) if row else 0

    def matches(self, fkey: str, stratum: str, limit: int = 25) -> list[dict]:
        rows = self.conn.execute(
            "SELECT d.title,d.artist,d.year,d.tradition,d.ext_id,p.first_pos,d.n_notes "
            "FROM postings p JOIN documents d ON d.doc_id=p.doc_id "
            "JOIN figures f ON f.figure_id=p.figure_id "
            "WHERE f.fkey=? AND f.stratum=? "
            "ORDER BY (d.year IS NULL), d.year LIMIT ?",
            (fkey, stratum, limit),
        ).fetchall()
        return [
            dict(zip(("title", "artist", "year", "tradition", "ext_id", "position", "n_notes"), r))
            for r in rows
        ]

    def document_pitches(self, stratum: str, ext_id: str) -> list[int]:
        """The stored melody, so a match can be played back rather than only named.

        Hearing your figure against the 1755 tune that also contains it is the difference
        between a count you take on trust and one you can check.
        """
        row = self.conn.execute(
            "SELECT pitches FROM documents WHERE stratum=? AND ext_id=?", (stratum, ext_id)
        ).fetchone()
        if not row or not row[0]:
            return []
        return [int(p) for p in row[0].split(",") if p.strip()]

    def rarity_percentile(self, fkey: str, stratum: str) -> float | None:
        """Where this figure's document frequency sits among all figures of the same
        encoding and length in the same stratum. High percentile = appears in more works
        than most = commonplace."""
        row = self.conn.execute(
            "SELECT encoding,n,df FROM figures WHERE fkey=? AND stratum=?", (fkey, stratum)
        ).fetchone()
        if not row:
            return None
        enc, n, df = row
        total, below = self.conn.execute(
            "SELECT COUNT(*), SUM(CASE WHEN df < ? THEN 1 ELSE 0 END) "
            "FROM figures WHERE stratum=? AND encoding=? AND n=?",
            (df, stratum, enc, n),
        ).fetchone()
        if not total:
            return None
        return 100.0 * (below or 0) / total

    def indexed_lengths(self, stratum: str | None = None) -> list[int]:
        """The n values actually present. A query figure must be one of these lengths:
        rarity is defined per (encoding, n), so comparing across lengths is meaningless."""
        if stratum:
            rows = self.conn.execute(
                "SELECT DISTINCT n FROM figures WHERE stratum=? ORDER BY n", (stratum,)
            ).fetchall()
        else:
            rows = self.conn.execute("SELECT DISTINCT n FROM figures ORDER BY n").fetchall()
        return [int(r[0]) for r in rows]

    def undated_count(self, stratum: str) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) FROM documents WHERE stratum=? AND year IS NULL", (stratum,)
        ).fetchone()
        return int(row[0]) if row else 0

    def stats(self) -> dict:
        d = {}
        for k, q in (
            ("documents", "SELECT COUNT(*) FROM documents"),
            ("figures", "SELECT COUNT(*) FROM figures"),
            ("postings", "SELECT COUNT(*) FROM postings"),
        ):
            d[k] = int(self.conn.execute(q).fetchone()[0])
        d["strata"] = self.strata()
        return d

    def close(self) -> None:
        existing = getattr(self._local, "conn", None)
        if existing is not None:
            existing.close()
            self._local.conn = None
