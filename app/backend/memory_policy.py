"""Persistent, opt-in accelerator-memory policy for Image Studio.

Performance mode preserves today's behavior. Other modes release cached model
objects plus MLX/Metal/PyTorch allocator caches only after generation is idle.
Manual release uses the same guarded path.
"""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

from fastapi import HTTPException


SETTINGS_FILE = Path(__file__).resolve().parent / "memory_policy.json"
MODES = {
    "performance": {"idle_seconds": None, "label": "Performance"},
    "balanced": {"idle_seconds": 600, "label": "Balanced"},
    "memory_saver": {"idle_seconds": 120, "label": "Memory Saver"},
    "immediate": {"idle_seconds": 0, "label": "Immediate"},
}
DEFAULT_MODE = "performance"
CHECK_INTERVAL_SECONDS = 5

_LOCK = threading.RLock()
_START_LOCK = threading.Lock()
_STARTED = False
_MANAGER = None
_LAST_ACTIVITY_AT: float | None = None
_LAST_RELEASE_AT: float | None = None
_LAST_RELEASE_REASON: str | None = None
_LAST_RELEASE_DETAILS: dict | None = None
_LAST_ERROR: str | None = None
_RELEASE_COUNT = 0
_RELEASING = False


def _read() -> dict:
    try:
        raw = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        raw = {}
    mode = raw.get("mode") if isinstance(raw, dict) else None
    if mode not in MODES:
        mode = DEFAULT_MODE
    return {"mode": mode}


def save(mode: object) -> dict:
    if not isinstance(mode, str) or mode not in MODES:
        raise HTTPException(400, f"mode must be one of: {', '.join(MODES)}")
    value = {"mode": mode}
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    partial = SETTINGS_FILE.with_suffix(".json.tmp")
    partial.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(partial, SETTINGS_FILE)
    return value


def _active_jobs() -> list:
    manager = _MANAGER
    if manager is None:
        return []
    return [
        job for job in manager.list_jobs()
        if str(getattr(job, "state", "")) in {"queued", "running", "cancelling"}
    ]


def mark_generation_started() -> None:
    global _LAST_ACTIVITY_AT
    with _LOCK:
        _LAST_ACTIVITY_AT = time.time()


def mark_generation_finished() -> None:
    global _LAST_ACTIVITY_AT
    with _LOCK:
        _LAST_ACTIVITY_AT = time.time()


def _release(reason: str) -> dict:
    global _LAST_RELEASE_AT, _LAST_RELEASE_REASON, _LAST_RELEASE_DETAILS
    global _LAST_ERROR, _RELEASE_COUNT, _RELEASING
    with _LOCK:
        if _RELEASING:
            raise HTTPException(409, "A memory release is already running")
        if _active_jobs():
            raise HTTPException(409, "Image generation is active; memory was not released")
        manager = _MANAGER
        if manager is None:
            raise HTTPException(503, "The generation manager is not ready")
        _RELEASING = True
    try:
        details = manager.release_memory()
        now = time.time()
        with _LOCK:
            _LAST_RELEASE_AT = now
            _LAST_RELEASE_REASON = reason
            _LAST_RELEASE_DETAILS = details
            _LAST_ERROR = None
            _RELEASE_COUNT += 1
            _RELEASING = False
        print(f"[memory] released accelerator memory ({reason}): {details}", flush=True)
        return status()
    except HTTPException:
        raise
    except Exception as exc:
        with _LOCK:
            _LAST_ERROR = f"{type(exc).__name__}: {exc}"
        raise HTTPException(409, f"Memory release deferred: {exc}") from exc
    finally:
        with _LOCK:
            _RELEASING = False


def release_now() -> dict:
    return _release("manual")


def run_due_release(now: float | None = None) -> dict | None:
    """Run one deterministic scheduler tick; public for focused regression tests."""
    current = time.time() if now is None else float(now)
    with _LOCK:
        mode = _read()["mode"]
        idle_seconds = MODES[mode]["idle_seconds"]
        last_activity = _LAST_ACTIVITY_AT
        last_release = _LAST_RELEASE_AT
        if idle_seconds is None or last_activity is None or _RELEASING:
            return None
        if _active_jobs() or current - last_activity < idle_seconds:
            return None
        if last_release is not None and last_release >= last_activity:
            return None
    return _release(f"automatic:{mode}")


def status() -> dict:
    with _LOCK:
        config = _read()
        mode = config["mode"]
        idle_seconds = MODES[mode]["idle_seconds"]
        active_count = len(_active_jobs())
        due_at = None
        if (
            idle_seconds is not None
            and _LAST_ACTIVITY_AT is not None
            and (_LAST_RELEASE_AT is None or _LAST_RELEASE_AT < _LAST_ACTIVITY_AT)
        ):
            due_at = _LAST_ACTIVITY_AT + idle_seconds
        return {
            "mode": mode,
            "default_mode": DEFAULT_MODE,
            "idle_seconds": idle_seconds,
            "options": [{"mode": key, **value} for key, value in MODES.items()],
            "active_jobs": active_count,
            "busy": bool(active_count or _RELEASING),
            "last_activity_at": _LAST_ACTIVITY_AT,
            "next_release_at": due_at,
            "last_release_at": _LAST_RELEASE_AT,
            "last_release_reason": _LAST_RELEASE_REASON,
            "last_release_details": _LAST_RELEASE_DETAILS,
            "last_error": _LAST_ERROR,
            "release_count": _RELEASE_COUNT,
        }


def start_background(manager) -> None:
    global _MANAGER, _STARTED
    _MANAGER = manager
    with _START_LOCK:
        if _STARTED:
            return
        _STARTED = True

    def loop() -> None:
        while True:
            time.sleep(CHECK_INTERVAL_SECONDS)
            try:
                run_due_release()
            except HTTPException as exc:
                print(f"[memory] automatic release deferred: {exc.detail}", flush=True)
            except Exception as exc:
                print(f"[memory] automatic release failed: {exc}", flush=True)

    threading.Thread(target=loop, name="memory-policy", daemon=True).start()
