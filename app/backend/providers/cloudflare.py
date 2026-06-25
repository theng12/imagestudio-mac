"""
Cloudflare Workers AI provider — free tier (10k neurons/day), needs a free
Cloudflare Account ID + API token (set in Settings).

    POST https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/black-forest-labs/flux-1-schnell
    Authorization: Bearer {api_token}
    body: {"prompt": "...", "steps": <=8, "seed": <int>}
    -> {"result": {"image": "<base64 jpeg>"}, "success": true, ...}

Note: the Workers AI flux-1-schnell endpoint has NO width/height params — output
size is fixed by Cloudflare. Stdlib-only (no extra deps).

Docs: https://developers.cloudflare.com/workers-ai/models/flux-1-schnell/
"""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from typing import Optional

from .base import CloudProvider, CloudRequest, CloudGenerationError

_ENDPOINT = (
    "https://api.cloudflare.com/client/v4/accounts/{account_id}"
    "/ai/run/@cf/black-forest-labs/flux-1-schnell"
)
_TIMEOUT_S = 120
_MAX_STEPS = 8   # Workers AI caps schnell at 8 steps


class CloudflareProvider(CloudProvider):
    id = "cloudflare"
    required_config = ("cloudflare_account_id", "cloudflare_api_token")

    def generate(self, req: CloudRequest, config: Optional[dict] = None) -> bytes:
        config = config or {}
        account_id = (config.get("cloudflare_account_id") or "").strip()
        token = (config.get("cloudflare_api_token") or "").strip()
        if not account_id or not token:
            raise CloudGenerationError(
                "Cloudflare needs an Account ID + API token. Add them in Settings "
                "→ Cloud provider keys."
            )
        prompt = (req.prompt or "").strip()
        if not prompt:
            raise CloudGenerationError("Cloudflare: empty prompt")

        body = {"prompt": prompt, "steps": _MAX_STEPS}
        if req.seed is not None and req.seed >= 0:
            body["seed"] = int(req.seed)

        url = _ENDPOINT.format(account_id=account_id)
        http_req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "ImageStudioKH/1.0 (+pinokio)",
            },
        )
        try:
            with urllib.request.urlopen(http_req, timeout=_TIMEOUT_S) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:300]
            raise CloudGenerationError(f"Cloudflare HTTP {e.code}: {detail}") from e
        except Exception as e:
            raise CloudGenerationError(
                f"Cloudflare request failed: {type(e).__name__}: {e}"
            ) from e

        if isinstance(payload, dict) and payload.get("success") is False:
            raise CloudGenerationError(f"Cloudflare error: {payload.get('errors')}")
        # Envelope is {"result": {"image": "<b64>"}}; tolerate a flat {"image": …}.
        b64 = (payload.get("result") or {}).get("image") or payload.get("image")
        if not b64:
            raise CloudGenerationError(
                f"Cloudflare returned no image: {str(payload)[:200]}"
            )
        try:
            return base64.b64decode(b64)
        except Exception as e:
            raise CloudGenerationError(f"Cloudflare image not valid base64: {e}") from e
