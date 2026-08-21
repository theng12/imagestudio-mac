from __future__ import annotations

import datetime as dt
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import stat
import subprocess
import sys
import threading
from types import SimpleNamespace
import inspect

import pytest

from backend.auto_update import AutoUpdater, UpdateDeferred, UpdateError, _parse_iso, _redact


@pytest.fixture
def updater(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AutoUpdater:
    root = tmp_path / "voicestudio-mac.git"
    (root / ".git").mkdir(parents=True)
    (root / "app").mkdir()
    (root / "conda_env" / "bin").mkdir(parents=True)
    (root / "VERSION").write_text("1.0.0\n")
    (root / "app" / "requirements.txt").write_text("fastapi\n")
    python = root / "conda_env" / "bin" / "python"
    python.symlink_to(sys.executable)
    spec = {
        "root": str(root), "title": "Voice Studio KH", "slug": "voicestudio-test",
        "expected_remote": "https://github.com/theng12/voicestudio-mac.git",
        "branch": "main", "port": 47870, "default_hour": 2,
        "server_label": "com.kh.voicestudio.server",
        "watchdog_label": "com.kh.voicestudio.watchdog",
    }
    item = AutoUpdater(spec)
    monkeypatch.setattr(item, "scheduler_status", lambda: {
        "installed": item.settings()["mode"] != "off", "supported": True,
        "label": item.agent_label,
    })
    monkeypatch.setattr(item, "apply_scheduler", lambda force_pending=False: {
        "installed": item.settings()["mode"] != "off" or force_pending,
        "supported": True, "label": item.agent_label,
    })
    monkeypatch.setattr(item, "_notify", lambda *args: None)
    return item


def _save(updater: AutoUpdater, mode: str) -> dict:
    return updater.save_settings({
        "mode": mode, "frequency": "daily", "maintenance_hour": 2,
        "idle_only": True,
    })


def test_default_is_off_and_idle_only(updater: AutoUpdater):
    assert updater.settings() == {
        "mode": "off", "frequency": "daily", "maintenance_hour": 2,
        "idle_only": True, "weekday": 6,
    }
    assert updater.public_status()["scheduler"]["installed"] is False


def test_status_advertises_exact_commit_and_dependency_convergence(updater: AutoUpdater):
    assert updater.public_status()["capabilities"] == {
        "managed_exact_commit": True,
        "dependency_convergence": 1,
    }


def _worktree_spec(root: Path) -> dict:
    return {
        "root": str(root), "title": "Image Studio KH", "slug": "imagestudio-test",
        "expected_remote": "https://github.com/theng12/imagestudio-mac.git",
        "branch": "main", "port": 47868, "default_hour": 4,
    }


def _commit_all(root: Path, message: str) -> str:
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "commit", "-m", message],
        check=True, capture_output=True, text=True,
    )
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def _runtime_state_rollback_repository(tmp_path: Path) -> tuple[Path, str, str]:
    root = tmp_path / "imagestudio-mac.git"
    subprocess.run(
        ["git", "init", "-b", "main", str(root)],
        check=True, capture_output=True, text=True,
    )
    subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Test User"], check=True)
    (root / ".gitignore").write_text("logs/\nauto_update/\n", encoding="utf-8")
    (root / "ENVIRONMENT").write_bytes(b"HF_HOME=./cache/HF_HOME\n")
    old_sha = _commit_all(root, "legacy tracked environment")

    (root / "ENVIRONMENT").unlink()
    (root / "ENVIRONMENT.example").write_bytes(b"HF_HOME=./cache/HF_HOME\n")
    (root / ".gitignore").write_text("logs/\nauto_update/\n/ENVIRONMENT\n", encoding="utf-8")
    new_sha = _commit_all(root, "machine-local environment")
    return root, old_sha, new_sha


