"""
Hugging Face Inference Providers — text-to-image via the HF router. Uses the
SAME Hugging Face token the app already stores for downloads (Settings → Hugging
Face token), as long as that token has the "Inference Providers" permission.
Free users get a small monthly inference credit, so this is best as a
bring-your-own-token option rather than a default free provider.

    POST https://router.huggingface.co/hf-inference/models/{model}
    Authorization: Bearer {hf_token}
    body: {"inputs":"<prompt>","parameters":{"width":W,"height":H,
           "num_inference_steps":N,"negative_prompt":"...","seed":<int>}}
    -> raw image bytes (PNG/JPEG)

Honors width/height. Stdlib-only (no extra deps).

Docs: https://huggingface.co/docs/inference-providers/tasks/text-to-image
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Optional

from .base import CloudProvider, CloudRequest, CloudGenerationError

_ENDPOINT = "https://router.huggingface.co/hf-inference/models/{model}"
_DEFAULT_MODEL = "black-forest-labs/FLUX.1-schnell"
_TIMEOUT_S = 120


class HuggingFaceProvider(CloudProvider):
    id = "huggingface"
    # Reuses the app's existing Hugging Face token (also used for downloads).
    required_config = ("hf_token",)

    def generate(self, req: CloudRequest, config: Optional[dict] = None) -> bytes:
        config = config or {}
        token = (config.get("hf_token") or "").strip()
        if not token:
            raise CloudGenerationError(
                "Hugging Face cloud generation needs your HF token. Add it in "
                "Settings → Hugging Face token (the token needs the "
                "'Inference Providers' permission)."
            )
        prompt = (req.prompt or "").strip()
        if not prompt:
            raise CloudGenerationError("Hugging Face: empty prompt")

        model = req.model_id or _DEFAULT_MODEL
        params: dict = {"width": int(req.width), "height": int(req.height)}
        if req.seed is not None and req.seed >= 0:
            params["seed"] = int(req.seed)
        if req.negative_prompt:
            params["negative_prompt"] = req.negative_prompt
        body = {"inputs": prompt, "parameters": params}

        url = _ENDPOINT.format(model=model)
        http_req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "image/png",
                "User-Agent": "ImageStudioKH/1.0 (+pinokio)",
            },
        )
        try:
            with urllib.request.urlopen(http_req, timeout=_TIMEOUT_S) as resp:
                data = resp.read()
                ctype = resp.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:400]
            hint = ""
            if e.code in (401, 403):
                hint = (" — make sure your Hugging Face token has the "
                        "'Inference Providers' permission.")
            elif e.code == 503:
                hint = " — the model is warming up on Hugging Face; try again in a moment."
            raise CloudGenerationError(
                f"Hugging Face HTTP {e.code}: {detail}{hint}"
            ) from e
        except Exception as e:
            raise CloudGenerationError(
                f"Hugging Face request failed: {type(e).__name__}: {e}"
            ) from e

        # The router returns raw image bytes. If we got JSON instead, it's an
        # error/status payload (e.g. the model loading) — surface it.
        if "application/json" in ctype or data[:1] == b"{":
            try:
                payload = json.loads(data.decode("utf-8", "replace"))
            except Exception:
                payload = {"raw": data[:200].decode("utf-8", "replace")}
            raise CloudGenerationError(
                f"Hugging Face returned no image: {str(payload)[:300]}"
            )
        if not data:
            raise CloudGenerationError("Hugging Face returned an empty response.")
        return data
