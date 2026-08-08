"""
Per-model output-size menus for GET /api/catalog (v1.17.0).

Story Studio (and any client) reads `sizes` to drive its aspect-ratio +
resolution pickers with ZERO pixel math — every entry is an exact, accepted
{width, height} the model/supplier will actually produce.

Rules implemented here:
  * Normal models → the approved GenStudio 1K/2K, /16-aligned ladder.
  * Fixed-output models (supports_custom_dimensions=False) → a single size with
    `fixed: true` (they ignore width/height and emit one model-chosen size).

Each size object:
    { aspect_ratio, label, width, height, tier, [default: true], [fixed: true] }

`tier` is the customer-facing quality label `1K` or `2K`.

build_sizes(model) returns:
    { "sizes": [...], "default_aspect_ratio": "16:9", "custom": {...} | None }
where `custom` (when present) describes the free-sizing range the model allows.
"""
from __future__ import annotations

from math import gcd

# ── Local ladders: approved GenStudio 1K/2K sizes, all /16-aligned ──
# (label, width, height, tier)
_LOCAL_LADDERS: dict[str, list[tuple[str, int, int, str]]] = {
    "16:9": [("1K", 1280, 720, "1K"), ("2K", 2560, 1440, "2K")],
    "9:16": [("1K", 720, 1280, "1K"), ("2K", 1440, 2560, "2K")],
    "1:1":  [("1K", 1024, 1024, "1K"), ("2K", 1984, 1984, "2K")],
    "4:3":  [("1K", 1152, 864, "1K"), ("2K", 2304, 1728, "2K")],
    "3:4":  [("1K", 864, 1152, "1K"), ("2K", 1728, 2304, "2K")],
    "3:2":  [("1K", 1200, 800, "1K"), ("2K", 2400, 1600, "2K")],
    "2:3":  [("1K", 800, 1200, "1K"), ("2K", 1600, 2400, "2K")],
    "5:4":  [("1K", 1120, 896, "1K"), ("2K", 2160, 1728, "2K")],
    "4:5":  [("1K", 896, 1120, "1K"), ("2K", 1728, 2160, "2K")],
    "21:9": [("1K", 1680, 720, "1K"), ("2K", 3024, 1296, "2K")],
    "2:1":  [("1K", 1408, 704, "1K"), ("2K", 2816, 1408, "2K")],
    "1:2":  [("1K", 704, 1408, "1K"), ("2K", 1408, 2816, "2K")],
}
_LOCAL_MAX_PIXELS = 4_000_000
_LOCAL_CUSTOM = {"min_px": 512, "max_px": 4096, "step": 16, "max_pixels": _LOCAL_MAX_PIXELS}


def local_default_presets() -> dict[str, tuple[int, int]]:
    """Return the approved 1K local canvases used by the generation endpoint.

    Keeping this derived from the catalog ladder prevents the Generate UI,
    ``/api/generate/availability``, and ``GET /api/catalog`` from drifting
    when a local preset changes.
    """
    return {
        aspect_ratio: (width, height)
        for aspect_ratio, ladder in _LOCAL_LADDERS.items()
        for _label, width, height, tier in ladder
        if tier == "1K"
    }


def local_aspect_options() -> list[dict]:
    """Return the ordered local ratio/resolution menu for Generate clients."""
    labels = {"16:9": "Wide", "9:16": "Tall", "1:1": "Square"}
    return [
        {
            "ratio": ratio,
            "label": labels.get(ratio, ratio),
            "width": ladder[0][1],
            "height": ladder[0][2],
            "resolution": ladder[0][3],
            "sizes": [
                {"resolution": tier, "label": label, "width": width, "height": height}
                for label, width, height, tier in ladder
            ],
        }
        for ratio, ladder in _LOCAL_LADDERS.items()
    ]

_DEFAULT_AR = "16:9"


def _ar_string(w: int, h: int) -> str:
    g = gcd(w, h) or 1
    return f"{w // g}:{h // g}"


def _pick_default(sizes: list[dict], default_ar: str) -> dict | None:
    """The entry to flag default:true — the '1K' tier of the default AR,
    else the largest available of that AR, else the first size overall."""
    pool = [s for s in sizes if s["aspect_ratio"] == default_ar]
    if not pool:
        return sizes[0] if sizes else None
    one_k = next((s for s in pool if s.get("tier") == "1K"), None)
    return one_k or pool[0]


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