def test_real_linked_worktree_metadata_file_is_accepted(tmp_path: Path):
    repository = tmp_path / "repository"
    worktree = tmp_path / "linked-worktree"
    subprocess.run(["git", "init", str(repository)], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(repository), "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(repository), "config", "user.name", "Test User"], check=True)
    (repository / "README.md").write_text("test\n")
    subprocess.run(["git", "-C", str(repository), "add", "README.md"], check=True)
    subprocess.run(["git", "-C", str(repository), "commit", "-m", "initial"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(repository), "worktree", "add", "-b", "linked", str(worktree), "HEAD"], check=True, capture_output=True, text=True)

    assert (worktree / ".git").is_file()
    assert AutoUpdater(_worktree_spec(worktree)).root == worktree


def test_nonexistent_git_worktree_metadata_is_rejected(tmp_path: Path):
    root = tmp_path / "imagestudio-mac"
    root.mkdir()
    (root / ".git").write_text("gitdir: /private/tmp/missing-worktree\n")

    with pytest.raises(UpdateError, match="real Git checkout"):
        AutoUpdater(_worktree_spec(root))


def test_head_only_worktree_metadata_is_rejected(tmp_path: Path):
    root = tmp_path / "imagestudio-mac"
    root.mkdir()
    gitdir = tmp_path / "imagestudio-worktree"
    gitdir.mkdir()
    (gitdir / "HEAD").write_text("ref: refs/heads/main\n")
    (root / ".git").write_text("gitdir: ../imagestudio-worktree\n")

    with pytest.raises(UpdateError, match="real Git checkout"):
        AutoUpdater(_worktree_spec(root))


@pytest.mark.parametrize("broken", ["backlink", "common"])
def test_worktree_metadata_with_broken_administrative_links_is_rejected(tmp_path: Path, broken: str):
    root = tmp_path / "imagestudio-mac"
    root.mkdir()
    gitdir = tmp_path / "imagestudio-worktree"
    gitdir.mkdir()
    common = tmp_path / "common-git"
    common.mkdir()
    (common / "config").write_text("[core]\n")
    (common / "objects").mkdir()
    (gitdir / "HEAD").write_text("ref: refs/heads/main\n")
    (gitdir / "commondir").write_text("../missing-common\n" if broken == "common" else "../common-git\n")
    (gitdir / "gitdir").write_text("../other/.git\n" if broken == "backlink" else "../imagestudio-mac/.git\n")
    (root / ".git").write_text("gitdir: ../imagestudio-worktree\n")

    with pytest.raises(UpdateError, match="real Git checkout"):
        AutoUpdater(_worktree_spec(root))


def test_settings_modes_install_and_remove_schedule(updater: AutoUpdater):
    assert _save(updater, "notify")["scheduler"]["installed"] is True
    assert _save(updater, "auto")["scheduler"]["installed"] is True
    status = _save(updater, "off")
    assert status["scheduler"]["installed"] is False
    assert status["next_check"] is None


def test_git_preserves_porcelain_status_columns(updater: AutoUpdater):
    updater.runner = lambda *_args, **_kwargs: subprocess.CompletedProcess(
        [], 0, " M ENVIRONMENT\n", "",
    )

    assert updater._git("status", "--porcelain") == " M ENVIRONMENT"


def test_dirty_checkout_renders_the_complete_porcelain_path(
    updater: AutoUpdater, monkeypatch: pytest.MonkeyPatch,
):
    def fake_git(*args, **_kwargs):
        command = tuple(args)
        if command == ("remote", "get-url", "origin"):
            return updater.spec["expected_remote"]
        if command[:3] == ("symbolic-ref", "--quiet", "--short"):
            return "main"
        if command[:2] == ("status", "--porcelain"):
            return " M ENVIRONMENT"
        raise AssertionError(command)

    monkeypatch.setattr(updater, "_git", fake_git)

    with pytest.raises(UpdateError) as excinfo:
        updater._git_preflight(fetch=False)

    assert str(excinfo.value) == (
        "Working tree has local changes: ENVIRONMENT. "
        "Commit or remove them before updating."
    )


def test_invalid_settings_are_rejected(updater: AutoUpdater):
    with pytest.raises(UpdateError):
        updater.save_settings({"mode": "always", "frequency": "daily",
                               "maintenance_hour": 2, "idle_only": True})
    with pytest.raises(UpdateError):
        updater.save_settings({"mode": "auto", "frequency": "daily",
                               "maintenance_hour": 24, "idle_only": True})


def test_notify_only_checks_but_does_not_install(updater: AutoUpdater, monkeypatch):
    _save(updater, "notify")
    updater._write_status(next_check="2000-01-01T00:00:00Z")
    monkeypatch.setattr(updater, "check", lambda: {"update_available": True, "latest_version": "2.0.0"})
    called = []
    monkeypatch.setattr(updater, "update", lambda **kwargs: called.append(kwargs))
    monkeypatch.setattr(updater, "_notify", lambda *args: called.append("notify"))
    updater.scheduled()
    assert called == ["notify"]


def test_auto_mode_installs_available_update(updater: AutoUpdater, monkeypatch):
    _save(updater, "auto")
    updater._write_status(next_check="2000-01-01T00:00:00Z")
    monkeypatch.setattr(updater, "check", lambda: {"update_available": True, "latest_version": "2.0.0"})
    called = []
    monkeypatch.setattr(updater, "update", lambda **kwargs: called.append(kwargs) or {"state": "succeeded"})
    updater.scheduled()
    assert called == [{"automatic": True}]


def test_active_work_defers_and_records_reason(updater: AutoUpdater, monkeypatch):
    monkeypatch.setattr(updater, "readiness_reasons", lambda: ["voice generation is running"])
    with pytest.raises(UpdateDeferred):
        updater.update(automatic=True)
    status = updater.public_status()
    assert status["state"] == "deferred"
    assert "voice generation" in status["defer_reason"]
    assert status["next_retry"]


def test_readiness_failure_defers_when_service_is_not_confirmed_stopped(
    updater: AutoUpdater, monkeypatch: pytest.MonkeyPatch
):
    def unavailable(*_args, **_kwargs):
        raise OSError("health endpoint unavailable")

    monkeypatch.setattr("backend.auto_update.urlopen", unavailable)
    monkeypatch.setattr(updater, "_service_loaded", lambda: True)
    monkeypatch.setattr(updater, "_port_accepting_connections", lambda: False)

    assert updater.readiness_reasons() == [
        "the update safety check is unavailable and Image Studio is not confirmed stopped"
    ]


def test_readiness_failure_is_safe_only_when_service_is_positively_stopped(
    updater: AutoUpdater, monkeypatch: pytest.MonkeyPatch
):
    def unavailable(*_args, **_kwargs):
        raise OSError("health endpoint unavailable")

    monkeypatch.setattr("backend.auto_update.urlopen", unavailable)
    monkeypatch.setattr(updater, "_service_loaded", lambda: False)
    monkeypatch.setattr(updater, "_port_accepting_connections", lambda: False)

    assert updater.readiness_reasons() == []


def test_unresponsive_listener_is_not_treated_as_a_stopped_service(
    updater: AutoUpdater, monkeypatch: pytest.MonkeyPatch
):
    def unavailable(*_args, **_kwargs):
        raise OSError("health endpoint unavailable")

    monkeypatch.setattr("backend.auto_update.urlopen", unavailable)
    monkeypatch.setattr(updater, "_service_loaded", lambda: False)
    monkeypatch.setattr(updater, "_port_accepting_connections", lambda: True)

    assert updater.readiness_reasons()


def test_service_state_probe_failure_also_fails_closed(
    updater: AutoUpdater, monkeypatch: pytest.MonkeyPatch
):
    def unavailable(*_args, **_kwargs):
        raise OSError("health endpoint unavailable")

    monkeypatch.setattr("backend.auto_update.urlopen", unavailable)
    monkeypatch.setattr(
        updater,
        "_service_loaded",
        lambda: (_ for _ in ()).throw(OSError("launchd unavailable")),
    )

    assert updater.readiness_reasons()


def test_update_after_work_creates_pending_retry(updater: AutoUpdater, monkeypatch):
    monkeypatch.setattr(updater, "readiness_reasons", lambda: ["download active"])
    status = updater.trigger_update(after_current=True)
    assert status["pending_manual"] is True
    assert status["state"] == "deferred"


def test_managed_target_requires_all_fields(updater: AutoUpdater):
    with pytest.raises(UpdateError, match="all be provided"):
        updater.trigger_update(target_commit="a" * 40)


@pytest.mark.parametrize("version", ["1.2", "01.2.3", "1.2.3.4", "1.2.3+build.1"])
def test_managed_target_requires_release_compatible_semver(
    updater: AutoUpdater, monkeypatch: pytest.MonkeyPatch, version: str
):
    monkeypatch.setattr(updater, "_spawn", lambda *_args: None)
    with pytest.raises(UpdateError, match="target_version is invalid"):
        updater.trigger_update(
            target_commit="a" * 40, target_version=version, operation_id="hub-op-1"
        )


def test_matching_managed_operation_is_adopted_without_duplicate_helper(
    updater: AutoUpdater, monkeypatch: pytest.MonkeyPatch
):
    spawned = []
    monkeypatch.setattr(
        updater, "_spawn",
        lambda *args: spawned.append(args) or SimpleNamespace(pid=os.getpid()),
    )

    request = {
        "target_commit": "a" * 40,
        "target_version": "2.0.0",
        "operation_id": "hub-op-1",
    }
    updater.trigger_update(**request)
    adopted = updater.trigger_update(**request)

    assert len(spawned) == 1
    assert adopted["managed_update"] == request


def test_concurrent_identical_managed_requests_admit_one_helper(
    updater: AutoUpdater, monkeypatch: pytest.MonkeyPatch
):
    request = {"target_commit": "a" * 40, "target_version": "2.0.0", "operation_id": "hub-op-1"}
    original_read = updater._read_status
    barrier = threading.Barrier(2)
    reads = 0
    reads_lock = threading.Lock()
    spawned = []

    def synchronized_read():
        nonlocal reads
        with reads_lock:
            reads += 1
            wait = reads <= 2
        if wait:
            try:
                barrier.wait(timeout=0.2)
            except threading.BrokenBarrierError:
                pass
        return original_read()

    monkeypatch.setattr(updater, "_read_status", synchronized_read)
    monkeypatch.setattr(
        updater, "_spawn",
        lambda *args: spawned.append(args) or SimpleNamespace(pid=os.getpid()),
    )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _unused: updater.trigger_update(**request), range(2)))

    assert len(spawned) == 1
    assert all(result["managed_update"] == request for result in results)


