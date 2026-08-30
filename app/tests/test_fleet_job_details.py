import base64
import json
import logging

import pytest
from fastapi.testclient import TestClient

from backend import fleet_auth, job_details, main
from backend.generation import GenerationJob, GenerationManager
from backend.job_details import JobMediaError, build_job_details, resolve_job_media


PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9WlJk9sAAAAASUVORK5CYII="
)


def image_job(tmp_path):
    output = tmp_path / "output" / "job-1.png"
    upload = tmp_path / "uploads" / "reference.png"
    output.parent.mkdir()
    upload.parent.mkdir()
    output.write_bytes(PNG_BYTES)
    upload.write_bytes(PNG_BYTES)
    return GenerationJob(
        "job-1", "edit", {
            "repo": "org/model", "prompt": "make the sky gold",
            "negative_prompt": "blur", "width": 1024, "height": 1024,
            "steps": 8, "guidance": 3.5, "seed": 42,
            "image_paths": [str(upload)], "lora_names": ["portrait"],
            "lora_paths": ["/private/lora.safetensors"], "_secret": "never",
        }, state="done", output_path=str(output), origin="api",
        started_at=10.0, finished_at=18.0,
    )


@pytest.fixture
def configured_job(tmp_path, monkeypatch):
    job = image_job(tmp_path)
    monkeypatch.setattr(job_details, "UPLOADS_DIR", tmp_path / "uploads")
    monkeypatch.setattr(job_details, "OUTPUT_DIR", tmp_path / "output")
    return job


def assert_safe_headers(response):
    assert response.headers["cache-control"] == "no-store, private, max-age=0"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_image_detail_projection_is_allowlisted_and_path_free(configured_job):
    details = build_job_details(configured_job, "fleet-secret", now=100)

    assert details["schema"] == "kh-studio.job-details.v1"
    assert details["studio"] == "image"
    assert details["job"] == {
        "id": "job-1",
        "state": "done",
        "model": "org/model",
        "operation": "edit",
        "created_at": configured_job.created_at,
        "started_at": 10.0,
        "finished_at": 18.0,
        "runtime_s": 8.0,
        "origin": "api",
        "origin_device": None,
    }
    assert details["inputs"] == {
        "prompt": "make the sky gold",
        "negative_prompt": "blur",
        "text": None,
        "reference_transcript": None,
        "parameters": {
            "width": 1024,
            "height": 1024,
            "steps": 8,
            "guidance": 3.5,
            "seed": 42,
            "lora_names": ["portrait"],
        },
    }
    assert len(details["references"]) == 1
    assert len(details["outputs"]) == 1
    for item, kind, name in (
        (details["references"][0], "reference", "reference.png"),
        (details["outputs"][0], "output", "job-1.png"),
    ):
        assert item["kind"] == kind
        assert item["name"] == name
        assert item["media_type"] == "image/png"
        assert item["size_bytes"] == len(PNG_BYTES)
        assert item["duration_s"] is None
        assert item["expires_at"] == 400
        assert item["handle"]
        assert "job-1" not in item["handle"]
        assert name not in item["handle"]

    serialized = json.dumps(details)
    assert "/private" not in serialized
    assert "lora_paths" not in serialized
    assert "_secret" not in serialized
    assert str(configured_job.params["image_paths"][0]) not in serialized
    assert configured_job.output_path not in serialized


@pytest.mark.parametrize(
    ("state", "progress", "expected"),
    (
        ("running", 0.42, 0.42),
        ("queued", 2.0, 1.0),
        ("running", -1.0, 0.0),
        ("running", float("nan"), 0.0),
        ("running", "legacy", 0.0),
    ),
)
def test_active_image_detail_progress_is_bounded(
    configured_job, state, progress, expected,
):
    configured_job.state = state
    configured_job.progress = progress

    details = build_job_details(configured_job, "fleet-secret", now=100)

    assert details["job"]["progress"] == expected


