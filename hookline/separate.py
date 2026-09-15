"""Source separation: pull a lead stem out before pitch tracking.

This is band 1 of the plan's own pipeline diagram, and skipping it is what broke the
first real-mix test. A time-domain pitch tracker finds the strongest periodicity in
whatever it is given; on commercial pop that is the bass, and no amount of tuning the
tracker changes which source is loudest.

Demucs is optional. When it is missing the pipeline falls back to the raw mix and says
so, rather than silently producing a bass transcription labelled as a melody.
"""
from __future__ import annotations

import numpy as np

DEMUCS_SR = 44100
STEMS = ("drums", "bass", "other", "vocals")


def available() -> bool:
    try:
        import demucs.apply  # noqa: F401
        import demucs.pretrained  # noqa: F401
        return True
    except Exception:
        return False


def _resample(x: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    if sr_in == sr_out:
        return x
    n = int(round(len(x) * sr_out / sr_in))
    if n <= 1:
        return np.zeros(0, dtype=np.float32)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


_MODEL = None


def _model(name: str = "htdemucs"):
    global _MODEL
    if _MODEL is None:
        from demucs.pretrained import get_model
        _MODEL = get_model(name)
        _MODEL.eval()
    return _MODEL


def separate(
    x: np.ndarray,
    sr: int,
    stems: tuple[str, ...] = ("vocals", "other"),
    model_name: str = "htdemucs",
    device: str | None = None,
) -> tuple[np.ndarray, dict]:
    """Return (lead_signal_at_sr, info).

    `stems` are summed. "vocals" alone is right for a sung hook; adding "other" keeps
    instrumental leads, at the cost of readmitting pads and counter-melodies.
    """
    info = {"separated": False, "stems": list(stems), "model": model_name, "reason": ""}
    if not available():
        info["reason"] = "demucs not installed — using the raw mix"
        return x, info

    import torch
    from demucs.apply import apply_model

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    model = _model(model_name)
    up = _resample(np.asarray(x, dtype=np.float32), sr, DEMUCS_SR)
    # demucs expects (batch, channels, samples); feed the mono signal as fake stereo
    wav = torch.from_numpy(np.stack([up, up])).unsqueeze(0).to(device)
    ref = wav.mean(dim=(0, 1))
    wav = (wav - ref.mean()) / (ref.std() + 1e-8)

    with torch.no_grad():
        out = apply_model(model.to(device), wav, device=device, progress=False, split=True,
                          overlap=0.15)[0]
    out = out * (ref.std() + 1e-8) + ref.mean()

    names = list(model.sources)
    keep = [names.index(s) for s in stems if s in names]
    if not keep:
        info["reason"] = f"none of {stems} in model sources {names}"
        return x, info

    lead = out[keep].sum(dim=0).mean(dim=0).cpu().numpy()
    lead = _resample(lead, DEMUCS_SR, sr)
    peak = float(np.max(np.abs(lead))) if lead.size else 0.0
    if peak > 0:
        lead = lead / peak

    info.update({"separated": True, "device": device, "sources": names,
                 "energy_ratio": round(float(peak), 4)})
    return lead.astype(np.float32), info
