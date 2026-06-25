"""
Pollinations.ai provider — free, no API key required.

Pollinations exposes a stable image endpoint where the prompt is URL-path
encoded and generation params are query args:

    GET https://image.pollinations.ai/prompt/<urlencoded prompt>?width=&height=&model=&seed=

The response body is the image itself. Uses only the stdlib so the cloud path
works without the heavy mflux/MLX generation install.

Docs: https://enter.pollinations.ai/api/docs
"""
from __future__ import annotations

import urllib.parse
import urllib.request
from typing import Optional

from .base import CloudProvider, CloudRequest, CloudGenerationError

_BASE = "https://image.pollinations.ai/prompt/"
_TIMEOUT_S = 120


class PollinationsProvider(CloudProvider):
    id = "pollinations"

    def generate(self, req: CloudRequest, config: Optional[dict] = None) -> bytes:
        prompt = (req.prompt or "").strip()
        if not prompt:
            raise CloudGenerationError("Pollinations: empty prompt")

        # Path-encode the prompt; encode "/" too so it stays one path segment.
        encoded = urllib.parse.quote(prompt, safe="")
        query = {
            "width": int(req.width),
            "height": int(req.height),
            "model": req.model_id or "flux",
            "nologo": "true",
            # Keep generations out of the public feed.
            "private": "true",
        }
        if req.seed is not None and req.seed >= 0:
            query["seed"] = int(req.seed)

        url = _BASE + encoded + "?" + urllib.parse.urlencode(query)
        http_req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "ImageStudioKH/1.0 (+pinokio)",
                "Accept": "image/*",
            },
        )
        try:
            with urllib.request.urlopen(http_req, timeout=_TIMEOUT_S) as resp:
                data = resp.read()
                ctype = resp.headers.get("Content-Type", "")
        except Exception as e:  # urllib raises a variety of error types
            raise CloudGenerationError(
                f"Pollinations request failed: {type(e).__name__}: {e}"
            ) from e

        if not data:
            raise CloudGenerationError("Pollinations returned an empty response")
        if "image" not in ctype.lower():
            # Pollinations returns text/plain on some error / rate-limit cases.
            snippet = data[:200].decode("utf-8", "replace")
            raise CloudGenerationError(
                f"Pollinations did not return an image "
                f"(Content-Type={ctype!r}): {snippet}"
            )
        return data