def test_concurrent_conflicting_managed_requests_reject_one(
    updater: AutoUpdater, monkeypatch: pytest.MonkeyPatch
):
    first = {"target_commit": "a" * 40, "target_version": "2.0.0", "operation_id": "hub-op-1"}
    second = {"target_commit": "b" * 40, "target_version": "2.0.0", "operation_id": "hub-op-2"}
    original_read = updater._read_status
    barrier = threading.Barrier(2)
    reads = 0
    reads_lock = threading.Lock()
    spawned = []

    def synchronized_read():
        nonlocal reads
        with reads_lock:
            reads += 1
            wait = reads <= 2
        if wait:
            try:
                barrier.wait(timeout=0.2)
            except threading.BrokenBarrierError:
                pass
        return original_read()

    monkeypatch.setattr(updater, "_read_status", synchronized_read)
    monkeypatch.setattr(
        updater, "_spawn",
        lambda *args: spawned.append(args) or SimpleNamespace(pid=os.getpid()),
    )

    def trigger(request):
        try:
            return updater.trigger_update(**request)
        except UpdateError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(trigger, (first, second)))

    assert len(spawned) == 1
    assert sum(isinstance(result, UpdateError) for result in results) == 1


def test_completed_managed_target_does_not_hijack_ordinary_deferred_update(
    updater: AutoUpdater, monkeypatch: pytest.MonkeyPatch
):
    updater._write_status(
        managed_update={
            "target_commit": "a" * 40,
            "target_version": "2.0.0",
            "operation_id": "hub-op-1",
        },
        pending_manual=False,
    )
    monkeypatch.setattr(updater, "readiness_reasons", lambda: ["generation active"])
    updater.trigger_update(after_current=True)
    calls = []
    monkeypatch.setattr(updater, "update", lambda **kwargs: calls.append(kwargs) or {"state": "succeeded"})

    updater.scheduled()

    assert calls == [{"automatic": False}]


