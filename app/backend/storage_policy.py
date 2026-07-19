"""Automatic retention and hard-cap cleanup for generated output backups.

Only files in ``app/output`` are eligible. Model caches, LoRAs, uploads,
settings, active jobs, and every other application path are outside this
module by construction.
"""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

from fastapi import HTTPException


SETTINGS_FILE = Path(__file__).resolve().parent / "storage_policy.json"
DEFAULTS = {"enabled": True, "retention_days": 3, "max_gb": 80.0}
_LOCK = threading.RLock()
_START_LOCK = threading.Lock()
_STARTED = False


def _read() -> dict:
    try:
        value = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        value = {}
    out = {**DEFAULTS, **(value if isinstance(value, dict) else {})}
    if not isinstance(out["enabled"], bool):
        out["enabled"] = True
    try:
        out["retention_days"] = int(out["retention_days"])
    except (TypeError, ValueError):
        out["retention_days"] = 3
    try:
        out["max_gb"] = float(out["max_gb"])
    except (TypeError, ValueError):
        out["max_gb"] = 80.0
    if not 1 <= out["retention_days"] <= 3650:
        out["retention_days"] = 3
    if not 1 <= out["max_gb"] <= 1000:
        out["max_gb"] = 80.0
    return out


def save(enabled: object, retention_days: object, max_gb: object) -> dict:
    if not isinstance(enabled, bool):
        raise HTTPException(400, "enabled must be true or false")
    try:
        days = int(retention_days)
        maximum = float(max_gb)
    except (TypeError, ValueError):
        raise HTTPException(400, "retention_days and max_gb must be numbers")
    if not 1 <= days <= 3650:
        raise HTTPException(400, "retention_days must be between 1 and 3650")
    if not 1 <= maximum <= 1000:
        raise HTTPException(400, "max_gb must be between 1 and 1000")
    value = {"enabled": enabled, "retention_days": days, "max_gb": maximum}
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    partial = SETTINGS_FILE.with_suffix(".json.tmp")
    partial.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(partial, SETTINGS_FILE)
    return value


def _candidates(output_dir: Path) -> list[Path]:
    if not output_dir.exists():
        return []
    files = []
    for path in output_dir.iterdir():
        try:
            if (path.name.startswith(".") or path.is_symlink()
                    or not path.is_file()):
                continue
            files.append(path)
        except OSError:
            continue
    return sorted(files, key=lambda path: path.stat().st_mtime)


def _snapshot(output_dir: Path) -> dict:
    files = _candidates(output_dir)
    rows = []
    for path in files:
        try:
            stat = path.stat()
            rows.append((path, stat.st_size, stat.st_mtime))
        except OSError:
            pass
    return {
        "used_bytes": sum(row[1] for row in rows),
        "count": len(rows),
        "oldest_at": rows[0][2] if rows else None,
        "newest_at": rows[-1][2] if rows else None,
        "rows": rows,
    }


def status(manager, output_dir: Path) -> dict:
    policy = _read()
    snap = _snapshot(output_dir)
    maximum = round(policy["max_gb"] * 1024 ** 3)
    return {
        **policy,
        **{key: value for key, value in snap.items() if key != "rows"},
        "max_bytes": maximum,
        "over_limit": policy["enabled"] and snap["used_bytes"] > maximum,
        "scope": "generated image outputs only",
    }


def _terminal_or_orphan(manager, path: Path) -> bool:
    job = manager.get(path.stem)
    return job is None or str(getattr(job, "state", "")) in {
        "done", "error", "cancelled",
    }


def _remove(manager, path: Path) -> int:
    if not _terminal_or_orphan(manager, path):
        return 0
    try:
        size = path.stat().st_size
    except OSError:
        return 0
    job = manager.get(path.stem)
    if job is not None:
        if not manager.delete_job(path.stem):
            return 0
    else:
        try:
            path.unlink()
        except OSError:
            return 0
    return size


def enforce(manager, output_dir: Path, target_bytes: int | None = None) -> dict:
    """Apply age expiry, then delete oldest outputs until the hard cap fits."""
    with _LOCK:
        policy = _read()
        before = _snapshot(output_dir)
        result = {
            "enabled": policy["enabled"],
            "retention_days": policy["retention_days"],
            "max_gb": policy["max_gb"],
            "used_before_bytes": before["used_bytes"],
            "used_bytes": before["used_bytes"],
            "deleted": 0,
            "freed_bytes": 0,
        }
        if not policy["enabled"] and target_bytes is None:
            return result
        maximum = (max(0, int(target_bytes)) if target_bytes is not None
                   else round(policy["max_gb"] * 1024 ** 3))
        cutoff = time.time() - policy["retention_days"] * 86400
        for path, _size, modified in list(before["rows"]):
            if modified >= cutoff:
                continue
            freed = _remove(manager, path)
            if freed:
                result["deleted"] += 1
                result["freed_bytes"] += freed
        snap = _snapshot(output_dir)
        for path, _size, _modified in list(snap["rows"]):
            if snap["used_bytes"] <= maximum:
                break
            freed = _remove(manager, path)
            if freed:
                result["deleted"] += 1
                result["freed_bytes"] += freed
                snap["used_bytes"] = max(0, snap["used_bytes"] - freed)
        final = _snapshot(output_dir)
        result.update(
            used_bytes=final["used_bytes"], count=final["count"],
            max_bytes=maximum, over_limit=final["used_bytes"] > maximum,
        )
        return result


def start_background(manager, output_dir: Path) -> None:
    """Run independently of the UI; first sweep waits so tests/imports stay safe."""
    global _STARTED
    with _START_LOCK:
        if _STARTED:
            return
        _STARTED = True

    def loop() -> None:
        time.sleep(60)
        while True:
            try:
                enforce(manager, output_dir)
            except Exception as exc:
                print(f"[storage] automatic cleanup failed: {exc}", flush=True)
            time.sleep(3600)

    threading.Thread(target=loop, name="output-storage-cleanup", daemon=True).start()
