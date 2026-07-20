from hashlib import sha256

from backend import cache
from backend.generation import GenerationJob


def test_snapshot_revision_requires_an_immutable_cached_commit(tmp_path, monkeypatch):
    monkeypatch.setenv("HF_HOME", str(tmp_path))
    root = cache.repo_cache_dir("owner/model")
    revision = "a" * 40
    (root / "refs").mkdir(parents=True)
    (root / "refs" / "main").write_text(revision)
    (root / "snapshots" / revision).mkdir(parents=True)

    assert cache.snapshot_revision("owner/model") == revision

    (root / "refs" / "main").write_text("main")
    assert cache.snapshot_revision("owner/model") is None


def test_completed_generation_serializes_final_png_evidence(tmp_path):
    content = b"\x89PNG\r\n\x1a\nfinal-image"
    output = tmp_path / "result.png"
    output.write_bytes(content)
    revision = "b" * 40
    job = GenerationJob(
        job_id="image-job",
        mode="txt2img",
        params={"repo": "owner/model", "model_revision": revision},
        state="done",
        output_path=str(output),
    )

    payload = job.serialize()

    assert payload["model_revision"] == revision
    assert payload["media_type"] == "image/png"
    assert payload["format"] == "png"
    assert payload["bytes"] == len(content)
    assert payload["sha256"] == sha256(content).hexdigest()
