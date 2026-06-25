"""
Together AI provider — the FLUX.1 [schnell] Free endpoint is free with a (free)
Together API key (set in Settings).

    POST https://api.together.xyz/v1/images/generations
    Authorization: Bearer {api_key}
    body: {"model": "...", "prompt": "...", "width": W, "height": H,
           "steps": <=4 (free), "n": 1, "response_format": "b64_json", "seed": <int>}
    -> {"data": [{"b64_json": "..."}]}   (or {"url": "..."} as a fallback)

Unlike Cloudflare's schnell endpoint, Together honors width/height. Stdlib-only.

Docs: https://docs.together.ai/docs/images-overview
"""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from typing import Optional

from .base import CloudProvider, CloudRequest, CloudGenerationError

_ENDPOINT = "https://api.together.xyz/v1/images/generations"
_TIMEOUT_S = 120
_FREE_MAX_STEPS = 4   # the FLUX.1-schnell-Free endpoint caps at 4 steps


class TogetherProvider(CloudProvider):
    id = "together"
    required_config = ("together_api_key",)

    def generate(self, req: CloudRequest, config: Optional[dict] = None) -> bytes:
        config = config or {}
        api_key = (config.get("together_api_key") or "").strip()
        if not api_key:
            raise CloudGenerationError(
                "Together needs an API key. Add it in Settings → Cloud provider keys."
            )
        prompt = (req.prompt or "").strip()
        if not prompt:
            raise CloudGenerationError("Together: empty prompt")

        body = {
            "model": req.model_id or "black-forest-labs/FLUX.1-schnell-Free",
            "prompt": prompt,
            "width": int(req.width),
            "height": int(req.height),
            "steps": _FREE_MAX_STEPS,
            "n": 1,
            "response_format": "b64_json",
        }
        if req.seed is not None and req.seed >= 0:
            body["seed"] = int(req.seed)

        http_req = urllib.request.Request(
            _ENDPOINT,
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
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
            raise CloudGenerationError(f"Together HTTP {e.code}: {detail}") from e
        except Exception as e:
            raise CloudGenerationError(
                f"Together request failed: {type(e).__name__}: {e}"
            ) from e

        data_arr = payload.get("data") or []
        if not data_arr:
            raise CloudGenerationError(f"Together returned no data: {str(payload)[:200]}")
        item = data_arr[0]

        b64 = item.get("b64_json")
        if b64:
            try:
                return base64.b64decode(b64)
            except Exception as e:
                raise CloudGenerationError(f"Together image not valid base64: {e}") from e

        # Fallback: the API returned a URL instead of inline base64.
        url = item.get("url")
        if url:
            try:
                with urllib.request.urlopen(url, timeout=_TIMEOUT_S) as r2:
                    return r2.read()
            except Exception as e:
                raise CloudGenerationError(f"Together image URL fetch failed: {e}") from e

        raise CloudGenerationError(
            f"Together returned neither b64_json nor url: {str(item)[:200]}"
        )