@pytest.mark.parametrize(
    ("collection", "expected"),
    (("references", "reference.png"), ("outputs", "job-1.png")),
)
def test_signed_handles_resolve_only_the_recorded_media(configured_job, collection, expected):
    details = build_job_details(configured_job, "fleet-secret", now=100)
    handle = details[collection][0]["handle"]

    target = resolve_job_media(configured_job, handle, "fleet-secret", now=100)

    assert target.path == (
        job_details.UPLOADS_DIR / expected if collection == "references"
        else job_details.OUTPUT_DIR / expected
    ).resolve()
    assert target.media_type == "image/png"
    assert target.name == expected


def test_handle_expires_after_exactly_300_seconds(configured_job):
    handle = build_job_details(configured_job, "fleet-secret", now=100)["outputs"][0]["handle"]

    assert resolve_job_media(configured_job, handle, "fleet-secret", now=399.999).path.name == "job-1.png"
    with pytest.raises(JobMediaError, match="handle_expired"):
        resolve_job_media(configured_job, handle, "fleet-secret", now=400)
    with pytest.raises(JobMediaError, match="handle_expired"):
        resolve_job_media(configured_job, handle, "fleet-secret", now=401)


def test_tampered_handle_is_permission_denied(configured_job):
    handle = build_job_details(configured_job, "fleet-secret", now=100)["outputs"][0]["handle"]
    tampered = handle[:-1] + ("A" if handle[-1] != "A" else "B")

    with pytest.raises(JobMediaError, match="permission_denied"):
        resolve_job_media(configured_job, tampered, "fleet-secret", now=100)


def test_pruned_media_returns_media_removed_even_with_fresh_handle(configured_job):
    output = job_details.OUTPUT_DIR / "job-1.png"
    output.unlink()
    fresh_handle = build_job_details(configured_job, "fleet-secret", now=100)["outputs"][0]["handle"]

    with pytest.raises(JobMediaError, match="media_removed"):
        resolve_job_media(configured_job, fresh_handle, "fleet-secret", now=100)


def test_symlink_under_approved_root_is_rejected_at_access(configured_job, tmp_path):
    reference = job_details.UPLOADS_DIR / "reference.png"
    handle = build_job_details(configured_job, "fleet-secret", now=100)["references"][0]["handle"]
    outside = tmp_path / "outside.png"
    outside.write_bytes(PNG_BYTES)
    reference.unlink()
    reference.symlink_to(outside)

    with pytest.raises(JobMediaError, match="media_removed"):
        resolve_job_media(configured_job, handle, "fleet-secret", now=100)


def test_symlinked_approved_root_is_rejected_at_access(configured_job, tmp_path, monkeypatch):
    outside = tmp_path / "outside-uploads"
    outside.mkdir()
    (outside / "reference.png").write_bytes(PNG_BYTES)
    linked_root = tmp_path / "linked-uploads"
    linked_root.symlink_to(outside, target_is_directory=True)
    configured_job.params["image_paths"] = [str(linked_root / "reference.png")]
    monkeypatch.setattr(job_details, "UPLOADS_DIR", linked_root)
    handle = build_job_details(configured_job, "fleet-secret", now=100)["references"][0]["handle"]

    with pytest.raises(JobMediaError, match="media_removed"):
        resolve_job_media(configured_job, handle, "fleet-secret", now=100)


def test_handle_is_bound_to_job_kind_and_index(configured_job):
    handle = build_job_details(configured_job, "fleet-secret", now=100)["references"][0]["handle"]
    other = GenerationJob(
        "job-2", configured_job.mode, configured_job.params,
        state="done", output_path=configured_job.output_path,
    )

    with pytest.raises(JobMediaError, match="permission_denied"):
        resolve_job_media(other, handle, "fleet-secret", now=100)

    payload, signature = handle.split(".", 1)
    decoded = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    for key, value in (("k", "output"), ("i", 1)):
        changed = dict(decoded, **{key: value})
        encoded = base64.urlsafe_b64encode(
            json.dumps(changed, separators=(",", ":"), sort_keys=True).encode()
        ).rstrip(b"=").decode()
        with pytest.raises(JobMediaError, match="permission_denied"):
            resolve_job_media(configured_job, f"{encoded}.{signature}", "fleet-secret", now=100)


