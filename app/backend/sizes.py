"""
Per-model output-size menus for GET /api/catalog (v1.17.0).

Story Studio (and any client) reads `sizes` to drive its aspect-ratio +
resolution pickers with ZERO pixel math — every entry is an exact, accepted
{width, height} the model/supplier will actually produce.

Rules implemented here:
  * Local models  → a curated, /16-aligned ladder capped at the local ~1.3 MP
    budget (so output stays in the latency/memory sweet spot).
  * Cloud models  → a higher ladder of familiar standard resolutions (720p,
    1080p, …), /8-aligned, filtered by each provider's real max side. Cloud is
    NOT downscaled to the local cap.
  * Fixed-output models (Cloudflare FLUX schnell, Gemini) → a single size with
    `fixed: true` (they ignore width/height and emit one model-chosen size).

Each size object:
    { aspect_ratio, label, width, height, tier, [default: true], [fixed: true] }

`tier` is fast | balanced | high | ultra (smallest→largest within an aspect
ratio) — clients can map quality presets (Fast / Balanced / Highest) straight
onto it instead of re-deriving smallest/middle/largest.

build_sizes(model) returns:
    { "sizes": [...], "default_aspect_ratio": "16:9", "custom": {...} | None }
where `custom` (when present) describes the free-sizing range the model allows.
"""
from __future__ import annotations

from math import gcd

# ── Local ladders: /16-aligned, each ≤ ~1.3 MP (the local budget) ──
# (label, width, height, tier)
_LOCAL_LADDERS: dict[str, list[tuple[str, int, int, str]]] = {
    "1:1":  [("768", 768, 768, "fast"),       ("1024", 1024, 1024, "balanced"), ("1152", 1152, 1152, "high")],
    "16:9": [("1024×576", 1024, 576, "fast"), ("1344×768", 1344, 768, "balanced"), ("1536×864", 1536, 864, "high")],
    "9:16": [("576×1024", 576, 1024, "fast"), ("768×1344", 768, 1344, "balanced"), ("864×1536", 864, 1536, "high")],
    "4:3":  [("896×672", 896, 672, "fast"),   ("1152×864", 1152, 864, "balanced"), ("1280×960", 1280, 960, "high")],
    "3:4":  [("672×896", 672, 896, "fast"),   ("864×1152", 864, 1152, "balanced"), ("960×1280", 960, 1280, "high")],
    "3:2":  [("1024×688", 1024, 688, "fast"), ("1216×832", 1216, 832, "balanced"), ("1344×896", 1344, 896, "high")],
    "2:3":  [("688×1024", 688, 1024, "fast"), ("832×1216", 832, 1216, "balanced"), ("896×1344", 896, 1344, "high")],
    "21:9": [("1280×544", 1280, 544, "fast"), ("1536×640", 1536, 640, "balanced")],
}
_LOCAL_MAX_PIXELS = 1_400_000
_LOCAL_CUSTOM = {"min_px": 512, "max_px": 1536, "step": 16, "max_pixels": _LOCAL_MAX_PIXELS}

# ── Cloud ladders: familiar standard resolutions, /8-aligned ──
_CLOUD_LADDERS: dict[str, list[tuple[str, int, int, str]]] = {
    "1:1":  [("512", 512, 512, "fast"),       ("1024", 1024, 1024, "balanced"), ("1536", 1536, 1536, "high"),  ("2048", 2048, 2048, "ultra")],
    "16:9": [("720p", 1280, 720, "fast"),     ("1080p", 1920, 1080, "balanced"), ("1440p", 2560, 1440, "high")],
    "9:16": [("720p", 720, 1280, "fast"),     ("1080p", 1080, 1920, "balanced"), ("1440p", 1440, 2560, "high")],
    "4:3":  [("1024×768", 1024, 768, "fast"), ("1600×1200", 1600, 1200, "balanced"), ("2048×1536", 2048, 1536, "high")],
    "3:4":  [("768×1024", 768, 1024, "fast"), ("1200×1600", 1200, 1600, "balanced"), ("1536×2048", 1536, 2048, "high")],
    "3:2":  [("1080×720", 1080, 720, "fast"), ("1536×1024", 1536, 1024, "balanced"), ("2016×1344", 2016, 1344, "high")],
    "2:3":  [("720×1080", 720, 1080, "fast"), ("1024×1536", 1024, 1536, "balanced"), ("1344×2016", 1344, 2016, "high")],
    "21:9": [("1280×544", 1280, 544, "fast"), ("1920×816", 1920, 816, "balanced"), ("2560×1088", 2560, 1088, "high")],
}
# Real max side (px) each provider accepts. Cloud is NOT capped to the local budget.
_CLOUD_MAX_SIDE = {
    "pollinations": 1920,   # Sana via Pollinations
    "cloudflare":   2048,   # SDXL / SDXL-Lightning / DreamShaper / Leonardo
    "together":     1536,   # free FLUX.1-schnell endpoint
    "nebius":       2048,   # FLUX dev / SDXL (up to 2000²)
    "huggingface":  1536,   # hf-inference FLUX schnell / SD3
}

_DEFAULT_AR = "16:9"


def _ar_string(w: int, h: int) -> str:
    g = gcd(w, h) or 1
    return f"{w // g}:{h // g}"


def _pick_default(sizes: list[dict], default_ar: str) -> dict | None:
    """The entry to flag default:true — the 'balanced' tier of the default AR,
    else the largest available of that AR, else the first size overall."""
    pool = [s for s in sizes if s["aspect_ratio"] == default_ar]
    if not pool:
        return sizes[0] if sizes else None
    bal = next((s for s in pool if s.get("tier") == "balanced"), None)
    return bal or pool[-1]   # ladders are small→large within an AR


def build_sizes(m) -> dict:
    """Return {sizes, default_aspect_ratio, custom} for a catalog ModelEntry."""
    # Fixed-output models → a single real size.
    if not m.supports_custom_dimensions:
        w, h = (m.fixed_size or (1024, 1024))
        ar = _ar_string(w, h)
        return {
            "sizes": [{
                "aspect_ratio": ar, "label": f"{w}×{h}",
                "width": w, "height": h, "tier": "balanced",
                "fixed": True, "default": True,
            }],
            "default_aspect_ratio": ar,
            "custom": None,
        }

    if m.is_cloud:
        max_side = _CLOUD_MAX_SIDE.get(m.cloud_provider, 1536)
        sizes = [
            {"aspect_ratio": ar, "label": label, "width": w, "height": h, "tier": tier}
            for ar, ladder in _CLOUD_LADDERS.items()
            for (label, w, h, tier) in ladder
            if max(w, h) <= max_side
        ]
        custom = {"min_px": 512, "max_px": max_side, "step": 8, "max_pixels": max_side * max_side}
    else:
        sizes = [
            {"aspect_ratio": ar, "label": label, "width": w, "height": h, "tier": tier}
            for ar, ladder in _LOCAL_LADDERS.items()
            for (label, w, h, tier) in ladder
            if w * h <= _LOCAL_MAX_PIXELS + 50_000
        ]
        custom = dict(_LOCAL_CUSTOM)

    default_ar = _DEFAULT_AR if any(s["aspect_ratio"] == _DEFAULT_AR for s in sizes) \
        else (sizes[0]["aspect_ratio"] if sizes else _DEFAULT_AR)
    chosen = _pick_default(sizes, default_ar)
    if chosen:
        chosen["default"] = True

    return {"sizes": sizes, "default_aspect_ratio": default_ar, "custom": custom}
