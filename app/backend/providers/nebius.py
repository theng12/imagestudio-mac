"""
Nebius AI Studio provider — OpenAI-compatible image generation. New accounts get
free trial credits (no credit card) covering FLUX schnell, FLUX dev, and SDXL.
Needs a Nebius API key (set in Settings).

    POST https://api.studio.nebius.com/v1/images/generations
    Authorization: Bearer {api_key}
    body: {"model":"black-forest-labs/flux-dev","prompt":"...",
           "response_format":"b64_json","response_extension":"png",
           "width":W,"height":H,"num_inference_steps":N,"seed":<int>}
    -> {"data":[{"b64_json":"..."}]}   (or {"url":"..."} as a fallback)

Honors width/height. Stdlib-only (no extra deps).

Docs: https://docs.nebius.com/studio/inference/
"""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from typing import Optional

from .base import CloudProvider, CloudRequest, CloudGenerationError

_ENDPOINT = "https://api.studio.nebius.com/v1/images/generations"
_DEFAULT_MODEL = "black-forest-labs/flux-dev"
_TIMEOUT_S = 120


def _steps_for(model_id: str) -> int:
    """Sensible step count per model — schnell is a few-step distilled model,
    dev/SDXL want more."""
    m = (model_id or "").lower()
    if "schnell" in m:
        return 4
    if "sdxl" in m:
        return 25
    return 28  # flux-dev and friends


class NebiusProvider(CloudProvider):
    id = "nebius"
    required_config = ("nebius_api_key",)

    def generate(self, req: CloudRequest, config: Optional[dict] = None) -> bytes:
        config = config or {}
        api_key = (config.get("nebius_api_key") or "").strip()
        if not api_key:
            raise CloudGenerationError(
                "Nebius needs an API key. Add it in Settings → Cloud provider keys."
            )
        prompt = (req.prompt or "").strip()
        if not prompt:
            raise CloudGenerationError("Nebius: empty prompt")

        model = req.model_id or _DEFAULT_MODEL
        body = {
            "model": model,
            "prompt": prompt,
            "response_format": "b64_json",
            "response_extension": "png",
            "width": int(req.width),
            "height": int(req.height),
            "num_inference_steps": _steps_for(model),
        }
        if req.seed is not None and req.seed >= 0:
            body["seed"] = int(req.seed)
        if req.negative_prompt:
            body["negative_prompt"] = req.negative_prompt

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
            detail = e.read().decode("utf-8", "replace")[:400]
            raise CloudGenerationError(f"Nebius HTTP {e.code}: {detail}") from e
        except Exception as e:
            raise CloudGenerationError(
                f"Nebius request failed: {type(e).__name__}: {e}"
            ) from e

        data_arr = payload.get("data") or []
        if not data_arr:
            raise CloudGenerationError(f"Nebius returned no data: {str(payload)[:200]}")
        item = data_arr[0]

        b64 = item.get("b64_json")
        if b64:
            try:
                return base64.b64decode(b64)
            except Exception as e:
                raise CloudGenerationError(f"Nebius image not valid base64: {e}") from e

        url = item.get("url")
        if url:
            try:
                with urllib.request.urlopen(url, timeout=_TIMEOUT_S) as r2:
                    return r2.read()
            except Exception as e:
                raise CloudGenerationError(f"Nebius image URL fetch failed: {e}") from e

        raise CloudGenerationError(
            f"Nebius returned neither b64_json nor url: {str(item)[:200]}"
        )
