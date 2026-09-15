"""Local HTTP server exposing the pipeline. Standard library only.

Uploads arrive as a raw request body with the filename in a query parameter rather than
as multipart, which keeps the server free of any parsing dependency.
"""
from __future__ import annotations

import io
import json
import tempfile
import uuid
import wave
from collections import OrderedDict
import traceback
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .index import Index
from .ledger import Ledger
from .pipeline import analyse, analyse_pitches

STATIC = Path(__file__).parent / "static"

# Decoded audio for the few most recent analyses, so hook snippets can be played back
# without re-uploading. Bounded: each entry is a couple of 90-second mono float arrays.
_CLIPS: "OrderedDict[str, dict]" = OrderedDict()
_CLIP_LIMIT = 4


def _remember(mix, lead, sr) -> str:
    token = uuid.uuid4().hex[:12]
    _CLIPS[token] = {"mix": mix, "lead": lead, "sr": sr}
    while len(_CLIPS) > _CLIP_LIMIT:
        _CLIPS.popitem(last=False)
    return token


def wav_bytes(samples, sr: int) -> bytes:
    import numpy as np

    clipped = np.clip(np.asarray(samples, dtype="float32"), -1.0, 1.0)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(int(sr))
        w.writeframes((clipped * 32767.0).astype("<i2").tobytes())
    return buf.getvalue()
NOTE_NAMES = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}
MAX_UPLOAD = 60 * 1024 * 1024


def parse_pitches(text: str) -> list[int]:
    """Accept MIDI numbers or note names: '60 62 64' or 'C4 D4 E4' or 'c d e'."""
    out: list[int] = []
    for tok in text.replace(",", " ").split():
        tok = tok.strip()
        if not tok:
            continue
        try:
            out.append(int(tok))
            continue
        except ValueError:
            pass
        name = tok.lower()
        if name[0] not in NOTE_NAMES:
            continue
        pitch = NOTE_NAMES[name[0]]
        i = 1
        while i < len(name) and name[i] in "#b♯♭":
            pitch += 1 if name[i] in "#♯" else -1
            i += 1
        octave = 4
        if i < len(name):
            try:
                octave = int(name[i:])
            except ValueError:
                octave = 4
        out.append(pitch + (octave + 1) * 12)
    return out