def test_dead_managed_operation_reinstalls_durable_recovery(
    updater: AutoUpdater, monkeypatch: pytest.MonkeyPatch
):
    request = {"target_commit": "a" * 40, "target_version": "2.0.0", "operation_id": "hub-op-1"}
    updater._write_status(active_managed_update=request, pending_manual=True, managed_helper_pid=999_999)
    scheduled = []
    spawned = []
    monkeypatch.setattr(updater, "apply_scheduler", lambda **kwargs: scheduled.append(kwargs) or {"installed": True})
    monkeypatch.setattr(
        updater, "_spawn",
        lambda *args: spawned.append(args) or SimpleNamespace(pid=os.getpid()),
    )

    updater.trigger_update(**request)

    assert scheduled == [{"force_pending": True}]
    assert len(spawned) == 1


def test_resumed_managed_update_restarts_original_service_after_stop(
    updater: AutoUpdater, monkeypatch: pytest.MonkeyPatch
):
    request = {"target_commit": "b" * 40, "target_version": "2.0.0", "operation_id": "hub-op-1"}
    updater._write_status(
        active_managed_update={**request, "run_mode": "service", "phase": "stopped"},
        pending_manual=True,
    )
    monkeypatch.setattr(updater, "active_mode", lambda: "stopped")
    monkeypatch.setattr(updater, "readiness_reasons", lambda: [])
    monkeypatch.setattr(updater, "_git_preflight", lambda **_kwargs: {
        "local": request["target_commit"], "remote": request["target_commit"],
        "latest": request["target_version"], "available": False,
    })
    started = []
    verified = []
    monkeypatch.setattr(updater, "_install_dependencies", lambda: None)
    monkeypatch.setattr(updater, "_verify_import", lambda _version: None)
    monkeypatch.setattr(updater, "_start_mode", lambda mode: started.append(mode))
    monkeypatch.setattr(
        updater, "_verify_health", lambda mode, *_args: verified.append(mode) or True
    )

    updater.update(**request)

    assert started == ["service"]
    assert verified == ["service"]


@pytest.mark.parametrize("phase", ["stopped", "merged", "merged"], ids=[
    "after-merge-before-phase-write", "during-install", "after-install-before-import",
])
def test_target_checkout_recovery_replays_install_and_import_before_restart(
    updater: AutoUpdater, monkeypatch: pytest.MonkeyPatch, phase: str
):
    request = {"target_commit": "b" * 40, "target_version": "2.0.0", "operation_id": "hub-op-1"}
    updater._write_status(
        active_managed_update={
            **request, "run_mode": "service", "phase": phase,
            "rollback_sha": "a" * 40, "rollback_version": "1.0.0",
        },
        pending_manual=True,
    )
    monkeypatch.setattr(updater, "active_mode", lambda: "stopped")
    monkeypatch.setattr(updater, "readiness_reasons", lambda: [])
    monkeypatch.setattr(updater, "_git_preflight", lambda **_kwargs: {
        "local": request["target_commit"], "remote": request["target_commit"],
        "latest": request["target_version"], "available": False,
    })
    calls = []
    monkeypatch.setattr(updater, "_install_dependencies", lambda: calls.append("install"))
    monkeypatch.setattr(updater, "_verify_import", lambda _version: calls.append("import"))
    monkeypatch.setattr(updater, "_start_mode", lambda mode: calls.append(f"start:{mode}"))
    monkeypatch.setattr(updater, "_verify_health", lambda *_args: calls.append("health") or True)

    updater.update(**request)

    assert calls == ["install", "import", "start:service", "health"]


@pytest.mark.parametrize("outcome", ["no-op", "failure", "success"])
def test_managed_terminal_paths_clear_retry_and_preserve_regular_check(
    updater: AutoUpdater, monkeypatch: pytest.MonkeyPatch, outcome: str
):
    request = {"target_commit": "b" * 40, "target_version": "2.0.0", "operation_id": "hub-op-1"}
    regular_check = "2030-01-01T00:00:00Z"
    _save(updater, "auto")
    updater._write_status(
        active_managed_update={**request, "run_mode": "stopped", "phase": "prepared"},
        pending_manual=True, next_retry="2026-08-15T10:00:00Z", next_check=regular_check,
    )
    monkeypatch.setattr(updater, "active_mode", lambda: "stopped")
    monkeypatch.setattr(updater, "readiness_reasons", lambda: [])
    if outcome == "success":
        monkeypatch.setattr(updater, "_git_preflight", lambda **_kwargs: {
            "local": "a" * 40, "remote": request["target_commit"],
            "latest": request["target_version"], "available": True,
        })
        monkeypatch.setattr(updater, "_git", lambda *_args, **_kwargs: "")
        monkeypatch.setattr(updater, "_stop_mode", lambda _mode: None)
        monkeypatch.setattr(updater, "_install_dependencies", lambda: None)
        monkeypatch.setattr(updater, "_verify_import", lambda _version: None)
        monkeypatch.setattr(updater, "_start_mode", lambda _mode: None)
        monkeypatch.setattr(updater, "_verify_health", lambda *_args: True)
    else:
        monkeypatch.setattr(updater, "_git_preflight", lambda **_kwargs: {
            "local": request["target_commit"], "remote": request["target_commit"],
            "latest": request["target_version"], "available": False,
        })
        monkeypatch.setattr(updater, "_verify_health", lambda *_args: outcome == "no-op")

    if outcome == "failure":
        with pytest.raises(UpdateError):
            updater.update(**request)
    else:
        updater.update(**request)

    status = updater.public_status()
    assert status["next_retry"] is None
    assert status["next_check"] == regular_check
    monkeypatch.setattr(updater, "check", lambda: pytest.fail("terminal managed update must not trigger Auto work"))
    updater.scheduled()


