import json
import threading

import pytest
from fastapi.testclient import TestClient

from backend import main
from backend import generation
from backend.generation import GenerationJob, GenerationManager


def test_activity_snapshot_waits_for_the_job_registry_lock():
    manager = GenerationManager.__new__(GenerationManager)
    manager._lock = threading.Lock()
    manager._jobs = {
        "running": GenerationJob("running", "txt2img", {"repo": "org/model"}, state="running"),
    }
    entered, finished = threading.Event(), threading.Event()

    def snapshot():
        entered.set()
        manager.activity_snapshot(observed_at=1.0)
        finished.set()

    with manager._lock:
        reader = threading.Thread(target=snapshot)
        reader.start()
        assert entered.wait(1)
        assert not finished.wait(0.1)
    assert finished.wait(1)
    reader.join()


@pytest.mark.parametrize("operation", ("start", "snapshot", "clear", "delete"))
def test_live_job_registry_operations_share_the_same_lock(tmp_path, monkeypatch, operation):
    """Starting and maintenance cannot race the activity reporter's job copy."""
    manager = GenerationManager.__new__(GenerationManager)
    manager._lock = threading.Lock()
    manager._jobs = {
        "terminal": GenerationJob("terminal", "txt2img", {"repo": "org/model"}, state="done"),
    }
    manager._persist = lambda: None
    monkeypatch.setattr(generation, "OUTPUT_DIR", tmp_path)

    class NoopWorker:
        def __init__(self, **_kwargs):
            pass

        def start(self):
            pass

    real_thread = threading.Thread
    monkeypatch.setattr(generation.threading, "Thread", NoopWorker)
    actions = {
        "start": lambda: manager.start_txt2img({"steps": 1}),
        "snapshot": lambda: manager.activity_snapshot(observed_at=1.0),
        "clear": manager.clear_history,
        "delete": lambda: manager.delete_job("terminal"),
    }
    entered, finished = threading.Event(), threading.Event()

    def run_operation():
        entered.set()
        actions[operation]()
        finished.set()

    with manager._lock:
        worker = real_thread(target=run_operation)
        worker.start()
        assert entered.wait(1)
        assert not finished.wait(0.1)
    assert finished.wait(1)
    worker.join()


def test_activity_snapshot_prefers_running_job_over_newer_queued_job():
    manager = GenerationManager.__new__(GenerationManager)
    manager._lock = threading.Lock()
    manager._jobs = {
        "running": GenerationJob(
            "running", "txt2img", {"repo": "running/model"},
            state="running", progress=0.6, started_at=11.0, created_at=10.0,
        ),
        "queued": GenerationJob(
            "queued", "txt2img", {"repo": "queued/model"},
            state="queued", progress=0.0, created_at=20.0,
        ),
    }

    result = manager.activity_snapshot(observed_at=25.0)

    assert result["active"]["id"] == "running"
    assert result["active"]["model"] == "running/model"


def test_activity_snapshot_exposes_only_active_and_latest_safe_evidence():
    manager = GenerationManager.__new__(GenerationManager)
    manager._lock = threading.Lock()
    manager._jobs = {
        "run": GenerationJob(
            "run", "txt2img", {"repo": "org/model", "prompt": "secret"},
            state="running", progress=0.4, started_at=20.0, origin="local_ui",
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
    assert result["active"]["origin"] == "local_ui"
    assert "origin_device" not in result["active"]
    assert result["latest"]["id"] == "done"
    assert result["latest"]["runtime_s"] == 5.0
    assert result["latest"]["source"] == "direct"
    assert "secret" not in repr(result)
    assert "/private/output.png" not in repr(result)


def test_activity_snapshot_clamps_progress_and_uses_terminal_timestamps():
    manager = GenerationManager.__new__(GenerationManager)
    manager._lock = threading.Lock()
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
        "origin": "unknown",
        "error": None,
    }
    assert result["latest"]["error"] is None
    assert result["latest"]["created_at"] is not None
    assert "old/model" not in json.dumps(result)


def test_activity_snapshot_defaults_legacy_history_provenance_to_unknown():
    job = GenerationManager._from_disk({
        "job_id": "legacy",
        "mode": "txt2img",
        "params": {"repo": "legacy/model", "prompt": "private"},
        "state": "done",
        "progress": 1.0,
        "created_at": 10.0,
        "started_at": 11.0,
        "finished_at": 12.0,
    })
    assert job is not None

    result = GenerationManager._activity_projection(job, observed_at=20.0)

    assert result["origin"] == "unknown"
    assert "origin_device" not in result
    assert "private" not in repr(result)


def test_activity_route_is_authenticated_and_returns_sanitized_snapshot(monkeypatch):
    manager = GenerationManager.__new__(GenerationManager)
    manager._lock = threading.Lock()
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
