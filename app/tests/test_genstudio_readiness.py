import json
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend import catalog
from backend.main import FLEET_TOKEN, app, get_catalog


RUNTIME_REPO = "AITRADER/FLUX2-klein-4B-mlx-4bit"
RUNTIME_REVISION = "7fd24828501390b67a92c8b66d2fc5a707d0ba1a"


def test_genstudio_model_inventory_records_revision_license_and_memory_floor():
    model = catalog.get_model(RUNTIME_REPO)

    assert model is not None
    assert model.qualified_revision == RUNTIME_REVISION
    assert model.capabilities == ("txt2img", "img2img", "edit")
    assert model.min_unified_memory_gb == 8
    assert model.license_spdx == "Apache-2.0"
    assert model.license_source_repo == "black-forest-labs/FLUX.2-klein-4B"
    assert len(model.license_source_revision or "") == 40
    assert model.license_repackage_copy_present is False


def test_health_and_inventory_expose_readiness_without_request_data():
    public = TestClient(app)
    health = public.get("/api/health")
    assert health.status_code == 200
    generation = health.json()["generation"]
    assert set(generation) == {"available", "busy", "queued", "running", "runtime_revision"}

    authed = TestClient(app, headers={"X-Studio-Token": FLEET_TOKEN})
    response = authed.get("/api/catalog")
    assert response.status_code == 200
    target = next(model for model in response.json()["models"] if model["repo"] == RUNTIME_REPO)
    assert target["qualified_revision"] == RUNTIME_REVISION
    assert target["license_evidence"]["spdx"] == "Apache-2.0"

    serialized = json.dumps({"health": health.json(), "target": target}).lower()
    for customer_field in ("image_path", "output_path", "resolved_seed", "jobs"):
        assert customer_field not in serialized


def test_inventory_marks_the_exact_cached_qualified_revision_ready():
    def cache_status(repo):
        return {
            "repo": repo,
            "state": "cached",
            "path": None,
            "bytes_complete": 1,
            "bytes_incomplete": 0,
        }

    with (
        patch("backend.main.cache.status_snapshot", side_effect=cache_status),
        patch("backend.main.cache.snapshot_revision", return_value=RUNTIME_REVISION),
        patch("backend.main.gen_manager.is_available", return_value=True),
    ):
        target = next(
            model for model in get_catalog()["models"] if model["repo"] == RUNTIME_REPO
        )

    assert target["model_revision"] == RUNTIME_REVISION
    assert target["qualified_revision_match"] is True
    assert target["execution_ready"] is True


def test_every_catalog_model_runs_locally_and_reports_a_real_cache_state():
    """v1.29.0 removed the cloud providers.

    Nothing in the catalog may claim a hosted provider, and no entry may be
    published with a synthesised "cached" state — every row now carries the
    real on-disk cache snapshot, so the Studio Hub's downloaded=true picker
    only ever offers models that were actually fetched.
    """
    assert all(model.provider == "local" for model in catalog.CATALOG)

    payload = get_catalog()
    for model in payload["models"]:
        assert model["provider"] == "local"
        for removed in (
            "is_cloud",
            "cloud_provider",
            "cloud_model_id",
            "cloud_credentials_ok",
            "cloud_provider_label",
            "cloud_signup_url",
            "requires_billing",
        ):
            assert removed not in model, f"{removed} still serialized for {model['repo']}"
        assert model["cache"]["state"] in {"absent", "partial", "cached"}

    assert not any(family.startswith(("pollinations", "cloudflare", "together",
                                      "gemini", "nebius", "huggingface"))
                   for family in payload["families"])


def test_txt2img_rejects_a_repo_that_is_not_in_the_catalog():
    """A stale client (or a history row naming a removed model) must get a clean
    400 rather than a 500 — the removed cloud repo ids are the concrete case."""
    client = TestClient(app, headers={"X-Studio-Token": FLEET_TOKEN})
    for repo in ("pollinations/flux", "cloudflare/sdxl-base", "not/a-real-model"):
        response = client.post(
            "/api/generate/txt2img",
            json={"repo": repo, "prompt": "a red apple", "width": 1024, "height": 1024},
        )
        assert response.status_code == 400, (repo, response.status_code, response.text)
        assert "Unknown repo" in response.json()["detail"]
