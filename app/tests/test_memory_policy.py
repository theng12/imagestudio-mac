from pathlib import Path

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


def test_default_preserves_performance_mode(tmp_path, monkeypatch):
    _reset(monkeypatch, tmp_path)
    data = memory_policy.status()
    assert data["mode"] == "performance"
    assert data["idle_seconds"] is None
    assert [item["mode"] for item in data["options"]] == [
        "performance", "balanced", "memory_saver", "immediate",
    ]


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
    assert "Performance · default" in html
    assert 'fetch("/api/memory-policy"' in script
    assert 'fetch("/api/memory/release"' in script
    assert PROCESS_TITLE == "Image Studio Mac"
