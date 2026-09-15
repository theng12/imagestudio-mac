import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend import cache, downloads, generation
from backend.main import FLEET_TOKEN, app, get_catalog


REPO = "AITRADER/FLUX2-klein-4B-mlx-4bit"
REVISION = "7fd24828501390b67a92c8b66d2fc5a707d0ba1a"


def _snapshot(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.setenv("HF_HOME", str(tmp_path))
    root = tmp_path / "hub" / "models--AITRADER--FLUX2-klein-4B-mlx-4bit"
    (root / "refs").mkdir(parents=True)
    (root / "refs" / "main").write_text(REVISION)
    snapshot = root / "snapshots" / REVISION
    snapshot.mkdir(parents=True)
    return snapshot


def _indexed_component(snapshot: Path, *shards: str) -> Path:
    component = snapshot / "text_encoder"
    component.mkdir()
    weight_map = {f"tensor_{index}": name for index, name in enumerate(shards)}
    (component / "model.safetensors.index.json").write_text(
        json.dumps({"weight_map": weight_map})
    )
    return component


def test_cached_snapshot_is_not_ready_when_an_indexed_shard_is_missing(tmp_path, monkeypatch):
    snapshot = _snapshot(tmp_path, monkeypatch)
    component = _indexed_component(snapshot, "0.safetensors", "1.safetensors")
    (component / "0.safetensors").write_bytes(b"present")

    assert cache.cache_state(REPO) == "cached"
    assert cache.model_files_readiness(REPO) == {
        "ready": False,
        "revision": REVISION,
        "error_code": "MODEL_FILES_UNAVAILABLE",
        "reason": "One or more required model files are missing or unreadable.",
    }


def test_cached_snapshot_is_not_ready_when_a_weight_symlink_is_broken(tmp_path, monkeypatch):
    snapshot = _snapshot(tmp_path, monkeypatch)
    component = _indexed_component(snapshot, "0.safetensors", "1.safetensors")
    (component / "0.safetensors").symlink_to("../../../blobs/missing")
    (component / "1.safetensors").write_bytes(b"present")

    assert cache.cache_state(REPO) == "cached"
    assert cache.model_files_readiness(REPO)["error_code"] == "MODEL_FILES_UNAVAILABLE"


def test_cached_snapshot_is_not_ready_when_a_companion_shard_is_unreadable(
    tmp_path, monkeypatch,
):
    snapshot = _snapshot(tmp_path, monkeypatch)
    component = _indexed_component(snapshot, "0.safetensors", "1.safetensors")
    (component / "0.safetensors").write_bytes(b"present")
    companion = component / "1.safetensors"
    companion.write_bytes(b"present")
    original_open = Path.open

    def refuse_companion(path, *args, **kwargs):
        if path == companion:
            raise PermissionError("test unreadable model shard")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", refuse_companion)

    assert cache.cache_state(REPO) == "cached"
    assert cache.model_files_readiness(REPO)["ready"] is False


def test_complete_snapshot_reports_immutable_revision_ready(tmp_path, monkeypatch):
    snapshot = _snapshot(tmp_path, monkeypatch)
    component = _indexed_component(snapshot, "0.safetensors", "1.safetensors")
    (component / "0.safetensors").write_bytes(b"first")
    (component / "1.safetensors").write_bytes(b"second")

    assert cache.model_files_readiness(REPO) == {
        "ready": True,
        "revision": REVISION,
        "error_code": None,
        "reason": None,
    }


def test_catalog_exposes_typed_file_readiness_and_fails_execution_closed():
    unavailable = {
        "ready": False,
        "revision": REVISION,
        "error_code": "MODEL_FILES_UNAVAILABLE",
        "reason": "One or more required model files are missing or unreadable.",
    }
    cached = {
        "repo": REPO,
        "state": "cached",
        "path": None,
        "bytes_complete": 1,
        "bytes_incomplete": 0,
    }
    with (
        patch("backend.main.cache.status_snapshot", return_value=cached),
        patch("backend.main.cache.snapshot_revision", return_value=REVISION),
        patch("backend.main.cache.model_files_readiness", return_value=unavailable),
        patch("backend.main.gen_manager.is_available", return_value=True),
    ):
        target = next(model for model in get_catalog()["models"] if model["repo"] == REPO)

    assert target["cache"]["state"] == "cached"
    assert target["readiness"] == unavailable
    assert target["execution_ready"] is False


def test_catalog_does_not_admit_a_partial_cache_with_readable_existing_shards():
    readable = {
        "ready": True,
        "revision": REVISION,
        "error_code": None,
        "reason": None,
    }
    partial = {
        "repo": REPO,
        "state": "partial",
        "path": None,
        "bytes_complete": 1,
        "bytes_incomplete": 1,
    }
    with (
        patch("backend.main.cache.status_snapshot", return_value=partial),
        patch("backend.main.cache.snapshot_revision", return_value=REVISION),
        patch("backend.main.cache.model_files_readiness", return_value=readable),
        patch("backend.main.gen_manager.is_available", return_value=True),
    ):
        target = next(model for model in get_catalog()["models"] if model["repo"] == REPO)

    assert target["readiness"]["ready"] is False
    assert target["readiness"]["error_code"] == "MODEL_FILES_UNAVAILABLE"
    assert target["execution_ready"] is False


def test_txt2img_rejects_unreadable_model_files_with_a_typed_error():
    unavailable = {
        "ready": False,
        "revision": REVISION,
        "error_code": "MODEL_FILES_UNAVAILABLE",
        "reason": "One or more required model files are missing or unreadable.",
    }
    client = TestClient(app, headers={"X-Studio-Token": FLEET_TOKEN})
    with (
        patch("backend.main.gen_manager.is_available", return_value=True),
        patch("backend.main.cache.cache_state", return_value="cached"),
        patch("backend.main.cache.snapshot_revision", return_value=REVISION),
        patch("backend.main.cache.model_files_readiness", return_value=unavailable),
    ):
        response = client.post(
            "/api/generate/txt2img",
            json={"repo": REPO, "prompt": "a violet cube", "width": 1024, "height": 1024},
        )

    assert response.status_code == 409
    assert response.json()["detail"] == {
        "error_code": "MODEL_FILES_UNAVAILABLE",
        "message": "One or more required model files are missing or unreadable.",
    }


def test_dispatch_rechecks_model_files_before_loading_the_worker(tmp_path, monkeypatch):
    snapshot = _snapshot(tmp_path, monkeypatch)
    component = _indexed_component(snapshot, "0.safetensors", "1.safetensors")
    (component / "0.safetensors").write_bytes(b"present")
    job = generation.GenerationJob(
        job_id="readiness-test",
        mode="txt2img",
        params={"repo": REPO, "model_revision": REVISION},
    )

    with pytest.raises(cache.ModelFilesUnavailable) as raised:
        generation.manager._dispatch_txt2img(job, tmp_path / "unused.png")

    assert raised.value.error_code == "MODEL_FILES_UNAVAILABLE"


def test_generation_job_serializes_a_typed_model_file_error():
    job = generation.GenerationJob(
        job_id="typed-generation-error",
        mode="txt2img",
        params={"repo": REPO, "model_revision": REVISION},
        state="error",
        error="ModelFilesUnavailable: MODEL_FILES_UNAVAILABLE",
        error_code="MODEL_FILES_UNAVAILABLE",
    )

    assert job.serialize()["error_code"] == "MODEL_FILES_UNAVAILABLE"


def test_download_does_not_report_done_when_required_files_remain_unavailable(monkeypatch):
    monkeypatch.setattr(downloads.cache, "ensure_hub_dir", lambda: None)
    monkeypatch.setattr(downloads.settings, "get_hf_token", lambda: None)
    monkeypatch.setattr(downloads, "snapshot_download", lambda **kwargs: "/unused")
    monkeypatch.setattr(
        downloads.DownloadManager, "_resolve_total_bytes", lambda self, repo, token: 1,
    )
    monkeypatch.setattr(
        downloads.cache,
        "model_files_readiness",
        lambda repo, revision=None: {
            "ready": False,
            "revision": REVISION,
            "error_code": "MODEL_FILES_UNAVAILABLE",
            "reason": "One or more required model files are missing or unreadable.",
        },
    )
    manager = downloads.DownloadManager()
    job = downloads.DownloadJob(job_id="readiness-download", repo=REPO)

    manager._run(job)

    assert job.state == "error"
    assert job.error == (
        "ModelFilesUnavailable: MODEL_FILES_UNAVAILABLE: "
        "One or more required model files are missing or unreadable."
    )
    assert job.error_code == "MODEL_FILES_UNAVAILABLE"
    assert job.serialize()["error_code"] == "MODEL_FILES_UNAVAILABLE"
