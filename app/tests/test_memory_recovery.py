from datetime import datetime

import pytest

from backend import generation
from backend.generation import GenerationJob, GenerationManager
from backend.restart_health import restart_rate_snapshot


def _job() -> GenerationJob:
    return GenerationJob(
        job_id="local-test",
        mode="txt2img",
        params={"repo": "owner/model", "seed": None},
    )


def test_verified_memory_failure_retries_once_with_same_seed(tmp_path, monkeypatch):
    manager = GenerationManager()
    job = _job()
    staged = tmp_path / "working.png"
    final = tmp_path / "final.png"
    attempts = []
    releases = []

    monkeypatch.setattr(
        manager,
        "_release_memory_locked",
        lambda reason="memory-recovery": releases.append(reason) or {"released": True},
    )
    monkeypatch.setattr(manager, "_service_installed", lambda: False)

    def dispatch(current, _output):
        attempts.append(current.params.get("seed"))
        if len(attempts) == 1:
            current.resolved_seed = 8675309
            raise RuntimeError("MPS backend out of memory")

    manager._dispatch_with_memory_recovery(
        job, staged, final, dispatch, local=True,
    )

    assert attempts == [None, 8675309]
    assert releases == ["memory-recovery"]
    assert manager.memory_status()["consecutive_failures"] == 0
    assert manager.memory_status()["last_event"]["error_type"] == "RuntimeError"
    assert "job_id" not in manager.memory_status()["last_event"]


def test_second_memory_failure_schedules_supervised_restart(tmp_path, monkeypatch):
    manager = GenerationManager()
    job = _job()
    started = []

    class FakeTimer:
        def __init__(self, interval, callback):
            self.interval = interval
            self.callback = callback
            self.daemon = False

        def start(self):
            started.append(self.interval)

    monkeypatch.setattr(manager, "_release_memory_locked", lambda *args: {})
    monkeypatch.setattr(manager, "_service_installed", lambda: True)
    monkeypatch.setattr(generation.threading, "Timer", FakeTimer)

    with pytest.raises(RuntimeError, match="restarting automatically"):
        manager._dispatch_with_memory_recovery(
            job,
            tmp_path / "working.png",
            tmp_path / "final.png",
            lambda *_args: (_ for _ in ()).throw(MemoryError()),
            local=True,
        )

    status = manager.memory_status()
    assert status["consecutive_failures"] == 2
    assert status["restart_scheduled"] is True
    assert started == []
    manager._start_scheduled_restart()
    assert started == [0.75]


def test_normal_and_cloud_failures_are_not_retried_or_restart_triggers(
        tmp_path, monkeypatch):
    manager = GenerationManager()
    attempts = 0
    monkeypatch.setattr(
        manager,
        "_record_memory_failure",
        lambda *_args: pytest.fail("normal failures must not count as memory failures"),
    )

    def fail(*_args):
        nonlocal attempts
        attempts += 1
        raise RuntimeError("provider connection timed out")

    with pytest.raises(RuntimeError, match="connection timed out"):
        manager._dispatch_with_memory_recovery(
            _job(),
            tmp_path / "working.png",
            tmp_path / "final.png",
            fail,
            local=False,
        )
    assert attempts == 1

    assert generation._is_memory_failure(MemoryError())
    assert generation._is_memory_failure(RuntimeError("std::bad_alloc"))
    assert not generation._is_memory_failure(RuntimeError("resource limit exceeded"))
    assert not generation._is_memory_failure(RuntimeError("invalid image dimensions"))


def test_restart_rate_snapshot_is_bounded_and_reports_warning(tmp_path):
    log = tmp_path / "watchdog.log"
    log.write_text(
        "[watchdog] 2026-07-24 08:00:00 health probe failed 3 consecutive times; restarting\n"
        "[watchdog] 2026-07-24 09:00:00 no /api/health; restarting\n"
        "customer request text that must be ignored\n",
        encoding="utf-8",
    )

    data = restart_rate_snapshot(log, now=datetime(2026, 7, 24, 10, 0, 0))

    assert data["status"] == "warning"
    assert data["alert"] is True
    assert data["restarts_24h"] == 2
    assert data["last_restart_at"] == "2026-07-24T09:00:00"
