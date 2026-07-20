from hashlib import sha256

from PIL import Image

from backend import cache, generation
from backend.generation import GenerationJob, GenerationManager


def test_snapshot_revision_requires_an_immutable_cached_commit(tmp_path, monkeypatch):
    monkeypatch.setenv("HF_HOME", str(tmp_path))
    root = cache.repo_cache_dir("owner/model")
    revision = "a" * 40
    (root / "refs").mkdir(parents=True)
    (root / "refs" / "main").write_text(revision)
    snapshot = root / "snapshots" / revision
    snapshot.mkdir(parents=True)

    assert cache.snapshot_revision("owner/model") == revision
    assert cache.snapshot_path("owner/model", revision) == snapshot.resolve()

    (root / "refs" / "main").write_text("main")
    assert cache.snapshot_revision("owner/model") is None
    assert cache.snapshot_path("owner/model", revision) == snapshot.resolve()
    assert cache.snapshot_path("owner/model", "main") is None


def test_final_png_is_validated_and_atomically_published(tmp_path, monkeypatch):
    monkeypatch.setattr(generation, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(generation, "HISTORY_FILE", tmp_path / ".history.json")
    working = tmp_path / ".working"
    working.mkdir()
    staged = working / "image-job.png"
    Image.new("RGB", (96, 64), "navy").save(staged, format="PNG")
    revision = "b" * 40
    job = GenerationJob(
        job_id="image-job",
        mode="txt2img",
        params={"repo": "owner/model", "model_revision": revision, "steps": 4},
        state="running",
        resolved_seed=42,
        runtime_revision="imagestudio-mac@1.22.2;mflux@0.17.5;mlx@0.31.2",
        worker_id="image@mac-a",
        machine_id="mac-a",
        started_at=10.0,
        finished_at=12.5,
    )

    manager = GenerationManager()
    final_path = manager._publish_final_png(job, staged)
    job.state = "done"
    payload = job.serialize()
    content = final_path.read_bytes()

    assert not staged.exists()
    assert final_path == tmp_path / "image-job.png"
    assert payload["model_repository"] == "owner/model"
    assert payload["model_revision"] == revision
    assert payload["runtime_revision"].startswith("imagestudio-mac@")
    assert payload["worker_id"] == "image@mac-a"
    assert payload["machine_id"] == "mac-a"
    assert payload["width"] == 96
    assert payload["height"] == 64
    assert payload["steps"] == 4
    assert payload["seed"] == 42
    assert payload["image_count"] == 1
    assert payload["runtime_seconds"] == 2.5
    assert payload["media_type"] == "image/png"
    assert payload["format"] == "png"
    assert payload["bytes"] == len(content)
    assert payload["sha256"] == sha256(content).hexdigest()
    assert payload["final_asset"]["sha256"] == payload["sha256"]


def test_partial_or_invalid_output_never_becomes_success(tmp_path, monkeypatch):
    monkeypatch.setattr(generation, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(generation, "HISTORY_FILE", tmp_path / ".history.json")
    monkeypatch.setattr(generation.memory_policy, "mark_generation_started", lambda: None)
    monkeypatch.setattr(generation.memory_policy, "mark_generation_finished", lambda: None)
    manager = GenerationManager()
    job = GenerationJob(
        job_id="broken-job",
        mode="txt2img",
        params={"repo": "owner/model", "model_revision": "c" * 40, "steps": 4},
        total_steps=4,
        runtime_revision="runtime-r1",
        worker_id="image",
        machine_id="mac-a",
    )

    def write_partial(_job, output_path):
        _job.resolved_seed = 7
        output_path.write_bytes(b"not-a-complete-png")

    monkeypatch.setattr(manager, "_dispatch_txt2img", write_partial)
    manager._run_txt2img(job)
    payload = job.serialize()

    assert job.state == "error"
    assert payload["state"] == "error"
    assert payload["output_path"] is None
    assert payload["output_url"] is None
    assert payload["final_asset"] is None
    assert not (tmp_path / "broken-job.png").exists()
    assert not (tmp_path / ".working" / "broken-job.png").exists()
