"""
Cloudflare Workers AI provider — free tier (10k neurons/day), needs a free
Cloudflare Account ID + API token (set in Settings).

    POST https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model_id}
    Authorization: Bearer {api_token}

Workers AI hosts several text-to-image models with DIFFERENT request/response
shapes, so this provider handles both:

  * FLUX.1 [schnell] (@cf/black-forest-labs/flux-1-schnell)
      body: {"prompt": "...", "steps": <=8, "seed": <int>}   (no width/height)
      -> {"result": {"image": "<base64 jpeg>"}, "success": true}   (JSON+base64)

  * Stable Diffusion family (SDXL base, SDXL-Lightning, DreamShaper, …)
      body: {"prompt": "...", "width": W, "height": H, "num_steps": <=20,
             "negative_prompt": "...", "seed": <int>}
      -> raw PNG bytes (binary)

We detect the response by Content-Type / magic bytes and return image bytes
either way. The model is chosen by the catalog entry's `cloud_model_id`.
Stdlib-only (no extra deps).

Docs: https://developers.cloudflare.com/workers-ai/models/ (filter: Text-to-Image)
"""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from typing import Optional

from .base import CloudProvider, CloudRequest, CloudGenerationError

_ENDPOINT = (
    "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model_id}"
)
_DEFAULT_MODEL = "@cf/black-forest-labs/flux-1-schnell"
_TIMEOUT_S = 120


def _build_body(model_id: str, req: CloudRequest) -> dict:
    """Per-model request body. FLUX schnell takes prompt+steps (fixed size);
    the SD-family models take width/height/num_steps/negative_prompt."""
    m = (model_id or "").lower()
    prompt = (req.prompt or "").strip()
    if "flux" in m:
        body: dict = {"prompt": prompt, "steps": 8}  # schnell caps at 8
        if req.seed is not None and req.seed >= 0:
            body["seed"] = int(req.seed)
        return body
    # Everything else (SDXL, SDXL-Lightning, DreamShaper, Leonardo Lucid/Phoenix)
    # honors width/height. num_steps caps at 20 for the SD models; the distilled
    # Lightning/LCM models only need a handful of steps.
    body = {
        "prompt": prompt,
        "width": int(req.width),
        "height": int(req.height),
        "num_steps": 8 if ("lightning" in m or "lcm" in m) else 20,
    }
    # negative_prompt is accepted by the SD models + Leonardo Phoenix, but NOT by
    # Leonardo Lucid Origin (its endpoint rejects unknown params) — so skip it there.
    if req.negative_prompt and "lucid" not in m:
        body["negative_prompt"] = req.negative_prompt
    if req.seed is not None and req.seed >= 0:
        body["seed"] = int(req.seed)
    return body


def _looks_like_image(data: bytes, ctype: str) -> bool:
    if "image" in (ctype or "").lower():
        return True
    return data[:8].startswith(b"\x89PNG") or data[:3] == b"\xff\xd8\xff"


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
        if not (req.prompt or "").strip():
            raise CloudGenerationError("Cloudflare: empty prompt")

        model_id = req.model_id or _DEFAULT_MODEL
        body = _build_body(model_id, req)

        url = _ENDPOINT.format(account_id=account_id, model_id=model_id)
        http_req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json, image/*",
                "User-Agent": "ImageStudioKH/1.0 (+pinokio)",
            },
        )
        try:
            with urllib.request.urlopen(http_req, timeout=_TIMEOUT_S) as resp:
                data = resp.read()
                ctype = resp.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:300]
            raise CloudGenerationError(f"Cloudflare HTTP {e.code}: {detail}") from e
        except Exception as e:
            raise CloudGenerationError(
                f"Cloudflare request failed: {type(e).__name__}: {e}"
            ) from e

        # SD-family models return the PNG directly.
        if _looks_like_image(data, ctype):
            return data

        # Otherwise it's the JSON envelope ({"result":{"image":"<b64>"}}), or an
        # error payload.
        try:
            payload = json.loads(data.decode("utf-8"))
        except Exception as e:
            raise CloudGenerationError(
                f"Cloudflare returned an unrecognized response "
                f"(Content-Type={ctype!r}): {data[:200]!r}"
            ) from e
        if isinstance(payload, dict) and payload.get("success") is False:
            raise CloudGenerationError(f"Cloudflare error: {payload.get('errors')}")
        b64 = (payload.get("result") or {}).get("image") or payload.get("image")
        if not b64:
            raise CloudGenerationError(
                f"Cloudflare returned no image: {str(payload)[:200]}"
            )
        try:
            return base64.b64decode(b64)
        except Exception as e:
            raise CloudGenerationError(f"Cloudflare image not valid base64: {e}") from e
