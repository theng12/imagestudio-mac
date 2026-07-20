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
    assert model.min_unified_memory_gb == 16
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
