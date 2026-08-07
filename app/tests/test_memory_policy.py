from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from backend import memory_policy
from backend.main import FLEET_TOKEN, app
from backend.process_title import PROCESS_TITLE


class Job:
    def __init__(self, state):
        self.state = state


class Manager:
    def __init__(self, jobs=None):
        self.jobs = jobs or []
        self.releases = 0

    def list_jobs(self):
        return self.jobs

    def release_memory(self):
        self.releases += 1
        return {"released": True, "actions": ["test cache cleared"]}


def _reset(monkeypatch, tmp_path, manager=None):
    monkeypatch.setattr(memory_policy, "SETTINGS_FILE", tmp_path / "memory_policy.json")
    monkeypatch.setattr(memory_policy, "_MANAGER", manager or Manager())
    monkeypatch.setattr(memory_policy, "_LAST_ACTIVITY_AT", None)
    monkeypatch.setattr(memory_policy, "_LAST_RELEASE_AT", None)
    monkeypatch.setattr(memory_policy, "_LAST_RELEASE_REASON", None)
    monkeypatch.setattr(memory_policy, "_LAST_RELEASE_DETAILS", None)
    monkeypatch.setattr(memory_policy, "_LAST_ERROR", None)
    monkeypatch.setattr(memory_policy, "_RELEASE_COUNT", 0)
    monkeypatch.setattr(memory_policy, "_RELEASING", False)


def test_explicit_performance_mode_keeps_model_loaded(tmp_path, monkeypatch):
    """`performance` must still pin a loaded model when an operator asks for
    it. What changed is that it is no longer the *default* — see
    test_default_mode_is_no_longer_the_one_that_never_releases below."""
    manager = Manager()
    _reset(monkeypatch, tmp_path, manager)
    memory_policy.save("performance")
    monkeypatch.setattr(memory_policy, "_LAST_ACTIVITY_AT", 100.0)
    assert memory_policy.status()["mode"] == "performance"
    assert memory_policy.run_due_release(now=100_000) is None
    assert manager.releases == 0


def test_default_mode_is_no_longer_the_one_that_never_releases(tmp_path, monkeypatch):
    """With no operator choice on disk, an idle model must eventually be
    freed. Previously the default was `performance` (idle_seconds=None), so
    the release thread ran forever and did nothing."""
    manager = Manager()
    _reset(monkeypatch, tmp_path, manager)
    monkeypatch.setattr(memory_policy, "_LAST_ACTIVITY_AT", 100.0)
    data = memory_policy.status()
    assert data["mode"] != "performance"
    assert data["idle_seconds"] is not None
    assert [item["mode"] for item in data["options"]] == [
        "performance", "balanced", "memory_saver", "immediate",
    ]
    assert memory_policy.run_due_release(now=100_000) is not None
    assert manager.releases == 1


def test_idle_policy_releases_once_after_deadline(tmp_path, monkeypatch):
    manager = Manager()
    _reset(monkeypatch, tmp_path, manager)
    memory_policy.save("balanced")
    monkeypatch.setattr(memory_policy, "_LAST_ACTIVITY_AT", 100.0)

    assert memory_policy.run_due_release(now=699.0) is None
    released = memory_policy.run_due_release(now=700.0)
    assert released["last_release_reason"] == "automatic:balanced"
    assert released["busy"] is False
    assert released["next_release_at"] is None
    assert manager.releases == 1
    assert memory_policy.run_due_release(now=701.0) is None


def test_active_generation_blocks_manual_release(tmp_path, monkeypatch):
    _reset(monkeypatch, tmp_path, Manager([Job("running")]))
    client = TestClient(app, headers={"X-Studio-Token": FLEET_TOKEN})
    response = client.post("/api/memory/release")
    assert response.status_code == 409


