import json

from fastapi.testclient import TestClient

from backend import main
from backend.generation import GenerationJob, GenerationManager


def test_activity_snapshot_exposes_only_active_and_latest_safe_evidence():
    manager = GenerationManager.__new__(GenerationManager)
    manager._jobs = {
        "run": GenerationJob(
            "run", "txt2img", {"repo": "org/model", "prompt": "secret"},
            state="running", progress=0.4, started_at=20.0,
        ),
        "done": GenerationJob(
            "done", "txt2img", {"repo": "org/model", "prompt": "secret"},
            state="done", progress=1.0, started_at=10.0, finished_at=15.0,
            output_path="/private/output.png",
        ),
    }

    result = manager.activity_snapshot(observed_at=25.0)

    assert result["schema"] == "kh-studio.activity.v1"
    assert result["studio"] == "image"
    assert result["observed_at"] == 25.0
    assert result["active"]["id"] == "run"
    assert result["active"]["model"] == "org/model"
    assert result["active"]["source"] == "direct"
    assert result["latest"]["id"] == "done"
    assert result["latest"]["runtime_s"] == 5.0
    assert result["latest"]["source"] == "direct"
    assert "secret" not in repr(result)
    assert "/private/output.png" not in repr(result)


def test_activity_snapshot_clamps_progress_and_uses_terminal_timestamps():
    manager = GenerationManager.__new__(GenerationManager)
    manager._jobs = {
        "old": GenerationJob(
            "old", "txt2img", {"repo": "old/model"}, state="error",
            progress=-3.0, started_at=5.0, finished_at=8.0,
        ),
        "new": GenerationJob(
            "new", "txt2img", {"repo": "new/model"}, state="cancelled",
            progress=3.0, started_at=20.0, finished_at=30.0,
        ),
    }

    result = manager.activity_snapshot(observed_at=40.0)

    assert result["active"] is None
    assert result["latest"] == {
        "id": "new",
        "state": "cancelled",
        "model": "new/model",
        "progress": 1.0,
        "created_at": result["latest"]["created_at"],
        "started_at": 20.0,
        "finished_at": 30.0,
        "runtime_s": 10.0,
        "source": "direct",
        "error": None,
    }
    assert result["latest"]["error"] is None
    assert result["latest"]["created_at"] is not None
    assert "old/model" not in json.dumps(result)


def test_activity_route_is_authenticated_and_returns_sanitized_snapshot(monkeypatch):
    manager = GenerationManager.__new__(GenerationManager)
    manager._jobs = {
        "run": GenerationJob(
            "run", "txt2img", {
                "repo": "org/model", "prompt": "private prompt",
                "image_path": "/private/reference.png",
            }, state="running", progress=2.0, started_at=20.0,
        ),
    }
    monkeypatch.setattr(main, "gen_manager", manager)

    public = TestClient(main.app)
    assert public.get("/api/fleet/activity").status_code == 401

    client = TestClient(main.app, headers={"X-Studio-Token": main.FLEET_TOKEN})
    response = client.get("/api/fleet/activity")

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema"] == "kh-studio.activity.v1"
    assert payload["studio"] == "image"
    assert payload["active"]["progress"] == 1.0
    assert payload["active"]["model"] == "org/model"
    assert "private prompt" not in response.text
    assert "/private/reference.png" not in response.text
