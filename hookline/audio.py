"""Audio decoding. MP3 in, mono float32 out.

Three decoders, tried in order, so the pipeline runs wherever it lands:
libsndfile (handles MP3 since 1.1), a pip-installed static ffmpeg, then the stdlib
wave module for uncompressed input. No system ffmpeg is required.
"""
from __future__ import annotations

import io
import subprocess
import wave
from pathlib import Path

import numpy as np

SR = 22050


def _resample(x: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    """Linear resampling. Adequate here: everything downstream works on f0 contours
    well below Nyquist, so resampler artefacts do not reach the pitch estimate."""
    if sr_in == sr_out:
        return x
    n_out = int(round(len(x) * sr_out / sr_in))
    if n_out <= 1:
        return np.zeros(0, dtype=np.float32)
    idx = np.linspace(0, len(x) - 1, n_out)
    return np.interp(idx, np.arange(len(x)), x).astype(np.float32)


def _via_soundfile(path: Path) -> tuple[np.ndarray, int]:
    import soundfile as sf

    data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    return data.mean(axis=1), sr


def _via_ffmpeg(path: Path) -> tuple[np.ndarray, int]:
    import imageio_ffmpeg

    exe = imageio_ffmpeg.get_ffmpeg_exe()
    proc = subprocess.run(
        [exe, "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
        capture_output=True,
        check=True,
    )
    return np.frombuffer(proc.stdout, dtype=np.float32).copy(), SR


def _via_wave(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as w:
        sr, n_ch, width = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    dtype = {1: np.uint8, 2: np.int16, 4: np.int32}.get(width)
    if dtype is None:
        raise ValueError(f"unsupported sample width: {width}")
    x = np.frombuffer(raw, dtype=dtype).astype(np.float32)
    x = (x - 128.0) / 128.0 if width == 1 else x / float(np.iinfo(dtype).max)
    if n_ch > 1:
        x = x.reshape(-1, n_ch).mean(axis=1)
    return x, sr


def load(path: str | Path, sr: int = SR) -> tuple[np.ndarray, int]:
    """Decode any supported file to mono float32 at `sr`. Returns (samples, sr)."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    errors = []
    for name, fn in (("soundfile", _via_soundfile), ("ffmpeg", _via_ffmpeg), ("wave", _via_wave)):
        try:
            x, sr_in = fn(path)
            if x.size == 0:
                raise ValueError("decoded zero samples")
            x = _resample(np.nan_to_num(x), sr_in, sr)
            peak = float(np.max(np.abs(x))) if x.size else 0.0
            if peak > 0:
                x = x / peak
            return x.astype(np.float32), sr
        except Exception as exc:  # try the next decoder
            errors.append(f"{name}: {exc}")
    raise RuntimeError("could not decode " + str(path) + "\n  " + "\n  ".join(errors))


def write_wav(path: str | Path, x: np.ndarray, sr: int = SR) -> Path:
    """Write mono float32 to 16-bit PCM WAV using only the stdlib."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    clipped = np.clip(x, -1.0, 1.0)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((clipped * 32767.0).astype("<i2").tobytes())
    return path
