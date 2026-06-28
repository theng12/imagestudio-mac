"""
Google AI Studio (Gemini) provider — Gemini 2.5 Flash Image ("Nano Banana").
Generous permanent free tier (no credit card) with just a Google AI Studio API
key (set in Settings).

    POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
    x-goog-api-key: {api_key}
    body: {"contents":[{"parts":[{"text":"<prompt>"}]}]}
    -> candidates[].content.parts[] -> the part with inlineData.data (base64 image)

The image model returns an image part by default; we scan all parts for the
first inlineData and decode it. Output size is model-determined (~1024px) — the
width/height controls are ignored (like Cloudflare's schnell endpoint), and the
generation isn't seed-deterministic. Stdlib-only (no extra deps).

Docs: https://ai.google.dev/gemini-api/docs/image-generation
"""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from typing import Optional

from .base import CloudProvider, CloudRequest, CloudGenerationError

_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
_DEFAULT_MODEL = "gemini-2.5-flash-image"
_TIMEOUT_S = 120


class GeminiProvider(CloudProvider):
    id = "gemini"
    required_config = ("gemini_api_key",)

    def generate(self, req: CloudRequest, config: Optional[dict] = None) -> bytes:
        config = config or {}
        api_key = (config.get("gemini_api_key") or "").strip()
        if not api_key:
            raise CloudGenerationError(
                "Gemini needs an API key. Add it in Settings → Cloud provider keys."
            )
        prompt = (req.prompt or "").strip()
        if not prompt:
            raise CloudGenerationError("Gemini: empty prompt")

        model = req.model_id or _DEFAULT_MODEL
        body = {"contents": [{"parts": [{"text": prompt}]}]}

        url = _ENDPOINT.format(model=model)
        http_req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers={
                "x-goog-api-key": api_key,
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
            # 429 on the free tier means billing isn't enabled — Gemini image
            # generation has a free-tier quota of 0. Give an actionable message.
            if e.code == 429 and ("free_tier" in detail or "quota" in detail.lower()):
                raise CloudGenerationError(
                    "Gemini image generation needs billing enabled on your Google "
                    "AI Studio / Cloud account — the free tier allows 0 image "
                    "requests (HTTP 429 quota exceeded). Enable billing at "
                    "https://aistudio.google.com/ (or switch to a free model like "
                    "Pollinations / Cloudflare SDXL)."
                ) from e
            raise CloudGenerationError(f"Gemini HTTP {e.code}: {detail}") from e
        except Exception as e:
            raise CloudGenerationError(
                f"Gemini request failed: {type(e).__name__}: {e}"
            ) from e

        # Scan candidates[].content.parts[] for the first inline image.
        for cand in (payload.get("candidates") or []):
            for part in ((cand.get("content") or {}).get("parts") or []):
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and inline.get("data"):
                    try:
                        return base64.b64decode(inline["data"])
                    except Exception as e:
                        raise CloudGenerationError(
                            f"Gemini image not valid base64: {e}"
                        ) from e

        # No image part — surface any safety/block feedback to help the user.
        fb = payload.get("promptFeedback") or {}
        block = fb.get("blockReason")
        raise CloudGenerationError(
            "Gemini returned no image"
            + (f" (blocked: {block})" if block else "")
            + f": {str(payload)[:200]}"
        )
