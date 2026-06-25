"""
Base types for cloud image-generation providers.

Local models run through mflux (see generation.py). Cloud models — catalog
entries with provider="cloud" — route here instead. Each provider is a thin
client that takes a prompt + dimensions and returns ENCODED image bytes (PNG or
JPEG) which the caller writes straight to disk.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


class CloudGenerationError(RuntimeError):
    """Raised when a cloud provider fails to return a usable image."""


@dataclass
class CloudRequest:
    prompt: str
    width: int
    height: int
    seed: Optional[int] = None
    model_id: Optional[str] = None       # provider-specific model name
    negative_prompt: Optional[str] = None


class CloudProvider:
    """Interface every cloud provider implements. `generate` returns encoded
    image bytes the caller persists as-is (or normalises to PNG).

    `config` carries provider-specific credentials/settings (e.g. an API key),
    resolved from app settings by the caller. Keyless providers ignore it.
    `required_config` lists the settings keys a provider needs so callers can
    surface a clear "set this in Settings" message.
    """

    id: str = "base"
    required_config: tuple[str, ...] = ()

    def generate(self, req: CloudRequest, config: Optional[dict] = None) -> bytes:  # pragma: no cover - interface
        raise NotImplementedError