def test_memory_policy_api_and_frontend_contract(tmp_path, monkeypatch):
    _reset(monkeypatch, tmp_path)
    client = TestClient(app, headers={"X-Studio-Token": FLEET_TOKEN})
    saved = client.put("/api/memory-policy", json={"mode": "memory_saver"})
    assert saved.status_code == 200
    assert saved.json()["idle_seconds"] == 120
    released = client.post("/api/memory/release")
    assert released.status_code == 200
    assert released.json()["last_release_reason"] == "manual"

    root = Path(__file__).parents[1]
    html = (root / "frontend" / "index.html").read_text(encoding="utf-8")
    script = (root / "frontend" / "app.js").read_text(encoding="utf-8")
    assert "Release Memory / Unload Model" in html
    # The "· default" badge is no longer hardcoded onto Performance: since
    # the default now follows the host's memory, the label is bound to
    # whatever the backend reports.
    assert "Performance" in html
    assert "memoryPolicy.default_mode==='performance'" in html
    assert 'fetch("/api/memory-policy"' in script
    assert 'fetch("/api/memory/release"' in script
    assert PROCESS_TITLE == "Image Studio Mac"


def test_shipped_default_actually_releases_on_idle(monkeypatch) -> None:
    """The idle-release thread ran on every fleet machine and did nothing,
    because the shipped default was "performance" (idle_seconds=None). Each
    Studio ships this same skeleton, so on a shared 8 GB Mac 3-5 of them each
    independently pinned a model forever: 16 of 19 machines could not start a
    job. A default that never releases is not a default."""
    assert memory_policy.MODES[memory_policy.DEFAULT_MODE]["idle_seconds"] is not None
    assert (
        memory_policy.MODES[memory_policy.SMALL_MACHINE_DEFAULT_MODE]["idle_seconds"]
        is not None
    )

    # Small machines get the tighter budget; roomy ones keep a model warm longer.
    monkeypatch.setattr(
        memory_policy, "_SMALL_MACHINE_GB", 12, raising=False
    )
    import psutil

    monkeypatch.setattr(
        psutil, "virtual_memory",
        lambda: SimpleNamespace(total=int(8.6e9), available=int(4e9),
                                used=int(4.6e9), percent=53.0),
    )
    assert memory_policy.default_mode() == "memory_saver"

    monkeypatch.setattr(
        psutil, "virtual_memory",
        lambda: SimpleNamespace(total=int(25.8e9), available=int(18e9),
                                used=int(7.8e9), percent=30.0),
    )
    assert memory_policy.default_mode() == "balanced"


def test_operator_choice_still_wins_over_the_machine_default(monkeypatch, tmp_path) -> None:
    """An explicit mode is persisted and must survive; the memory-aware default
    only applies when nobody has chosen."""
    settings = tmp_path / "memory_policy.json"
    settings.write_text('{"mode": "performance"}\n', encoding="utf-8")
    monkeypatch.setattr(memory_policy, "SETTINGS_FILE", settings)
    assert memory_policy._read()["mode"] == "performance"


def test_ui_does_not_hardcode_performance_as_the_default() -> None:
    """The mode picker said "Performance · default". The default is chosen
    from the host's memory, so a hardcoded label is simply wrong on every
    8 GB machine. The badge must follow whatever the backend reports."""
    markup = (Path(__file__).resolve().parents[1]
              / "frontend" / "index.html").read_text(encoding="utf-8")
    assert "Performance · default" not in markup
    for mode in ("performance", "balanced", "memory_saver", "immediate"):
        assert f"memoryPolicy.default_mode==='{mode}'" in markup


def test_psutil_is_a_declared_base_dependency() -> None:
    """default_mode() imports psutil unconditionally on every install to size
    the machine-aware default, but psutil previously lived only in
    requirements-generation.lock.txt — the optional MLX/diffusers stack, not
    the base install install.js actually runs. A base-only install would hit
    the ImportError, which default_mode()'s bare except swallows, silently
    falling back to DEFAULT_MODE regardless of host memory: exactly the wrong
    direction on the small machines this default targets. Guards against that
    dependency quietly drifting back out of the base files."""
    root = Path(__file__).resolve().parents[1]
    requirements = (root / "requirements.txt").read_text(encoding="utf-8")
    lock = (root / "requirements.lock.txt").read_text(encoding="utf-8")
    assert "psutil" in requirements
    assert "psutil==" in lock