class Handler(BaseHTTPRequestHandler):
    index: Index
    ledger: Ledger

    def log_message(self, fmt, *args):  # quieter console
        pass

    # ---------- helpers ----------

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, payload: dict, code: int = 200) -> None:
        self._send(code, json.dumps(payload).encode(), "application/json; charset=utf-8")

    # ---------- routes ----------

    def do_GET(self):
        route = urllib.parse.urlparse(self.path)
        if route.path in ("/", "/index.html"):
            page = STATIC / "app.html"
            if not page.exists():
                return self._send(500, b"app.html missing", "text/plain")
            return self._send(200, page.read_bytes(), "text/html; charset=utf-8")
        if route.path == "/api/demo":
            demo = Path("data/demo/demo_known_melody.mp3")
            if not demo.exists():
                return self._json({"error": "no bundled demo; run scripts/make_demo.py"}, 404)
            year = urllib.parse.parse_qs(route.query).get("year", ["1950"])[0]
            result = analyse(demo, self.index, reference_year=int(year) if year.isdigit() else None,
                             keep_audio=True)
            result["file"] = demo.name
            result["clip_token"] = _remember(result.pop("_mix"), result.pop("_lead"),
                                             result.pop("_sr"))
            result["demo_note"] = (
                "A melody from the indexed corpus itself (NLB125974_01, 'Daar ging een "
                "patertje langs de kant', 1890), synthesised to audio. Clean synthetic tone "
                "is the kind end of the range — a real mix is much harder."
            )
            return self._json(result)
        if route.path == "/api/clip":
            q = urllib.parse.parse_qs(route.query)
            entry = _CLIPS.get(q.get("token", [""])[0])
            if entry is None:
                return self._send(404, b"clip expired", "text/plain")
            source = "lead" if q.get("source", ["mix"])[0] == "lead" else "mix"
            sr = entry["sr"]
            try:
                start = max(float(q.get("start", ["0"])[0]), 0.0)
                end = float(q.get("end", ["0"])[0]) or start + 3.0
            except ValueError:
                start, end = 0.0, 3.0
            pad = 0.25  # a little air either side, so the figure is not clipped mid-note
            a = int(max(start - pad, 0) * sr)
            b = int((end + pad) * sr)
            data = entry[source][a:b]
            if data.size == 0:
                return self._send(404, b"empty clip", "text/plain")
            return self._send(200, wav_bytes(data, sr), "audio/wav")

        if route.path == "/api/render":
            q = urllib.parse.parse_qs(route.query)
            from .synth import render as synth_render

            pitches: list[int] = []
            if q.get("pitches"):
                pitches = [int(p) for p in q["pitches"][0].split(",") if p.strip().lstrip("-").isdigit()]
            elif q.get("ext_id"):
                stratum = q.get("stratum", [""])[0]
                full = self.index.document_pitches(stratum, q["ext_id"][0])
                try:
                    pos = int(q.get("pos", ["0"])[0])
                    n = int(q.get("n", ["9"])[0])
                except ValueError:
                    pos, n = 0, 9
                lo = max(pos - 2, 0)
                pitches = full[lo : pos + n + 2]
            if not pitches:
                return self._send(404, b"nothing to render", "text/plain")
            audio_arr = synth_render(pitches[:40], [0.34] * len(pitches[:40]))
            return self._send(200, wav_bytes(audio_arr, 22050), "audio/wav")

        if route.path == "/api/stats":
            return self._json({"index": self.index.stats(), "ledger": self.ledger.stats()})
        if route.path == "/api/lineage":
            q = urllib.parse.parse_qs(route.query).get("q", [""])[0]
            return self._json(self.ledger.lineage(q) if q else {"found": False})
        if route.path == "/api/katz":
            return self._json({"ranking": self.ledger.katz()[:20]})
        return self._send(404, b"not found", "text/plain")

    def do_POST(self):
        route = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(route.query)
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_UPLOAD:
            return self._json({"error": "file is larger than the 60 MB limit"}, 413)
        body = self.rfile.read(length)

        try:
            year = params.get("year", [""])[0]
            year_int = int(year) if year.strip().isdigit() else None

            if route.path == "/api/analyze":
                name = params.get("name", ["upload"])[0]
                suffix = Path(name).suffix or ".mp3"
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as fh:
                    fh.write(body)
                    tmp = Path(fh.name)
                fmin = params.get("fmin", ["65"])[0]
                try:
                    fmin_f = float(fmin)
                except ValueError:
                    fmin_f = 65.0
                try:
                    result = analyse(tmp, self.index, reference_year=year_int, fmin=fmin_f,
                                     stem=params.get("stem", ["auto"])[0], keep_audio=True)
                    result["file"] = name
                    result["clip_token"] = _remember(result.pop("_mix"), result.pop("_lead"),
                                                     result.pop("_sr"))
                    return self._json(result)
                finally:
                    tmp.unlink(missing_ok=True)

            if route.path == "/api/symbolic":
                payload = json.loads(body or b"{}")
                pitches = parse_pitches(str(payload.get("pitches", "")))
                if len(pitches) < 4:
                    return self._json({"error": "give at least four notes"}, 400)
                return self._json(
                    analyse_pitches(
                        pitches, self.index,
                        reference_year=payload.get("year") or year_int,
                        label=payload.get("label") or "symbolic query",
                    )
                )
        except Exception as exc:
            return self._json({"error": str(exc), "trace": traceback.format_exc()[-1200:]}, 500)

        return self._send(404, b"not found", "text/plain")


def serve(host: str = "127.0.0.1", port: int = 8765, db: str = "data/hookline.db") -> None:
    Handler.index = Index(db)
    Handler.ledger = Ledger()
    stats = Handler.index.stats()
    print(f"Hookline on http://{host}:{port}")
    print(f"  index: {stats['documents']} documents, {stats['figures']} figures, {stats['postings']} postings")
    for s in stats["strata"]:
        print(f"    {s['name']:14} {s['n_docs']:>6} docs   {s['license'][:44]}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()