def test_target_checkout_recovery_keeps_persisted_rollback_point(
    updater: AutoUpdater, monkeypatch: pytest.MonkeyPatch
):
    request = {"target_commit": "b" * 40, "target_version": "2.0.0", "operation_id": "hub-op-1"}
    updater._write_status(
        active_managed_update={
            **request, "run_mode": "service", "phase": "merged",
            "rollback_sha": "a" * 40, "rollback_version": "1.0.0",
        },
        pending_manual=True,
    )
    monkeypatch.setattr(updater, "active_mode", lambda: "stopped")
    monkeypatch.setattr(updater, "readiness_reasons", lambda: [])
    monkeypatch.setattr(updater, "_git_preflight", lambda **_kwargs: {
        "local": request["target_commit"], "remote": request["target_commit"],
        "latest": request["target_version"], "available": False,
    })
    monkeypatch.setattr(
        updater, "_install_dependencies", lambda: (_ for _ in ()).throw(UpdateError("install failed"))
    )
    rollbacks = []
    monkeypatch.setattr(updater, "_rollback", lambda *args: rollbacks.append(args) or True)

    with pytest.raises(UpdateError, match="install failed"):
        updater.update(**request)

    assert rollbacks == [("a" * 40, "b" * 40, "service", "1.0.0")]


def test_managed_launch_sets_prompt_retry_ahead_of_future_regular_check(
    updater: AutoUpdater, monkeypatch: pytest.MonkeyPatch
):
    request = {"target_commit": "a" * 40, "target_version": "2.0.0", "operation_id": "hub-op-1"}
    now = dt.datetime(2026, 8, 15, 10, tzinfo=dt.timezone.utc)
    updater.now = lambda: now
    updater._write_status(next_check="2030-01-01T00:00:00Z")
    monkeypatch.setattr(updater, "_spawn", lambda *_args: SimpleNamespace(pid=os.getpid()))

    updater.trigger_update(**request)

    assert _parse_iso(updater.public_status()["next_retry"]) <= now
    calls = []
    monkeypatch.setattr(updater, "update", lambda **kwargs: calls.append(kwargs) or {"state": "succeeded"})
    updater.scheduled()
    assert calls == [{"automatic": False, **request}]


def test_completed_managed_operation_remains_idempotent_beyond_eight_later_operations(
    updater: AutoUpdater, monkeypatch: pytest.MonkeyPatch
):
    history = [
        {
            "target_commit": f"{index:x}" * 40,
            "target_version": "2.0.0",
            "operation_id": f"hub-op-{index}",
            "result": "succeeded",
        }
        for index in range(9)
    ]
    updater._write_status(managed_operation_history=history)
    monkeypatch.setattr(updater, "_spawn", lambda *_args: pytest.fail("completed operation must be adopted"))

    result = updater.trigger_update(
        target_commit="0" * 40, target_version="2.0.0", operation_id="hub-op-0"
    )

    assert result["managed_update"] is None


def test_managed_target_only_merges_requested_sha(updater: AutoUpdater, monkeypatch):
    target = "b" * 40
    main_tip = "c" * 40
    calls = []

    def fake_git(*args, **_kwargs):
        command = tuple(args)
        calls.append(command)
        if command == ("remote", "get-url", "origin"):
            return updater.spec["expected_remote"]
        if command[:3] == ("symbolic-ref", "--quiet", "--short"):
            return "main"
        if command[:2] == ("status", "--porcelain") or command[:1] == ("fetch",):
            return ""
        if command == ("rev-parse", "HEAD"):
            return "a" * 40
        if command == ("rev-parse", "origin/main"):
            return main_tip
        if command == ("rev-parse", "--verify", f"{target}^{{commit}}"):
            return target
        if command == ("show", f"{target}:VERSION"):
            return "2.0.0"
        if command[:1] == ("merge",):
            return ""
        raise AssertionError(command)

    monkeypatch.setattr(updater, "_git", fake_git)
    monkeypatch.setattr(
        updater, "_run",
        lambda args, **_kwargs: subprocess.CompletedProcess(args, 0, "", ""),
    )
    monkeypatch.setattr(updater, "readiness_reasons", lambda: [])
    monkeypatch.setattr(updater, "active_mode", lambda: "stopped")
    monkeypatch.setattr(updater, "_stop_mode", lambda _mode: None)
    monkeypatch.setattr(updater, "_install_dependencies", lambda: None)
    monkeypatch.setattr(updater, "_verify_import", lambda _version: None)
    monkeypatch.setattr(updater, "_start_mode", lambda _mode: None)
    monkeypatch.setattr(updater, "_verify_health", lambda *_args: True)

    updater.update(target_commit=target, target_version="2.0.0", operation_id="hub-op-1")

    assert ("merge", "--ff-only", target) in calls
    assert ("merge", "--ff-only", "origin/main") not in calls


def test_busy_managed_update_keeps_durable_target(updater: AutoUpdater, monkeypatch):
    monkeypatch.setattr(updater, "readiness_reasons", lambda: ["generation active"])

    with pytest.raises(UpdateDeferred):
        updater.update(
            target_commit="a" * 40,
            target_version="2.0.0",
            operation_id="hub-op-1",
        )

    status = updater.public_status()
    assert status["pending_manual"] is True
    assert status["managed_update"] == {
        "target_commit": "a" * 40,
        "target_version": "2.0.0",
        "operation_id": "hub-op-1",
    }


