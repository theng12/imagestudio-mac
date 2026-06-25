"""
Cloud image-generation providers.

Catalog entries with provider="cloud" route through here instead of mflux.
Add a new provider by implementing CloudProvider and registering it in
`_REGISTRY` below, then add a catalog ModelEntry with the matching
`cloud_provider` id.

Providers use ONLY the Python stdlib (urllib) so the cloud path works even
without the heavy mflux/MLX generation install — a free cloud image is just
an HTTP request.
"""
from __future__ import annotations

from typing import Optional

from .base import CloudProvider, CloudRequest, CloudGenerationError
from .pollinations import PollinationsProvider
from .cloudflare import CloudflareProvider
from .together import TogetherProvider

_REGISTRY: dict[str, CloudProvider] = {
    "pollinations": PollinationsProvider(),
    "cloudflare": CloudflareProvider(),
    "together": TogetherProvider(),
}


def get_provider(provider_id: str) -> Optional[CloudProvider]:
    """Return the registered provider for `provider_id`, or None."""
    return _REGISTRY.get(provider_id)


__all__ = [
    "get_provider",
    "CloudProvider",
    "CloudRequest",
    "CloudGenerationError",
]
