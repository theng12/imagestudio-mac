"""
LoRA discovery.

Scans `app/lora/` for `*.safetensors` files and surfaces them with basic
metadata (filename, size, mtime). The user drops LoRAs into that folder
manually for now — auto-import comes later.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable


LORA_DIR = Path(__file__).resolve().parent.parent / "lora"


def ensure_dir() -> Path:
    LORA_DIR.mkdir(parents=True, exist_ok=True)
    return LORA_DIR


def list_loras() -> list[dict]:
    ensure_dir()
    out: list[dict] = []
    for p in sorted(_iter_safetensors(LORA_DIR)):
        try:
            stat = p.stat()
        except FileNotFoundError:
            continue
        out.append({
            "name": p.stem,
            "filename": p.name,
            "path": str(p.resolve()),
            "size_bytes": stat.st_size,
            "modified": stat.st_mtime,
        })
    return out


def _iter_safetensors(root: Path) -> Iterable[Path]:
    if not root.exists():
        return
    for p in root.rglob("*.safetensors"):
        if p.is_file():
            yield p


def resolve_lora_path(name: str) -> Path | None:
    """Map a UI-supplied name (filename stem) back to an absolute path."""
    for p in _iter_safetensors(LORA_DIR):
        if p.stem == name:
            return p.resolve()
    return None