def test_public_status_redacts_and_bounds_details(updater: AutoUpdater):
    updater._write_status(
        details=[f"token=secret-{index}" for index in range(20)],
        last_update_result="Authorization: Bearer super-secret",
    )

    status = updater.public_status()

    assert len(status["details"]) <= 8
    assert "super-secret" not in status["last_update_result"]
    assert all("secret-" not in item for item in status["details"])


def test_concurrent_update_lock_is_refused(updater: AutoUpdater):
    with updater._exclusive_lock():
        with pytest.raises(UpdateError, match="already running"):
            with updater._exclusive_lock():
                pass


@pytest.mark.parametrize("case, message", [
    ("remote", "Unexpected Git remote"),
    ("branch", "configured main branch"),
    ("dirty", "local changes"),
    ("diverged", "diverged"),
])
def test_git_safety_refusals(updater: AutoUpdater, monkeypatch, case, message):
    def fake_git(*args, **kwargs):
        command = tuple(args)
        if command == ("remote", "get-url", "origin"):
            return "https://github.com/attacker/wrong.git" if case == "remote" else updater.spec["expected_remote"]
        if command[:3] == ("symbolic-ref", "--quiet", "--short"):
            return "feature" if case == "branch" else "main"
        if command[:2] == ("status", "--porcelain"):
            return " M local.txt" if case == "dirty" else ""
        if command[:1] == ("fetch",):
            return ""
        if command == ("rev-parse", "HEAD"):
            return "a" * 40
        if command == ("rev-parse", "origin/main"):
            return "b" * 40
        if command[:1] == ("show",):
            return "2.0.0"
        raise AssertionError(command)
    monkeypatch.setattr(updater, "_git", fake_git)
    def fake_run(args, **kwargs):
        rc = 1 if case == "diverged" and "merge-base" in args else 0
        return subprocess.CompletedProcess(args, rc, "", "")
    monkeypatch.setattr(updater, "_run", fake_run)
    with pytest.raises(UpdateError, match=message):
        updater._git_preflight()


def test_disk_space_failure_happens_before_files_change(updater: AutoUpdater, monkeypatch):
    monkeypatch.setattr(updater, "readiness_reasons", lambda: [])
    monkeypatch.setattr("backend.auto_update.shutil.disk_usage", lambda _p: type("D", (), {"free": 1})())
    monkeypatch.setattr(updater, "_git_preflight", lambda **kwargs: pytest.fail("Git update must not start"))
    with pytest.raises(UpdateError, match="disk space"):
        updater.update()


@pytest.mark.parametrize("failure", ["dependencies", "health"])
def test_install_or_health_failure_attempts_rollback(updater: AutoUpdater, monkeypatch, failure):
    monkeypatch.setattr(updater, "readiness_reasons", lambda: [])
    monkeypatch.setattr(updater, "active_mode", lambda: "stopped")
    monkeypatch.setattr(updater, "_git_preflight", lambda **kwargs: {
        "local": "a" * 40, "remote": "b" * 40, "latest": "2.0.0", "available": True,
    })
    monkeypatch.setattr(updater, "_stop_mode", lambda mode: None)
    monkeypatch.setattr(updater, "_git", lambda *args, **kwargs: "")
    monkeypatch.setattr(updater, "_verify_import", lambda expected: None)
    monkeypatch.setattr(updater, "_start_mode", lambda mode: None)
    monkeypatch.setattr(updater, "_verify_health", lambda *_args: failure != "health")
    if failure == "dependencies":
        monkeypatch.setattr(updater, "_install_dependencies", lambda: (_ for _ in ()).throw(UpdateError("dependency install failed")))
    else:
        monkeypatch.setattr(updater, "_install_dependencies", lambda: None)
    rollbacks = []
    monkeypatch.setattr(updater, "_rollback", lambda *args: rollbacks.append(args) or True)
    with pytest.raises(UpdateError):
        updater.update()
    assert len(rollbacks) == 1
    assert updater.public_status()["rollback"] == "succeeded"


def test_rollback_failure_is_reported(updater: AutoUpdater, monkeypatch):
    monkeypatch.setattr(updater, "readiness_reasons", lambda: [])
    monkeypatch.setattr(updater, "active_mode", lambda: "stopped")
    monkeypatch.setattr(updater, "_git_preflight", lambda **kwargs: {
        "local": "a" * 40, "remote": "b" * 40, "latest": "2.0.0", "available": True,
    })
    monkeypatch.setattr(updater, "_stop_mode", lambda mode: None)
    monkeypatch.setattr(updater, "_git", lambda *args, **kwargs: "")
    monkeypatch.setattr(updater, "_install_dependencies", lambda: (_ for _ in ()).throw(UpdateError("boom")))
    monkeypatch.setattr(updater, "_rollback", lambda *args: False)
    with pytest.raises(UpdateError):
        updater.update()
    assert updater.public_status()["rollback"] == "failed"


def test_service_and_pinokio_modes_restart_only_their_owner(updater: AutoUpdater, monkeypatch):
    calls = []
    monkeypatch.setattr(updater, "_run", lambda args, **kwargs: calls.append(tuple(args)) or subprocess.CompletedProcess(args, 0, "", ""))
    monkeypatch.setattr(updater, "_pterm", lambda action: calls.append(("pterm", action)))
    updater._start_mode("service")
    updater._start_mode("pinokio")
    assert calls == [("/bin/bash", "install_service.sh"), ("pterm", "start")]


