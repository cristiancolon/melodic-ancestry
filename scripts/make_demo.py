"""Render a real corpus melody to audio so the pipeline can be tested against known input."""
import sys, pathlib, json, gzip
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from hookline import audio, synth

target_family = None
picked = None
with gzip.open("data/mtc.jsonl.gz", "rt", encoding="utf-8") as fh:
    for i, line in enumerate(fh):
        if i > 4000: break
        rec = json.loads(line)
        p = [x for x in (rec.get("features", {}).get("midipitch") or []) if isinstance(x, int)]
        if 24 <= len(p) <= 40 and rec.get("tunefamily") and rec.get("year"):
            picked = rec; break

pitches = [x for x in picked["features"]["midipitch"] if isinstance(x, int)][:32]
durs = [min(max(float(d) * 0.34, 0.16), 0.7) for d in picked["features"]["duration"][:32]]
x = synth.render(pitches, durs)
out = pathlib.Path("data/demo")
out.mkdir(parents=True, exist_ok=True)
audio.write_wav(out / "demo_known_melody.wav", x)

# also produce an MP3, so the primary input format is exercised for real
try:
    import imageio_ffmpeg, subprocess
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-y",
                    "-i", str(out / "demo_known_melody.wav"), "-b:a", "128k",
                    str(out / "demo_known_melody.mp3")], check=True)
except Exception as e:
    print("mp3 encode skipped:", e)

print(json.dumps({"id": picked["id"], "family": picked.get("tunefamily_full") or picked.get("tunefamily"),
                  "year": picked["year"], "n_notes": len(pitches), "pitches": pitches[:12]}, indent=2))
