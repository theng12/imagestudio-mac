"""
Persistent app settings.

Stored as JSON at `app/backend/settings.json` (gitignored). Currently holds
the Hugging Face token; structured as a dict so we can add more keys later
without rev-bumping the file format.

The token is read/written via the get_hf_token / set_hf_token helpers; the
download manager falls back to this token whenever the user doesn't pass an
explicit per-download token. Atomic writes (tmp → rename) so a crash mid-save
can't corrupt the file.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Optional


_PATH = Path(__file__).resolve().parent / "settings.json"
_LOCK = threading.Lock()

DEFAULTS: dict[str, Any] = {
    "hf_token": "",
    # Cloud-provider credentials (v1.6.0). Pollinations needs none; these are
    # only used by keyed providers (Cloudflare Workers AI, Together AI).
    "cloudflare_account_id": "",
    "cloudflare_api_token": "",
    "together_api_key": "",
}

# Cloud-provider credential mapping: provider id -> the settings keys it needs.
# Read by generation._generate_cloud to build the per-provider config dict.
CLOUD_CREDENTIAL_KEYS: dict[str, list[str]] = {
    "pollinations": [],
    "cloudflare": ["cloudflare_account_id", "cloudflare_api_token"],
    "together": ["together_api_key"],
}

_cache: dict[str, Any] = {}
_loaded = False


def _load_if_needed() -> None:
    global _cache, _loaded
    if _loaded:
        return
    try:
        if _PATH.exists():
            data = json.loads(_PATH.read_text())
            if isinstance(data, dict):
                _cache = {**DEFAULTS, **data}
            else:
                _cache = dict(DEFAULTS)
        else:
            _cache = dict(DEFAULTS)
    except Exception:
        _cache = dict(DEFAULTS)
    _loaded = True


def get(key: str) -> Any:
    with _LOCK:
        _load_if_needed()
        return _cache.get(key, DEFAULTS.get(key))


def set_value(key: str, value: Any) -> None:
    with _LOCK:
        _load_if_needed()
        _cache[key] = value
        tmp = _PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(_cache, indent=2))
        os.replace(tmp, _PATH)


def get_hf_token() -> Optional[str]:
    token = get("hf_token")
    if isinstance(token, str) and token.strip():
        return token.strip()
    return None


def set_hf_token(token: Optional[str]) -> None:
    set_value("hf_token", (token or "").strip())


def get_cloud_credentials(provider_id: str) -> dict:
    """Return {settings_key: value} for the given cloud provider's keys.
    Empty dict for providers that need no credentials (e.g. Pollinations)."""
    out: dict[str, str] = {}
    for k in CLOUD_CREDENTIAL_KEYS.get(provider_id, []):
        v = get(k)
        out[k] = v.strip() if isinstance(v, str) else (v or "")
    return out


def _mask(value: Optional[str]) -> str:
    """First 3 + last 4 chars, or bullets for short values; '' when empty."""
    if not value:
        return ""
    return value[:3] + "…" + value[-4:] if len(value) >= 10 else "•" * len(value)


def serialize_public() -> dict:
    """
    Caller-safe view: never includes a raw secret. Returns masked previews
    (first 3 + last 4 chars) so users can confirm the right values are saved.
    """
    token = get_hf_token()
    out: dict[str, Any] = {
        "hf_token_set": bool(token),
        "hf_token_masked": _mask(token),
    }
    # Cloud-provider credentials — masked status only, never the raw value.
    for key in ("cloudflare_account_id", "cloudflare_api_token", "together_api_key"):
        v = get(key)
        v = v.strip() if isinstance(v, str) else ""
        out[f"{key}_set"] = bool(v)
        out[f"{key}_masked"] = _mask(v)
    return out
