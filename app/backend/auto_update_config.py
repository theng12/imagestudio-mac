"""Image Studio's fixed, non-user-editable updater identity."""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from .auto_update import AutoUpdater


ROOT = Path(__file__).resolve().parents[2]
SPEC = {
    "root": str(ROOT),
    "title": "Image Studio KH",
    "slug": "imagestudio",
    "expected_remote": "https://github.com/theng12/imagestudio-mac.git",
    "branch": "main",
    "port": 47868,
    "server_label": "com.kh.imagestudio.server",
    "watchdog_label": "com.kh.imagestudio.watchdog",
    "default_hour": 4,
    "default_weekday": 6,
    "verify_module": "backend.main",
    "generation_marker": "mflux",
    "generation_requirements": "requirements-generation.lock.txt",
}


def create_updater(readiness: Optional[Callable[[], list[str]]] = None, **kwargs) -> AutoUpdater:
    return AutoUpdater(SPEC, readiness=readiness, **kwargs)
