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
    # Cloud-provider credentials (v1.13.0).
    "gemini_api_key": "",
    "nebius_api_key": "",
}

# Cloud-provider credential mapping: provider id -> the settings keys it needs.
# Read by generation._generate_cloud to build the per-provider config dict.
# Note: huggingface reuses the app's existing `hf_token` (also used for
# downloads) — no separate key, so a token set for downloads also unlocks HF
# cloud generation (as long as it has the "Inference Providers" permission).
CLOUD_CREDENTIAL_KEYS: dict[str, list[str]] = {
    "pollinations": [],
    "cloudflare": ["cloudflare_account_id", "cloudflare_api_token"],
    "together": ["together_api_key"],
    "gemini": ["gemini_api_key"],
    "nebius": ["nebius_api_key"],
    "huggingface": ["hf_token"],
}

_cache: dict[str, Any] = {}
_loaded = False


def _secure_permissions(path: Path) -> None:
    """Keep provider credentials readable only by the current user."""
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _load_if_needed() -> None:
    global _cache, _loaded
    if _loaded:
        return
    try:
        if _PATH.exists():
            _secure_permissions(_PATH)
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
        _secure_permissions(tmp)
        os.replace(tmp, _PATH)
        _secure_permissions(_PATH)


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


# Human-readable name for the credential a keyed provider needs — used to build
# the "Add your <X> in Settings" hint surfaced in the catalog (fit.hint).
CLOUD_CREDENTIAL_LABELS: dict[str, str] = {
    "cloudflare": "Cloudflare Account ID + API token",
    "together": "Together API key",
    "gemini": "Google AI Studio (Gemini) API key",
    "nebius": "Nebius API key",
    "huggingface": "Hugging Face token (with Inference Providers permission)",
}

# Display name for each cloud provider — surfaced on model cards as "via <name>".
CLOUD_PROVIDER_LABELS: dict[str, str] = {
    "pollinations": "Pollinations",
    "cloudflare": "Cloudflare Workers AI",
    "together": "Together AI",
    "gemini": "Google AI Studio",
    "nebius": "Nebius AI Studio",
    "huggingface": "Hugging Face",
}

# Where a user goes to get the credential (or, for keyless providers, to learn
# about the service). Surfaced in the catalog as `cloud_signup_url` so the UI —
# and downstream consumers like Story Studio — can link straight to it from the
# "needs API key" state instead of making the user hunt for the dashboard.
CLOUD_CREDENTIAL_URLS: dict[str, str] = {
    "pollinations": "https://pollinations.ai",
    "cloudflare": "https://dash.cloudflare.com/profile/api-tokens",
    "together": "https://api.together.ai/settings/api-keys",
    "gemini": "https://aistudio.google.com/apikey",
    "nebius": "https://studio.nebius.com/settings/api-keys",
    # Deep link that pre-selects the "Inference Providers" permission HF needs.
    "huggingface": "https://huggingface.co/settings/tokens/new?ownUserPermissions=inference.serverless.write&tokenType=fineGrained",
}


def cloud_provider_label(provider_id: Optional[str]) -> str:
    """Human-readable provider name, e.g. 'Together AI'. Falls back to the id."""
    return CLOUD_PROVIDER_LABELS.get(provider_id or "", (provider_id or "").title())


def cloud_signup_url(provider_id: Optional[str]) -> str:
    """URL where the user gets this provider's credential (or learns about it).
    Empty string for unknown providers."""
    return CLOUD_CREDENTIAL_URLS.get(provider_id or "", "")


def cloud_credentials_ok(provider_id: Optional[str]) -> bool:
    """True when EVERY credential the provider needs is set (non-empty).

    Always True for providers that need none (e.g. Pollinations → empty key
    list). This mirrors exactly what the provider classes check before a
    request, so 'ok' here means 'won't fail at generate-time for a missing
    credential'. Unknown/None provider → treat as not-ok (can't verify)."""
    if not provider_id or provider_id not in CLOUD_CREDENTIAL_KEYS:
        return False
    for k in CLOUD_CREDENTIAL_KEYS[provider_id]:
        v = get(k)
        if not (isinstance(v, str) and v.strip()):
            return False
    return True


def cloud_credentials_hint(provider_id: Optional[str]) -> str:
    """One-line setup hint for a cloud model whose credential is missing."""
    label = CLOUD_CREDENTIAL_LABELS.get(provider_id or "", "API credentials")
    return f"Add your {label} in Settings to use this model."


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
    for key in ("cloudflare_account_id", "cloudflare_api_token", "together_api_key",
                "gemini_api_key", "nebius_api_key"):
        v = get(key)
        v = v.strip() if isinstance(v, str) else ""
        out[f"{key}_set"] = bool(v)
        out[f"{key}_masked"] = _mask(v)
    return out
