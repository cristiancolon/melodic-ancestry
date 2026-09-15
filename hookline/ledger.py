"""The Ledger: directed, dated work-to-work derivation edges.

Direction never comes from the audio. It comes from here, or it is not claimed. This is
the whole of the project's position on the direction problem: every verified system that
produces ancestry gets its arrows from human curation, so the honest thing is to say so
and show the curator's edge rather than to infer one from a similarity score.

Both sources are queried live at small scale -- no bulk dump -- and cached. Edges are
reported with their source so a reader can tell curated fact from model output.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

USER_AGENT = "Hookline/0.1 (melodic provenance research prototype)"
WIKIDATA = "https://query.wikidata.org/sparql"
MUSICBRAINZ = "https://musicbrainz.org/ws/2"

# Musical-work classes: song, musical composition, single, musical work/composition.
WORK_TYPES = "wd:Q7366 wd:Q134556 wd:Q207628 wd:Q2188189 wd:Q105543609"

SPARQL_DERIVATIONS = """
SELECT ?work ?workLabel ?workDate ?basedOn ?basedOnLabel ?basedOnDate WHERE {
  ?work wdt:P144 ?basedOn .
  ?work wdt:P31 ?workType .
  VALUES ?workType { %s }
  OPTIONAL { ?work wdt:P577 ?workDate . }
  OPTIONAL { ?basedOn wdt:P577 ?basedOnDate . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
LIMIT %d
"""

SCHEMA = """
CREATE TABLE IF NOT EXISTS edges (
    src TEXT NOT NULL,        -- the derivative
    dst TEXT NOT NULL,        -- the antecedent
    src_label TEXT, dst_label TEXT,
    src_year INTEGER, dst_year INTEGER,
    relation TEXT, source TEXT, fetched_at REAL,
    PRIMARY KEY (src, dst, source)
);
"""


@dataclass
class Edge:
    src: str
    dst: str
    src_label: str
    dst_label: str
    src_year: int | None
    dst_year: int | None
    relation: str
    source: str


def _get(url: str, timeout: float = 30.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _year(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(str(value)[:4].lstrip("-") or 0) or None
    except ValueError:
        return None


class Ledger:
    def __init__(self, path: str | Path = "data/ledger.db"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self.conn.executescript(SCHEMA)

    @property
    def conn(self) -> sqlite3.Connection:
        existing = getattr(self._local, "conn", None)
        if existing is None:
            existing = sqlite3.connect(str(self.path))
            self._local.conn = existing
        return existing

    # ---------- sources ----------

    def fetch_wikidata(self, limit: int = 400) -> int:
        """Wikidata P144 ('based on'), restricted to musical-work types.

        Unrestricted P144 is dominated by software; the type filter is what makes it a
        music graph. Dates come from P577 and are NOT trustworthy on their own -- some
        are Wikipedia-import artefacts with no reference chain -- so they are stored as
        reported and flagged by source, never treated as adjudicated fact.
        """
        query = SPARQL_DERIVATIONS % (WORK_TYPES, limit)
        url = f"{WIKIDATA}?query={urllib.parse.quote(query)}&format=json"
        data = json.loads(_get(url))
        rows = data.get("results", {}).get("bindings", [])
        edges = [
            Edge(
                src=r["work"]["value"].rsplit("/", 1)[-1],
                dst=r["basedOn"]["value"].rsplit("/", 1)[-1],
                src_label=r.get("workLabel", {}).get("value", ""),
                dst_label=r.get("basedOnLabel", {}).get("value", ""),
                src_year=_year(r.get("workDate", {}).get("value")),
                dst_year=_year(r.get("basedOnDate", {}).get("value")),
                relation="based on (P144)",
                source="wikidata",
            )
            for r in rows
            if "work" in r and "basedOn" in r
        ]
        return self.add(edges)

    def fetch_musicbrainz_work(self, mbid: str, pause: float = 1.05) -> int:
        """Work-to-work relationships for one MBID.

        MusicBrainz asks for 1 request/second and its search endpoint returns 503 under
        load, so callers should retry rather than assume a hard failure.
        """
        url = f"{MUSICBRAINZ}/work/{mbid}?inc=work-rels&fmt=json"
        data = json.loads(_get(url))
        title = data.get("title", "")
        edges = []
        for rel in data.get("relations", []):
            target = rel.get("work") or {}
            if not target.get("id"):
                continue
            backward = rel.get("direction") == "backward"
            a, b = (target["id"], mbid) if backward else (mbid, target["id"])
            la, lb = (target.get("title", ""), title) if backward else (title, target.get("title", ""))
            edges.append(
                Edge(a, b, la, lb, None, None, rel.get("type", "related"), "musicbrainz")
            )
        time.sleep(pause)
        return self.add(edges)

    # ---------- storage ----------

    def add(self, edges: list[Edge]) -> int:
        now = time.time()
        self.conn.executemany(
            "INSERT OR REPLACE INTO edges VALUES(?,?,?,?,?,?,?,?,?)",
            [
                (e.src, e.dst, e.src_label, e.dst_label, e.src_year, e.dst_year,
                 e.relation, e.source, now)
                for e in edges
            ],
        )
        self.conn.commit()
        return len(edges)

    def edges(self) -> list[Edge]:
        rows = self.conn.execute(
            "SELECT src,dst,src_label,dst_label,src_year,dst_year,relation,source FROM edges"
        ).fetchall()
        return [Edge(*r) for r in rows]

    def lineage(self, label_query: str, depth: int = 3) -> dict:
        """Ancestors and descendants of a work, matched loosely by label."""
        edges = self.edges()
        by_label = {}
        for e in edges:
            by_label.setdefault(e.src_label.lower(), e.src)
            by_label.setdefault(e.dst_label.lower(), e.dst)
        q = label_query.lower().strip()
        node = next((v for k, v in by_label.items() if q and q in k), None)
        if node is None:
            return {"found": False, "query": label_query}

        labels = {}
        for e in edges:
            labels[e.src] = e.src_label or e.src
            labels[e.dst] = e.dst_label or e.dst

        def walk(start, forward):
            seen, frontier, out = {start}, [start], []
            for _ in range(depth):
                nxt = []
                for n in frontier:
                    for e in edges:
                        a, b = (e.src, e.dst) if forward else (e.dst, e.src)
                        if a == n and b not in seen:
                            seen.add(b)
                            nxt.append(b)
                            out.append({
                                "from": labels.get(a, a), "to": labels.get(b, b),
                                "relation": e.relation, "source": e.source,
                                "from_year": e.src_year if forward else e.dst_year,
                                "to_year": e.dst_year if forward else e.src_year,
                            })
                frontier = nxt
            return out

        return {
            "found": True,
            "node": labels.get(node, node),
            "antecedents": walk(node, True),
            "descendants": walk(node, False),
        }

    def katz(self, alpha: float = 0.1, beta: float = 1.0, iterations: int = 100) -> list[tuple[str, float]]:
        """Katz centrality over the derivation graph.

        This reproduces the measure Bryan & Wang used on the only working ancestry
        result in the literature. On a sparse curated graph the ranking mostly tells you
        how much curation a work has attracted, which is itself the number that decides
        whether there is a product in the undocumented tail.
        """
        edges = self.edges()
        if not edges:
            return []
        nodes = sorted({e.src for e in edges} | {e.dst for e in edges})
        idx = {n: i for i, n in enumerate(nodes)}
        labels = {}
        for e in edges:
            labels[e.src] = e.src_label or e.src
            labels[e.dst] = e.dst_label or e.dst

        try:
            import numpy as np
        except ImportError:
            return []
        A = np.zeros((len(nodes), len(nodes)), dtype=float)
        for e in edges:
            A[idx[e.dst], idx[e.src]] = 1.0  # influence flows antecedent -> derivative

        x = np.full(len(nodes), beta, dtype=float)
        for _ in range(iterations):
            nxt = alpha * (A @ x) + beta
            if np.allclose(nxt, x, atol=1e-9):
                x = nxt
                break
            x = nxt
        order = np.argsort(-x)
        return [(labels.get(nodes[i], nodes[i]), float(x[i])) for i in order]

    def stats(self) -> dict:
        row = self.conn.execute(
            "SELECT COUNT(*), COUNT(DISTINCT src), COUNT(DISTINCT source) FROM edges"
        ).fetchone()
        dated = self.conn.execute(
            "SELECT COUNT(*) FROM edges WHERE src_year IS NOT NULL AND dst_year IS NOT NULL"
        ).fetchone()[0]
        return {"edges": row[0], "works": row[1], "sources": row[2], "fully_dated": dated}

    def close(self) -> None:
        existing = getattr(self._local, "conn", None)
        if existing is not None:
            existing.close()
            self._local.conn = None