def test_fleet_detail_and_media_http_contract(configured_job, monkeypatch, caplog):
    manager = GenerationManager.__new__(GenerationManager)
    manager._jobs = {configured_job.job_id: configured_job}
    monkeypatch.setattr(main, "gen_manager", manager)
    monkeypatch.setattr(fleet_auth, "load_token", lambda: "fleet-secret")

    assert TestClient(main.app).get(
        "/api/fleet/jobs/job-1/details",
        headers={"host": "worker.example"},
    ).status_code == 401

    client = TestClient(
        main.app,
        headers={"X-Studio-Token": "fleet-secret", "host": "worker.example"},
    )
    missing = client.get("/api/fleet/jobs/missing/details")
    assert missing.status_code == 404
    assert missing.json() == {"detail": {"code": "job_not_found"}}

    details_response = client.get("/api/fleet/jobs/job-1/details")
    assert details_response.status_code == 200
    handle = details_response.json()["outputs"][0]["handle"]

    inline = client.get(f"/api/fleet/jobs/job-1/media/{handle}")
    assert inline.status_code == 200
    assert inline.content == PNG_BYTES
    assert inline.headers["content-disposition"].startswith("inline;")

    ranged = client.get(
        f"/api/fleet/jobs/job-1/media/{handle}",
        headers={"Range": "bytes=0-0"},
    )
    assert ranged.status_code == 206
    assert ranged.content == PNG_BYTES[:1]
    assert ranged.headers["content-range"] == f"bytes 0-0/{len(PNG_BYTES)}"

    download = client.get(f"/api/fleet/jobs/job-1/media/{handle}?download=true")
    assert download.status_code == 200
    assert download.headers["content-disposition"].startswith("attachment;")

    for response in (details_response, inline, ranged, download):
        assert_safe_headers(response)

    (job_details.OUTPUT_DIR / "job-1.png").unlink()
    removed = client.get(f"/api/fleet/jobs/job-1/media/{handle}")
    assert removed.status_code == 410
    assert removed.json() == {"detail": {"code": "media_removed"}}

    private_values = (
        configured_job.params["prompt"], configured_job.output_path,
        "fleet-secret", handle,
    )
    with caplog.at_level(logging.WARNING):
        denied = client.get(f"/api/fleet/jobs/job-1/media/{handle}x")
    assert denied.status_code == 403
    assert denied.json() == {"detail": {"code": "permission_denied"}}
    for value in private_values:
        assert value not in denied.text
        assert value not in caplog.text


def test_fleet_job_error_responses_are_not_cacheable(configured_job, monkeypatch):
    manager = GenerationManager.__new__(GenerationManager)
    manager._jobs = {configured_job.job_id: configured_job}
    monkeypatch.setattr(main, "gen_manager", manager)
    monkeypatch.setattr(fleet_auth, "load_token", lambda: "fleet-secret")
    monkeypatch.setattr(job_details.time, "time", lambda: 100.0)

    public = TestClient(main.app, headers={"host": "worker.example"})
    client = TestClient(
        main.app,
        headers={"X-Studio-Token": "fleet-secret", "host": "worker.example"},
    )
    handle = client.get("/api/fleet/jobs/job-1/details").json()["outputs"][0]["handle"]
    responses = {
        401: public.get("/api/fleet/jobs/job-1/details"),
        404: client.get("/api/fleet/jobs/missing/details"),
        403: client.get(f"/api/fleet/jobs/job-1/media/{handle}x"),
    }
    (job_details.OUTPUT_DIR / "job-1.png").unlink()
    responses[410] = client.get(f"/api/fleet/jobs/job-1/media/{handle}")
    monkeypatch.setattr(job_details.time, "time", lambda: 400.0)
    expired = client.get(f"/api/fleet/jobs/job-1/media/{handle}")

    for status, response in responses.items():
        assert response.status_code == status
        assert_safe_headers(response)
    assert expired.status_code == 410
    assert expired.json() == {"detail": {"code": "handle_expired"}}
    assert_safe_headers(expired)