def test_dependency_refresh_uses_only_the_all_installed_bridge(
    updater: AutoUpdater, monkeypatch: pytest.MonkeyPatch
):
    calls = []
    monkeypatch.setattr(
        updater,
        "_run",
        lambda args, **kwargs: calls.append([str(item) for item in args])
        or subprocess.CompletedProcess(args, 0, "", ""),
    )

    updater._install_dependencies()

    assert calls == [[
        str(updater.root / "conda_env" / "bin" / "python"),
        "-m", "backend.dependency_convergence", "all-installed",
    ]]
    source = inspect.getsource(AutoUpdater._install_dependencies)
    assert "pip install" not in source


def test_convergence_subprocess_failure_marks_update_failed_and_rolls_back(
    updater: AutoUpdater, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(updater, "readiness_reasons", lambda: [])
    monkeypatch.setattr(updater, "active_mode", lambda: "stopped")
    monkeypatch.setattr(updater, "_git_preflight", lambda **_kwargs: {
        "local": "a" * 40, "remote": "b" * 40, "latest": "2.0.0", "available": True,
    })
    monkeypatch.setattr(updater, "_stop_mode", lambda _mode: None)
    monkeypatch.setattr(updater, "_git", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(updater, "_verify_import", lambda _version: None)
    monkeypatch.setattr(updater, "_start_mode", lambda _mode: None)
    monkeypatch.setattr(updater, "_verify_health", lambda *_args: True)
    expected = [
        str(updater.root / "conda_env" / "bin" / "python"),
        "-m", "backend.dependency_convergence", "all-installed",
    ]
    calls = []

    def fail_convergence(args, **_kwargs):
        calls.append(args)
        if args == expected:
            raise UpdateError("dependency convergence failed")
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(updater, "_run", fail_convergence)
    rollbacks = []
    monkeypatch.setattr(updater, "_rollback", lambda *args: rollbacks.append(args) or True)

    with pytest.raises(UpdateError, match="dependency convergence failed"):
        updater.update()

    assert calls == [expected]
    assert rollbacks == [("a" * 40, "b" * 40, "stopped", "1.0.0")]
    assert updater.public_status()["state"] == "failed"
    assert updater.public_status()["rollback"] == "succeeded"


@pytest.mark.parametrize(
    ("bridge_present", "generation_present"),
    [(False, False), (False, True), (True, False)],
    ids=["pre-bridge-base", "pre-bridge-generation", "bridge"],
)
def test_rollback_restores_dependencies_from_the_checked_out_tree(
    updater: AutoUpdater, monkeypatch: pytest.MonkeyPatch, bridge_present: bool,
    generation_present: bool,
):
    old_sha = "a" * 40
    new_sha = "b" * 40
    bridge = updater.root / "app" / "backend" / "dependency_convergence.py"
    bridge.parent.mkdir()
    bridge.write_text("# bridge\n")
    old_requirements = updater.root / "app" / "requirements.txt"
    generation_requirements = updater.root / "app" / "requirements-generation.lock.txt"
    if generation_present:
        generation_requirements.write_text("mflux==0.17.5\n")
        (updater.root / "conda_env" / "lib" / "python3.12" / "site-packages" / "mflux").mkdir(parents=True)
    events = []
    calls = []

    def fake_git(*args, **_kwargs):
        events.append(("git", args))
        if args == ("rev-parse", "HEAD"):
            return new_sha
        if args == ("status", "--porcelain", "--untracked-files=normal"):
            return ""
        if args == ("ls-tree", "--name-only", new_sha, "--", "ENVIRONMENT"):
            return "ENVIRONMENT"
        if args == ("read-tree", "--reset", "-u", old_sha):
            old_requirements.write_text("old-fastapi\n")
            if not bridge_present:
                bridge.unlink()
            return ""
        if args == ("update-ref", "refs/heads/main", old_sha, new_sha):
            return ""
        raise AssertionError(args)

    monkeypatch.setattr(updater, "_git", fake_git)
    monkeypatch.setattr(updater, "_stop_mode", lambda mode: events.append(("stop", mode)))
    monkeypatch.setattr(updater, "_verify_import", lambda version: events.append(("import", version)))
    monkeypatch.setattr(updater, "_start_mode", lambda mode: events.append(("start", mode)))
    monkeypatch.setattr(updater, "_verify_health", lambda *args: events.append(("health", args)) or True)
    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        events.append(("run", tuple(args)))
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(updater, "_run", fake_run)

    assert updater._rollback(old_sha, new_sha, "stopped", "1.0.0") is True

    read_tree = events.index(("git", ("read-tree", "--reset", "-u", old_sha)))
    first_install = next(index for index, event in enumerate(events) if event[0] == "run")
    assert read_tree < first_install
    if bridge_present:
        assert calls == [(
            [str(updater.root / "conda_env" / "bin" / "python"),
             "-m", "backend.dependency_convergence", "all-installed"],
            {"cwd": updater.root / "app", "timeout": 1800},
        )]
    else:
        expected = [(
            [str(updater.root / "conda_env" / "bin" / "python"), "-m", "pip", "install",
             "-r", str(old_requirements)],
            {"cwd": updater.root / "app", "timeout": 1800},
        )]
        if generation_present:
            expected.extend([
                ([str(updater.root / "conda_env" / "bin" / "python"), "-m", "pip", "install",
                  "-r", str(generation_requirements)],
                 {"cwd": updater.root / "app", "timeout": 1800}),
                ([str(updater.root / "conda_env" / "bin" / "python"), "-c",
                  "import mflux; print('GEN_VERIFY_OK')"],
                 {"cwd": updater.root / "app", "timeout": 1800}),
            ])
        assert calls == expected
    assert events[-3:] == [("import", "1.0.0"), ("start", "stopped"),
                            ("health", ("stopped", "1.0.0", old_sha))]


def test_rollback_to_legacy_commit_preserves_machine_environment_bytes_and_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    root, old_sha, new_sha = _runtime_state_rollback_repository(tmp_path)
    machine_environment = b"HF_HOME=/Volumes/Models\r\nCUSTOM_SETTING=keep\n"
    environment = root / "ENVIRONMENT"
    environment.write_bytes(machine_environment)
    environment.chmod(0o640)
    updater = AutoUpdater(_worktree_spec(root))
    monkeypatch.setattr(updater, "_stop_mode", lambda _mode: None)
    monkeypatch.setattr(updater, "_restore_rollback_dependencies", lambda: None)
    monkeypatch.setattr(updater, "_verify_import", lambda _version: None)
    monkeypatch.setattr(updater, "_start_mode", lambda _mode: None)
    monkeypatch.setattr(updater, "_verify_health", lambda *_args: True)

    assert updater._rollback(old_sha, new_sha, "stopped", "1.30.3") is True

    assert environment.read_bytes() == machine_environment
    assert stat.S_IMODE(environment.stat().st_mode) == 0o640
    assert subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip() == old_sha
    assert subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain=v1", "--untracked-files=normal"],
        check=True, capture_output=True, text=True,
    ).stdout == " M ENVIRONMENT\n"


def test_rollback_refuses_symlinked_machine_environment_without_touching_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    root, old_sha, new_sha = _runtime_state_rollback_repository(tmp_path)
    target = tmp_path / "operator-settings"
    target.write_bytes(b"SECRET_SETTING=keep\n")
    environment = root / "ENVIRONMENT"
    environment.symlink_to(target)
    updater = AutoUpdater(_worktree_spec(root))
    monkeypatch.setattr(updater, "_stop_mode", lambda _mode: None)

    assert updater._rollback(old_sha, new_sha, "stopped", "1.30.3") is False

    assert environment.is_symlink()
    assert target.read_bytes() == b"SECRET_SETTING=keep\n"
    assert subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip() == new_sha


def test_rollback_read_tree_failure_restores_machine_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    root, old_sha, new_sha = _runtime_state_rollback_repository(tmp_path)
    machine_environment = b"HF_HOME=/Volumes/Models\nCUSTOM_SETTING=keep\n"
    environment = root / "ENVIRONMENT"
    environment.write_bytes(machine_environment)
    environment.chmod(0o600)
    updater = AutoUpdater(_worktree_spec(root))
    real_git = updater._git

    def fail_after_read_tree(*args, **kwargs):
        result = real_git(*args, **kwargs)
        if args == ("read-tree", "--reset", "-u", old_sha):
            raise UpdateError("simulated failure after worktree mutation")
        return result

    monkeypatch.setattr(updater, "_git", fail_after_read_tree)
    monkeypatch.setattr(updater, "_stop_mode", lambda _mode: None)

    assert updater._rollback(old_sha, new_sha, "stopped", "1.30.3") is False

    assert environment.read_bytes() == machine_environment
    assert stat.S_IMODE(environment.stat().st_mode) == 0o600
    assert subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip() == new_sha
    assert not list(root.glob(".ENVIRONMENT.rollback.*.tmp"))


def test_rollback_preparation_failure_after_move_preserves_machine_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    root, old_sha, new_sha = _runtime_state_rollback_repository(tmp_path)
    machine_environment = b"HF_HOME=/Volumes/Models\nCUSTOM_SETTING=keep\n"
    environment = root / "ENVIRONMENT"
    environment.write_bytes(machine_environment)
    environment.chmod(0o640)
    updater = AutoUpdater(_worktree_spec(root))
    real_replace = os.replace

    def fail_after_environment_move(source, destination):
        real_replace(source, destination)
        if Path(source) == environment and Path(destination).name.startswith(
            ".ENVIRONMENT.rollback."
        ):
            raise OSError("simulated failure after moving machine state")

    monkeypatch.setattr("backend.auto_update.os.replace", fail_after_environment_move)
    monkeypatch.setattr(updater, "_stop_mode", lambda _mode: None)

    assert updater._rollback(old_sha, new_sha, "stopped", "1.30.3") is False

    backups = list(root.glob(".ENVIRONMENT.rollback.*.tmp"))
    preserved = environment if environment.exists() else backups[0]
    assert preserved.read_bytes() == machine_environment
    assert stat.S_IMODE(preserved.stat().st_mode) == 0o640
    assert environment.exists() or len(backups) == 1
    assert subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip() == new_sha


def test_secrets_are_redacted():
    value = _redact({"hf_token": "hf_secret", "details": "Authorization: Bearer-abc"})
    assert value["hf_token"] == "[redacted]"
    assert "Bearer-abc" not in value["details"]


def test_next_daily_and_weekly_checks_are_future(updater: AutoUpdater):
    now = dt.datetime(2026, 7, 15, 10, tzinfo=dt.timezone.utc)
    updater.now = lambda: now
    daily = updater._next_regular({**updater.defaults, "frequency": "daily", "maintenance_hour": 2})
    weekly = updater._next_regular({**updater.defaults, "frequency": "weekly", "maintenance_hour": 2})
    assert daily > now
    assert weekly > daily


def test_build_suffix_version_matching(updater: AutoUpdater):
    updater.spec["allow_build_suffix"] = True
    assert updater._version_matches("1.22.0.abcdef0", "1.22.0")
    assert not updater._version_matches("1.21.9.abcdef0", "1.22.0")
