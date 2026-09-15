"""
HF cache inspection.

Pure-ish functions that look at the on-disk Hugging Face cache and answer:
- where is HF_HOME for this server?
- is repo X fully cached, partially cached, or absent?
- what's the on-disk size of repo X?
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Optional


def hf_home() -> Path:
    """
    Resolve HF_HOME the same way huggingface_hub does, but as an absolute path.
    Defaults match the library's defaults so we agree with `hf download`.
    """
    raw = os.environ.get("HF_HOME") or os.environ.get("HUGGINGFACE_HUB_CACHE")
    if raw:
        return Path(raw).expanduser().resolve()
    # huggingface_hub default
    return (Path.home() / ".cache" / "huggingface").resolve()


def hub_dir() -> Path:
    return hf_home() / "hub"


def repo_cache_dir(repo: str) -> Path:
    """HF cache folder name for a repo, e.g. 'org/name' -> 'models--org--name'."""
    safe = "models--" + repo.replace("/", "--")
    return hub_dir() / safe


def has_incomplete(repo: str) -> bool:
    blobs = repo_cache_dir(repo) / "blobs"
    if not blobs.exists():
        return False
    try:
        for entry in blobs.iterdir():
            if entry.name.endswith(".incomplete"):
                return True
    except FileNotFoundError:
        return False
    return False


def has_any_snapshot(repo: str) -> bool:
    snaps = repo_cache_dir(repo) / "snapshots"
    if not snaps.exists():
        return False
    try:
        return any(snaps.iterdir())
    except FileNotFoundError:
        return False


# Recognized model-weight extensions. A snapshot that contains only README /
# LICENSE / .gitattributes is NOT actually usable, so cache_state() now
# requires at least one file with one of these extensions before reporting
# "cached". This catches the silent-partial-download failure mode for gated
# repos where the user hasn't accepted the license / provided a token: HF
# downloads the public LICENSE.md + README.md (which create a snapshot dir
# and make has_any_snapshot() return True) but skips the actual weights.
_WEIGHT_EXTENSIONS = (
    ".safetensors", ".bin", ".ckpt", ".gguf",
    ".pt", ".pth", ".npz", ".mlpackage",
)

MODEL_FILES_UNAVAILABLE = "MODEL_FILES_UNAVAILABLE"
MODEL_FILES_UNAVAILABLE_REASON = (
    "One or more required model files are missing or unreadable."
)


class ModelFilesUnavailable(RuntimeError):
    error_code = MODEL_FILES_UNAVAILABLE

    def __init__(self, reason: str = MODEL_FILES_UNAVAILABLE_REASON) -> None:
        self.reason = reason
        super().__init__(f"{self.error_code}: {reason}")


def has_weight_files(repo: str) -> bool:
    """True if any snapshot under this repo contains at least one file with
    a recognized weight extension. Walks subdirectories because diffusers
    repos keep weights inside component dirs (transformer/, vae/, etc.) and
    huge models shard weights across multiple files."""
    snaps = repo_cache_dir(repo) / "snapshots"
    if not snaps.exists():
        return False
    try:
        for snap in snaps.iterdir():
            if not snap.is_dir():
                continue
            for path in snap.rglob("*"):
                name = path.name
                if name.endswith(".incomplete"):
                    continue
                lower = name.lower()
                if any(lower.endswith(ext) for ext in _WEIGHT_EXTENSIONS):
                    return True
    except (FileNotFoundError, PermissionError):
        return False
    return False


def snapshot_revision(repo: str) -> str | None:
    """Return the immutable cached commit used for inference, never a moving alias."""
    refs_main = repo_cache_dir(repo) / "refs" / "main"
    try:
        revision = refs_main.read_text().strip()
    except (FileNotFoundError, PermissionError, OSError):
        return None
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        return None
    snapshot = repo_cache_dir(repo) / "snapshots" / revision
    return revision if snapshot.is_dir() else None


def snapshot_path(repo: str, revision: str | None) -> Path | None:
    """Resolve an immutable cached snapshot without following a moving ref."""
    if not revision or not re.fullmatch(r"[0-9a-f]{40}", revision):
        return None
    snapshot = repo_cache_dir(repo) / "snapshots" / revision
    return snapshot.resolve() if snapshot.is_dir() else None


def _weight_path(path: Path) -> bool:
    lower = path.name.lower()
    return any(lower.endswith(ext) for ext in _WEIGHT_EXTENSIONS)


def _readable_nonempty(path: Path) -> bool:
    """Probe availability without hashing or reading a multi-GB weight."""
    try:
        with path.open("rb") as handle:
            return bool(handle.read(1))
    except (OSError, ValueError):
        return False


def _indexed_weight_paths(snapshot: Path) -> tuple[set[Path], bool]:
    """Return every shard named by safetensors indexes in this snapshot.

    An index is the source of truth for sharded checkpoints: finding one good
    shard is insufficient when its companion is absent. Index files are small
    metadata, so reading them is bounded and avoids hashing any model weight.
    """
    required: set[Path] = set()
    try:
        indexes = tuple(snapshot.rglob("*.safetensors.index.json"))
    except (FileNotFoundError, PermissionError, OSError):
        return required, False
    for index in indexes:
        try:
            with index.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            return required, False
        weight_map = payload.get("weight_map") if isinstance(payload, dict) else None
        if not isinstance(weight_map, dict) or not weight_map:
            return required, False
        for relative in weight_map.values():
            if not isinstance(relative, str):
                return required, False
            shard = Path(relative)
            if shard.is_absolute() or ".." in shard.parts:
                return required, False
            required.add(index.parent / shard)
    return required, True


def model_files_readiness(repo: str, revision: str | None = None) -> dict:
    """Verify that an immutable snapshot's required weight shards can be opened.

    This deliberately reads only safetensors index metadata plus one byte from
    each weight file. It detects missing shards, dangling cache symlinks, empty
    files, and read/permission failures without checksumming model contents on
    the catalog polling path.
    """
    actual_revision = revision or snapshot_revision(repo)
    snapshot = snapshot_path(repo, actual_revision)
    if snapshot is None:
        return {
            "ready": False,
            "revision": actual_revision,
            "error_code": MODEL_FILES_UNAVAILABLE,
            "reason": MODEL_FILES_UNAVAILABLE_REASON,
        }

    indexed, indexes_ok = _indexed_weight_paths(snapshot)
    try:
        discovered = {path for path in snapshot.rglob("*") if _weight_path(path)}
    except (FileNotFoundError, PermissionError, OSError):
        discovered = set()
        indexes_ok = False
    required = indexed | discovered
    ready = indexes_ok and bool(required) and all(_readable_nonempty(path) for path in required)
    return {
        "ready": ready,
        "revision": actual_revision,
        "error_code": None if ready else MODEL_FILES_UNAVAILABLE,
        "reason": None if ready else MODEL_FILES_UNAVAILABLE_REASON,
    }


def require_model_files(repo: str, revision: str | None = None) -> dict:
    readiness = model_files_readiness(repo, revision)
    if not readiness["ready"]:
        raise ModelFilesUnavailable(str(readiness["reason"]))
    return readiness


def cache_state(repo: str) -> str:
    """
    Returns one of: 'absent', 'partial', 'cached'.
    'partial' means there are .incomplete blobs, a started but unfinished
    snapshot, or a snapshot that has no actual weight files (the gated-repo
    partial-download failure mode — see has_weight_files()).
    """
    if not repo_cache_dir(repo).exists():
        return "absent"
    if has_incomplete(repo):
        return "partial"
    if has_any_snapshot(repo):
        # A snapshot exists, but it must contain real model weights — not
        # just LICENSE.md / README.md / .gitattributes — to count as cached.
        return "cached" if has_weight_files(repo) else "partial"
    return "partial"


def disk_bytes(repo: str) -> int:
    """Total bytes used by all real blobs of this repo (excludes .incomplete)."""
    blobs = repo_cache_dir(repo) / "blobs"
    if not blobs.exists():
        return 0
    total = 0
    try:
        for entry in blobs.iterdir():
            if entry.name.endswith(".incomplete"):
                continue
            try:
                total += entry.stat().st_size
            except (FileNotFoundError, PermissionError):
                continue
    except FileNotFoundError:
        return 0
    return total


def incomplete_bytes(repo: str) -> int:
    """Total bytes currently held by .incomplete partial files."""
    blobs = repo_cache_dir(repo) / "blobs"
    if not blobs.exists():
        return 0
    total = 0
    try:
        for entry in blobs.iterdir():
            if not entry.name.endswith(".incomplete"):
                continue
            try:
                total += entry.stat().st_size
            except (FileNotFoundError, PermissionError):
                continue
    except FileNotFoundError:
        return 0
    return total


def status_snapshot(repo: str) -> dict:
    state = cache_state(repo)
    return {
        "repo": repo,
        "state": state,
        "path": str(repo_cache_dir(repo)) if state != "absent" else None,
        "bytes_complete": disk_bytes(repo),
        "bytes_incomplete": incomplete_bytes(repo),
    }


def ensure_hub_dir() -> Path:
    d = hub_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d
